"""Read-only local API, database, broker, readiness, and container probes."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.parse
from urllib.request import Request, urlopen

from tools.local_runtime_config import (API_HEALTH_URL, ALLOWED_CONTAINERS, BROKER_HOST, BROKER_PORT, GENERATION_TABLES)

def api_health(timeout: float, urlopen_fn=urlopen) -> tuple[bool, str]:
    """8000 API 的 liveness 检查；本工具从不代启/重启 API。"""
    try:
        req = Request(API_HEALTH_URL, method="GET")
        with urlopen_fn(req, timeout=timeout) as resp:
            reachable = resp.status == 200
        return reachable, "8000 /health 可达" if reachable else "8000 /health 非 200"
    except Exception as exc:
        return False, f"8000 /health 不可达: {type(exc).__name__}"


def database_check(dsn: str | None, timeout: float) -> tuple[bool, str, str | None]:
    """PG：连接 DSN，断言 current_database()==zhijuan_local 且迁移表齐全。"""
    if not dsn:
        return False, "DATABASE_URL 未配置", "NOT_CONFIGURED"
    import psycopg
    try:
        with psycopg.connect(dsn, connect_timeout=timeout) as conn:
            row = conn.execute("SELECT current_database()").fetchone()
            dbname = str(row[0]) if row else ""
            rows = conn.execute(
                "SELECT tablename FROM pg_catalog.pg_tables "
                "WHERE schemaname = current_schema() AND tablename LIKE 'generation_%'"
            ).fetchall()
            existing = {str(r[0]) for r in rows}
    except Exception as exc:
        return False, f"PG 连接失败: {type(exc).__name__}", "DATABASE_UNAVAILABLE"
    if dbname != "zhijuan_local":
        return False, f"当前数据库是 {dbname}，不是 zhijuan_local", "DATABASE_UNAVAILABLE"
    missing = [name for name in GENERATION_TABLES if name not in existing]
    if missing:
        return False, f"缺少 generation_* 表: {missing}", "DATABASE_UNAVAILABLE"
    return True, f"PG 就绪（{dbname}，{len(existing)} 张 generation_* 表）", None


def broker_check(timeout: float) -> tuple[bool, str, str | None]:
    """55672 端口 / AMQP 握手探测（不携带凭据，不消费队列）。"""
    try:
        sock = socket.create_connection((BROKER_HOST, BROKER_PORT), timeout=timeout)
    except OSError as exc:
        return False, f"55672 不可达: {type(exc).__name__}", "BROKER_UNAVAILABLE"
    try:
        sock.settimeout(timeout)
        # AMQP 0-9-1 协议头：客户端先发；服务端或回显协议头，或直接以
        # connection.start 方法帧应答（RabbitMQ 4 的行为，帧首字节 0x01、
        # class 0x000A）。两种应答都证明对端是 AMQP 服务。
        sock.sendall(b"AMQP\x00\x00\x09\x01")
        reply = sock.recv(16)
        reachable = reply.startswith(b"AMQP") or (
            len(reply) >= 9 and reply[0] == 0x01 and reply[7:9] == b"\x00\x0a")
    except OSError as exc:
        return False, f"AMQP 握手失败: {type(exc).__name__}", "BROKER_UNAVAILABLE"
    finally:
        sock.close()
    if not reachable:
        return False, "55672 可连但对端未应答 AMQP 协议头", "BROKER_UNAVAILABLE"
    if not os.getenv("CELERY_BROKER_URL"):
        return False, "RabbitMQ 可达，但 CELERY_BROKER_URL 未配置", "NOT_CONFIGURED"
    return True, "RabbitMQ 55672 AMQP 可达", None


def heartbeat_check(component: str, timeout: float) -> tuple[bool, str, str | None]:
    """查 runtime_heartbeats 里同 runtime_id 的组件心跳是否新鲜。

    表不存在一律视为未就绪；行存在但过期给 HEARTBEAT_STALE。
    """
    unavailable_code = "WORKER_UNAVAILABLE" if component == "worker" else "DISPATCHER_UNAVAILABLE"
    runtime_id = os.getenv("ZHIJUAN_RUNTIME_ID", "zhijuan-local")
    ttl = float(os.getenv("ZHIJUAN_HEARTBEAT_TTL_SECONDS", "20"))
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return False, "DATABASE_URL 未配置，无法查询心跳", "NOT_CONFIGURED"
    try:
        import sys
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        import psycopg
        import services.api.runtime_heartbeats as hb
        with psycopg.connect(dsn, connect_timeout=timeout) as conn:
            fresh = hb.fresh_components(conn, runtime_id, ttl)
    except Exception as exc:
        return False, f"心跳表不可查（未部署或无权限）: {type(exc).__name__}", unavailable_code
    entry = fresh.get(component)
    if entry is None:
        return False, f"无 {component} 心跳记录（进程未运行或未上线）", unavailable_code
    age = entry.get("age_seconds")
    if entry.get("ok"):
        return True, f"{component} 心跳新鲜（{age:.1f}s < {ttl:.0f}s）", None
    return False, f"{component} 心跳过期（{age:.1f}s >= {ttl:.0f}s）", "HEARTBEAT_STALE"


def tcp_base_check(base_url: str | None, timeout: float, label: str) -> tuple[bool, str, str | None]:
    """author/solver 网关 base URL 的 TCP 可达性（不发起真实 Runs 调用）。"""
    unavailable_code = "AUTHOR_UNAVAILABLE" if label == "author" else "SOLVER_UNAVAILABLE"
    url = (base_url or "").rstrip("/")
    if not url:
        return False, f"{label} base URL 未配置", "NOT_CONFIGURED"
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
    except OSError as exc:
        return False, f"{label} TCP 不可达（{host}:{port}）: {type(exc).__name__}", unavailable_code
    return True, f"{label} TCP 可达（{host}:{port}）", None


def budget_check(timeout: float, *, urlopen_fn=urlopen) -> tuple[bool, str, str | None]:
    """只读预算状态（C3：不预留、不调用上游、不改账本）。"""
    url = os.getenv("ZHIJUAN_BUDGET_INTERNAL_URL", "http://127.0.0.1:8650/internal/budget")
    token = os.getenv("ZHIJUAN_BUDGET_PROXY_TOKEN", "")
    if not token:
        return False, "ZHIJUAN_BUDGET_PROXY_TOKEN 未配置（预算不可用）", "NOT_CONFIGURED"
    try:
        req = Request(url + "?min_requests=1", method="GET", headers={"Authorization": f"Bearer {token}"})
        with urlopen_fn(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return False, f"/internal/budget 不可达: {type(exc).__name__}", "BUDGET_UNAVAILABLE"
    sufficient = body.get("sufficient")
    reason = body.get("reason_code")
    if sufficient is False or reason == "BUDGET_INSUFFICIENT":
        return False, "预算不足（reason_code=%s）" % reason, "BUDGET_INSUFFICIENT"
    return True, "预算接口可达", None


def container_state(name: str, timeout: float = 10.0) -> tuple[str, str]:
    """对精确名称容器做只读 `docker ps --format`（名称来自白名单）。

    返回 (state, 状态行)；state ∈ running/exited/.../missing/unknown。
    """
    if name not in ALLOWED_CONTAINERS:
        raise RuntimeError(f"docker 只允许查询精确名称: {sorted(ALLOWED_CONTAINERS)}")
    try:
        proc = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name=^{name}$",
             "--format", "{{.State}}\t{{.Status}}"],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "unknown", f"docker ps 不可用: {type(exc).__name__}"
    line = proc.stdout.strip()
    if not line:
        return "missing", f"容器 {name} 未找到"
    state, _, status = line.partition("\t")
    return state, f"{name}: {status}"
