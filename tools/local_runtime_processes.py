"""Local runtime PID ownership checks and child-process helpers."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from tools.local_runtime_config import READY_URLS, ROOT, RUNTIME_DIR, WORKER_MARKERS

def _write_pid_file(kind: str, pid: int) -> Path:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(RUNTIME_DIR, 0o700)
    except OSError:
        pass
    path = RUNTIME_DIR / f"{kind}.pid"
    payload = {"pid": int(pid), "kind": kind,
               "started_at": datetime.now(timezone.utc).isoformat()}
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _read_pid_file(kind: str) -> int | None:
    path = RUNTIME_DIR / f"{kind}.pid"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return int(payload.get("pid"))
    except (ValueError, OSError, TypeError):
        return None


def _remove_pid_file(kind: str) -> None:
    try:
        (RUNTIME_DIR / f"{kind}.pid").unlink(missing_ok=True)
    except OSError:
        pass


def _cmdline_for_pid(pid: int) -> str | None:
    """读取进程命令行（macOS/Linux ps）。失败或不存在返回 None。"""
    try:
        proc = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    line = proc.stdout.strip()
    return line or None


def _terminate_owned(pid: int, grace_seconds: float = 10.0) -> str:
    """对已校验归属的进程发 TERM，超时升级为 KILL（只针对本项目进程）。"""
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


def spawn_process(command: list[str], kind: str) -> subprocess.Popen:
    """用 Python 注入 env 启动子进程；日志落到 .runtime/logs/，工具不回显。"""
    log_dir = RUNTIME_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{kind}.log"
    log_handle = open(log_path, "ab", buffering=0)
    env = dict(os.environ)
    proc = subprocess.Popen(
        command, cwd=str(ROOT), env=env,
        stdin=subprocess.DEVNULL, stdout=log_handle, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    proc._log_handle = log_handle  # type: ignore[attr-defined]
    return proc


def verify_pid_ownership(pid: int, cmdline_for_pid_fn=None) -> tuple[bool, str]:
    """kill 前校验：命令行必须命中 worker/调度器标记，且 PID 文件在本项目 .runtime/ 下。"""
    cmdline = (cmdline_for_pid_fn or _cmdline_for_pid)(pid)
    if not cmdline:
        return False, f"PID {pid} 不存在或无权限读取，拒绝操作"
    if any(marker in cmdline for marker in WORKER_MARKERS):
        return True, f"PID {pid} 命令行「{cmdline[:80]}」属本项目"
    return False, f"PID {pid} 命令行不含 {WORKER_MARKERS}，拒绝 kill"


def readiness_snapshot(timeout: float, *, urlopen_fn=urlopen, ready_urls=READY_URLS) -> dict[str, Any]:
    """GET /readyz（或 /v1/readyz），fail-closed：generation.ready 必须显式为 true。"""
    last_error = None
    for url in ready_urls:
        try:
            req = Request(url, method="GET")
            with urlopen_fn(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            generation = body.get("generation")
            if isinstance(generation, dict) and generation.get("ready") is True:
                return {"ok": True, "generation": generation, "url": url, "error": None}
            return {
                "ok": False,
                "generation": generation,
                "url": url,
                "error": "readyz 未返回 generation.ready=true",
            }
        except Exception as exc:
            last_error = f"{url} 不可用: {type(exc).__name__}"
    return {"ok": False, "generation": None, "url": None, "error": last_error}
