"""本地运行接线工具：doctor / start-generation / stop-generation。"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.request import urlopen

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.local_runtime_config import (
    ACTIVE_JOB_STATUSES, ALLOWED_CONTAINERS, API_HEALTH_URL, BROKER_HOST, BROKER_PORT,
    ENV_PATH, GENERATION_TABLES, MQ_CONTAINER, PG_CONTAINER, READY_URLS, ROOT,
    RUNTIME_DIR, VHOST, WORKER_MARKERS, load_dotenv, parse_env_key_value,
)
from tools import local_runtime_broker as _broker
from tools import local_runtime_doctor as _doctor
from tools import local_runtime_generation as _generation
from tools import local_runtime_processes as _processes
from tools import local_runtime_probes as _probes


def api_health(timeout: float):
    return _probes.api_health(timeout, urlopen_fn=urlopen)


def database_check(dsn: str | None, timeout: float):
    return _probes.database_check(dsn, timeout)


def broker_check(timeout: float):
    return _probes.broker_check(timeout)


def heartbeat_check(component: str, timeout: float):
    return _probes.heartbeat_check(component, timeout)


def tcp_base_check(base_url: str | None, timeout: float, label: str):
    return _probes.tcp_base_check(base_url, timeout, label)


def budget_check(timeout: float):
    return _probes.budget_check(timeout, urlopen_fn=urlopen)


def container_state(name: str, timeout: float = 10.0):
    return _probes.container_state(name, timeout)


def _next_action_for(name: str, ok: bool, code: str | None, detail: str):
    return _doctor._next_action_for(name, ok, code, detail)


def _print_doctor(result: dict[str, Any]) -> None:
    return _doctor._print_doctor(result)


def doctor() -> dict[str, Any]:
    return _doctor.doctor(sys.modules[__name__])


def _broker_user() -> str:
    return _broker._broker_user()


def docker_exec_mq(ctl_args: list[str], timeout: float = 30.0):
    return _broker.docker_exec_mq(ctl_args, timeout)


def _ensure_vhost():
    return _broker.ensure_vhost(broker_user_fn=_broker_user, docker_exec_mq_fn=docker_exec_mq)


def _wait_amqp_ready(timeout: float = 30.0, interval: float = 1.0) -> bool:
    return _broker._wait_amqp_ready(timeout, interval)


def _write_pid_file(kind: str, pid: int) -> Path:
    return _processes._write_pid_file(kind, pid)


def _read_pid_file(kind: str) -> int | None:
    return _processes._read_pid_file(kind)


def _remove_pid_file(kind: str) -> None:
    return _processes._remove_pid_file(kind)


def _cmdline_for_pid(pid: int) -> str | None:
    return _processes._cmdline_for_pid(pid)


def verify_pid_ownership(pid: int):
    return _processes.verify_pid_ownership(pid, _cmdline_for_pid)


def _terminate_owned(pid: int, grace_seconds: float = 10.0) -> str:
    return _processes._terminate_owned(pid, grace_seconds)


def spawn_process(command: list[str], kind: str):
    return _processes.spawn_process(command, kind)


def _readiness_snapshot(timeout: float):
    return _processes.readiness_snapshot(timeout, urlopen_fn=urlopen, ready_urls=READY_URLS)


def start_generation() -> dict[str, Any]:
    return _generation.start_generation(sys.modules[__name__])


def _recycle_newly_started(*procs: subprocess.Popen | None) -> None:
    return _generation.recycle_newly_started(sys.modules[__name__], *procs)


def _active_jobs():
    return _generation._active_jobs()


def stop_generation() -> dict[str, Any]:
    return _generation.stop_generation(sys.modules[__name__])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="知卷本地运行接线工具（doctor = 只读巡检；start-generation / stop-generation = 启停 Worker+调度器）")
    parser.add_argument("command", choices=("doctor", "start-generation", "stop-generation"))
    args = parser.parse_args(argv)
    load_dotenv()
    if args.command == "doctor":
        result = doctor()
        return 0 if result.get("ready") else 1
    result = start_generation() if args.command == "start-generation" else stop_generation()
    print(json.dumps({k: v for k, v in result.items() if k != "detail"}, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
