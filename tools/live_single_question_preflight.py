"""Read-only checks and fail-closed preflight for the isolated acceptance runtime."""
from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone
from typing import Any
from urllib.request import Request

from tools.live_single_question_budget import BudgetInsufficientError
from tools.live_single_question_config import API_PORT, TEST_DATABASE_NAME, TEST_VHOST, ACCEPT_RUNTIME_ID, REQUIRED_TABLES

def verify_test_database(timeout: float = 6.0) -> dict[str, Any]:
    """连接 ZHIJUAN_TEST_DATABASE_URL，硬断言库身份 == zhijuan_accept_w6。

    等于 zhijuan_local 或其他库立即拒绝（当前数据库函数只允许这一个）。
    """
    dsn = os.getenv("ZHIJUAN_TEST_DATABASE_URL", "")
    if not dsn:
        return {"ok": False, "detail": "ZHIJUAN_TEST_DATABASE_URL 未配置",
                "code": "NOT_CONFIGURED", "next_action": "在验收环境配置 ZHIJUAN_TEST_DATABASE_URL 指向 zhijuan_accept_w6"}
    import psycopg
    try:
        with psycopg.connect(dsn, connect_timeout=max(1, int(timeout))) as conn:
            row = conn.execute("SELECT current_database()").fetchone()
            dbname = str(row[0]) if row else ""
            existing = {str(r[0]) for r in conn.execute(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = current_schema()").fetchall()}
    except Exception as exc:
        return {"ok": False, "detail": f"PG 连接失败: {type(exc).__name__}",
                "code": "DATABASE_UNAVAILABLE", "next_action": "确认 PG 容器运行中且测试库已建"}
    if dbname != TEST_DATABASE_NAME:
        return {"ok": False, "detail": f"当前数据库是 {dbname}，不是 {TEST_DATABASE_NAME}（绝不连 zhijuan_local）",
                "code": "DATABASE_UNAVAILABLE", "next_action": "核对 ZHIJUAN_TEST_DATABASE_URL 指向专属测试库"}
    missing = [name for name in REQUIRED_TABLES if name not in existing]
    if missing:
        return {"ok": False, "detail": f"缺少表: {missing}", "code": "DATABASE_UNAVAILABLE",
                "next_action": "先在测试库执行 database/003/004/005 迁移"}
    return {"ok": True, "detail": f"PG 就绪（{dbname}，{len(existing)} 张表包含心跳表）", "code": None}


def probe_author(timeout: float, hooks) -> tuple[bool, str, str | None]:
    base = os.getenv("HERMES_API_BASE_URL", "").rstrip("/")
    if not base or not os.getenv("HERMES_API_KEY"):
        return False, "author 网关地址或令牌未配置", "NOT_CONFIGURED"
    try:
        status, payload = hooks._http_get(base + "/health", timeout=timeout)
    except Exception as exc:
        return False, f"author /health 不可达: {type(exc).__name__}", "AUTHOR_UNAVAILABLE"
    if status != 200 or (isinstance(payload, dict) and payload.get("status") != "ok"):
        return False, f"author /health 状态异常 HTTP {status}", "AUTHOR_UNAVAILABLE"
    return True, "author 网关就绪（200 status=ok）", None


def probe_solver(timeout: float, hooks) -> tuple[bool, str, str | None]:
    base = os.getenv("HERMES_SOLVER_API_BASE_URL", "").rstrip("/")
    if not base or not os.getenv("HERMES_SOLVER_API_KEY"):
        return False, "solver-entry 网关地址或令牌未配置", "NOT_CONFIGURED"
    try:
        status, payload = hooks._http_get(base + "/internal/readiness", timeout=timeout,
                                    token=os.getenv("HERMES_SOLVER_API_KEY", ""))
    except Exception as exc:
        return False, f"solver-entry /internal/readiness 不可达: {type(exc).__name__}", "SOLVER_UNAVAILABLE"
    if status != 200:
        return False, f"solver-entry 就绪状态 HTTP {status}", "SOLVER_UNAVAILABLE"
    # 与 health.py::_probe_solver 一致：body 须 status==OK 且 upstream_configured==true。
    if (not isinstance(payload, dict) or payload.get("status") != "OK"
            or payload.get("upstream_configured") is not True):
        return False, "solver-entry 上游未配置或就绪响应缺字段", "SOLVER_UNAVAILABLE"
    return True, "solver-entry 就绪（200 status=OK upstream_configured=true）", None


def broker_url_ok() -> tuple[bool, str, str | None]:
    url = os.getenv("CELERY_BROKER_URL", "")
    if not url.startswith(("amqp://", "amqps://")):
        return False, "CELERY_BROKER_URL 未配置或非 amqp 开头", "NOT_CONFIGURED"
    # 验收必须用专属 vhost，绝不与日常 vhost 混用。
    if "/" + TEST_VHOST not in url:
        return False, f"CELERY_BROKER_URL 未指向验收 vhost {TEST_VHOST}", "NOT_CONFIGURED"
    return True, "CELERY_BROKER_URL 已配置（验收 vhost）", None


def port_in_use(port: int, timeout: float = 1.0) -> bool:
    """SO_REUSEADDR 探测：bind 成功说明空闲；bind 失败（占用）返回 True。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        sock.close()


def probe_timeout() -> float:
    return float(os.getenv("ZHIJUAN_READINESS_PROBE_TIMEOUT", "2.0"))


def preflight(hooks) -> dict[str, Any]:
    """逐项输出 组件/状态/下一动作；全部通过才 ready=true。只读，无副作用。"""
    timeout = hooks.probe_timeout()
    checked_at = datetime.now(timezone.utc).isoformat()

    budget_payload: dict[str, Any] | None = None
    budget_ok, budget_detail, budget_code = True, "预算接口可达", None
    try:
        budget_payload = hooks.budget_query(min_requests=2)
    except BudgetInsufficientError as exc:
        budget_ok, budget_detail, budget_code = False, str(exc), "BUDGET_INSUFFICIENT"
    except RuntimeError as exc:
        budget_ok, budget_detail, budget_code = False, str(exc), "BUDGET_UNAVAILABLE"

    author_ok, author_detail, author_code = hooks.probe_author(timeout)
    solver_ok, solver_detail, solver_code = hooks.probe_solver(timeout)
    db = hooks.verify_test_database(timeout=timeout)
    broker_ok, broker_detail, broker_code = hooks.broker_url_ok()
    port_busy = hooks.port_in_use(API_PORT)
    port_ok, port_detail, port_code = (not port_busy), (
        f"{API_PORT} 端口空闲" if not port_busy else f"{API_PORT} 端口被占用"), (
        None if not port_busy else "PORT_IN_USE")

    components = {
        "budget": {"ok": budget_ok, "detail": budget_detail, "code": budget_code,
                   "next_action": "配置 ZHIJUAN_BUDGET_PROXY_TOKEN 与 ZHIJUAN_BUDGET_INTERNAL_URL 并启动费用代理（需余量≥2 次）" if not budget_ok and budget_code else "无需操作"},
        "author": {"ok": author_ok, "detail": author_detail, "code": author_code,
                   "next_action": "确认 author 网关（默认 127.0.0.1:8644）已启动且 /health 返回 200" if not author_ok else "无需操作"},
        "solver": {"ok": solver_ok, "detail": solver_detail, "code": solver_code,
                   "next_action": "确认 solver-entry（默认 127.0.0.1:8643）已启动且 /internal/readiness 鉴权可达" if not solver_ok else "无需操作"},
        "database": {"ok": db["ok"], "detail": db["detail"], "code": db["code"],
                     "next_action": db.get("next_action", "无需操作")},
        "broker": {"ok": broker_ok, "detail": broker_detail, "code": broker_code,
                   "next_action": "配置 CELERY_BROKER_URL 指向验收 vhost zhijuan-accept-w6" if not broker_ok else "无需操作"},
        "port_8020": {"ok": port_ok, "detail": port_detail, "code": port_code,
                      "next_action": "释放 8020 端口（预检只读，不代杀进程）" if not port_ok else "无需操作"},
    }

    ready = all(comp["ok"] for comp in components.values())
    result = {
        "tool": "live-single-question-preflight",
        "runtime_id": ACCEPT_RUNTIME_ID,
        "checked_at": checked_at,
        "ready": ready,
        "budget": budget_payload,  # 只含非秘密字段（calls/reserved_cny/…），不含 token
        "components": components,
        "reason_codes": sorted({comp["code"] for comp in components.values() if comp.get("code")}),
    }
    hooks._print_preflight(result)
    return result


def _print_preflight(result: dict[str, Any]) -> None:
    print(f"[preflight] checked_at={result['checked_at']}")
    for name, comp in result["components"].items():
        mark = "OK" if comp["ok"] else "FAIL"
        print(f"  {name:12s} [{mark}] {comp['detail']}")
        if not comp["ok"] and comp.get("next_action"):
            print(f"              -> {comp['next_action']}")
    budget = result.get("budget") or {}
    if budget:
        print(f"  budget      预检快照: calls={budget.get('calls')} reserved_cny={budget.get('reserved_cny')} "
              f"remaining_requests={budget.get('remaining_requests')} remaining_cny={budget.get('remaining_cny')} "
              f"reason_code={budget.get('reason_code')}")
    print(f"[preflight] ready={result['ready']} reason_codes={result['reason_codes']}")
