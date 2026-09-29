"""Child commands, isolated environment, heartbeat wait, and owned PID cleanup."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.live_single_question_config import (ACCEPT_RUNTIME_ID, API_PORT, API_MARKERS, LOG_DIR, ROOT, RUNTIME_DIR, WORKER_MARKERS)

def api_command() -> list[str]:
    return [str(ROOT / ".venv/bin/uvicorn"), "services.api.main:app",
            "--host", "127.0.0.1", "--port", str(API_PORT)]


def worker_command() -> list[str]:
    return [str(ROOT / ".venv/bin/celery"), "-A", "services.worker.jobs:app", "worker",
            "--pool=solo", "--concurrency=1", "--without-gossip",
            "--without-mingle", "--without-heartbeat", "--loglevel=INFO"]


def scheduler_command() -> list[str]:
    return [str(ROOT / ".venv/bin/python"), "-m", "services.worker.scheduler"]


def child_env(*, broker: str | None = None) -> dict[str, str]:
    """构造子进程 env：显式注入验收参数；绝不从父进程环境继承 8000 服务。

    键名与 AGENTS/实施计划 §6.2 一致；ZHIJUAN_SKIP_DOTENV=1 使子进程
    （settings.py、store.py 等）不再自行读 .env，而是完全使用注入值。
    """
    dsn = os.getenv("ZHIJUAN_TEST_DATABASE_URL", "")
    required = {
        "DATABASE_URL": dsn,
        "ZHIJUAN_TEST_DATABASE_URL": dsn,
        "HERMES_API_BASE_URL": os.getenv("HERMES_API_BASE_URL", ""),
        "HERMES_API_KEY": os.getenv("HERMES_API_KEY", ""),
        "HERMES_SOLVER_API_BASE_URL": os.getenv("HERMES_SOLVER_API_BASE_URL", ""),
        "HERMES_SOLVER_API_KEY": os.getenv("HERMES_SOLVER_API_KEY", ""),
        "ZHIJUAN_BUDGET_INTERNAL_URL": os.getenv("ZHIJUAN_BUDGET_INTERNAL_URL", ""),
        "ZHIJUAN_BUDGET_PROXY_TOKEN": os.getenv("ZHIJUAN_BUDGET_PROXY_TOKEN", ""),
        "ZHIJUAN_RUNTIME_ID": ACCEPT_RUNTIME_ID,
        "ZHIJUAN_SKIP_DOTENV": "1",
        "ZHIJUAN_DEEPSEEK_MODEL_ID": os.getenv("ZHIJUAN_DEEPSEEK_MODEL_ID", "deepseek-flash"),
        "ZHIJUAN_HEARTBEAT_TTL_SECONDS": os.getenv("ZHIJUAN_HEARTBEAT_TTL_SECONDS", "20"),
    }
    if broker:
        required["CELERY_BROKER_URL"] = broker
    return required


def spawn_process(command: list[str], kind: str, env: dict[str, str],
                  log_name: str | None = None) -> subprocess.Popen:
    """启动一个子进程；日志追加写 .runtime/logs/<log_name>.log（不解析、不回显）。"""
    log_dir = LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(RUNTIME_DIR, 0o700)
    except OSError:
        pass
    log_path = log_dir / f"{log_name or kind}.log"
    log_handle = open(log_path, "ab", buffering=0)
    full_env = dict(os.environ)
    full_env.update(env)
    proc = subprocess.Popen(
        command, cwd=str(ROOT), env=full_env,
        stdin=subprocess.DEVNULL, stdout=log_handle, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    proc._log_handle = log_handle  # type: ignore[attr-defined]
    return proc


def verify_pid_ownership(pid: int, markers: tuple[str, ...] = WORKER_MARKERS) -> tuple[bool, str]:
    """kill 前校验 PID 命令行归属（复用 local_runtime.verify_pid_ownership 等价逻辑）。"""
    try:
        proc = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, f"PID {pid} 查询失败，拒绝操作"
    if proc.returncode != 0:
        return False, f"PID {pid} 不存在或无权限读取，拒绝操作"
    cmdline = proc.stdout.strip()
    if not cmdline:
        return False, f"PID {pid} 无命令行，拒绝操作"
    if any(marker in cmdline for marker in markers):
        return True, f"PID {pid} 命令行「{cmdline[:80]}」属本项目"
    return False, f"PID {pid} 命令行不含 {markers}，拒绝 kill"


def terminate_owned(pid: int, grace_seconds: float = 10.0) -> str:
    """对已校验归属的进程 TERM，超时升级 KILL（只针对本项目进程）。"""
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return f"PID {pid} 已退出"
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return f"PID {pid} 已终止（TERM）"
        except PermissionError:
            return f"PID {pid} 存在但无权限，未强杀"
        time.sleep(0.2)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return f"PID {pid} 已退出"
    return f"PID {pid} 已强杀（KILL，TERM 超时）"


def wait_heartbeats(test_dsn: str, *, timeout: float = 60.0, interval: float = 1.0) -> dict:
    """等测试库 runtime_heartbeats 出现新鲜的 worker 与 dispatcher 心跳。

    超时失败抛 RuntimeError（由 run 负责清理尚未回收的本次进程）。
    runtime_id=zhijuan-accept-l01，TTL=20s（fresh_components 判定）。
    """
    # 以脚本方式运行时 sys.path[0] 为 tools/，需显式把仓库根加入（与
    # local_runtime.py 的心跳检查同款处理），才能 import services.*。
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    from services.api.runtime_heartbeats import fresh_components
    import psycopg
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        with psycopg.connect(test_dsn, connect_timeout=10) as conn:
            fresh = fresh_components(conn, ACCEPT_RUNTIME_ID, 20.0)
        last = fresh
        if fresh.get("worker", {}).get("ok") and fresh.get("dispatcher", {}).get("ok"):
            return {
                "ok": True,
                "detail": f"worker/dispatcher 心跳新鲜"
                          f"（worker age={fresh['worker'].get('age_seconds'):.1f}s, "
                          f"dispatcher age={fresh['dispatcher'].get('age_seconds'):.1f}s）",
                "heartbeats": {k: dict(v) for k, v in fresh.items()},
            }
        time.sleep(interval)
    missing = [name for name in ("worker", "dispatcher") if not last.get(name, {}).get("ok")]
    raise RuntimeError(f"心跳等待超时（{timeout:.0f}s），缺失/过期: {missing}")
