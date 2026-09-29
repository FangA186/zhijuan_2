#!/usr/bin/env python3
"""知卷 L01 单题真实链路受控运行工具（preflight / run）。"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.local_runtime_config import load_dotenv, parse_env_key_value
from tools.live_single_question_config import (
    ACCEPT_RUNTIME_ID, API_BASE, API_PORT, API_MARKERS, ENV_PATH, GENERATION_TABLES,
    LOG_DIR, NOT_RESPONSIBLE_STATUSES, REPORT_DIR, REPORT_PATH, REQUIRED_TABLES,
    ROOT, RUNTIME_DIR, TERMINAL_JOB_STATUSES, TEST_DATABASE_NAME, TEST_VHOST, WORKER_MARKERS,
)
from tools.live_single_question_budget import BudgetInsufficientError
from tools import live_single_question_acceptance as _acceptance
from tools import live_single_question_budget as _budget
from tools import live_single_question_evidence as _evidence
from tools import live_single_question_preflight as _preflight
from tools import live_single_question_processes as _processes
from tools import live_single_question_runner as _runner


def _http_get(url: str, *, timeout: float, token: str | None = None, headers: dict[str, str] | None = None):
    return _budget.http_get(url, timeout=timeout, token=token, headers=headers, urlopen_fn=urlopen)


def _budget_endpoint() -> str:
    return _budget._budget_endpoint()


def budget_query(min_requests: int, *, require_sufficient: bool = True) -> dict[str, Any]:
    return _budget.budget_query(min_requests, require_sufficient=require_sufficient, hooks=sys.modules[__name__])


def verify_test_database(timeout: float = 6.0):
    return _preflight.verify_test_database(timeout)


def probe_author(timeout: float):
    return _preflight.probe_author(timeout, sys.modules[__name__])


def probe_solver(timeout: float):
    return _preflight.probe_solver(timeout, sys.modules[__name__])


def broker_url_ok():
    return _preflight.broker_url_ok()


def port_in_use(port: int, timeout: float = 1.0) -> bool:
    return _preflight.port_in_use(port, timeout)


def probe_timeout() -> float:
    return _preflight.probe_timeout()


def preflight() -> dict[str, Any]:
    return _preflight.preflight(sys.modules[__name__])


def _print_preflight(result: dict[str, Any]) -> None:
    return _preflight._print_preflight(result)


def api_command() -> list[str]:
    return _processes.api_command()


def worker_command() -> list[str]:
    return _processes.worker_command()


def scheduler_command() -> list[str]:
    return _processes.scheduler_command()


def child_env(*, broker: str | None = None) -> dict[str, str]:
    return _processes.child_env(broker=broker)


def spawn_process(command: list[str], kind: str, env: dict[str, str], log_name: str | None = None):
    return _processes.spawn_process(command, kind, env, log_name)


def verify_pid_ownership(pid: int, markers: tuple[str, ...] = WORKER_MARKERS):
    return _processes.verify_pid_ownership(pid, markers)


def terminate_owned(pid: int, grace_seconds: float = 10.0) -> str:
    return _processes.terminate_owned(pid, grace_seconds)


def wait_heartbeats(test_dsn: str, *, timeout: float = 60.0, interval: float = 1.0) -> dict:
    return _processes.wait_heartbeats(test_dsn, timeout=timeout, interval=interval)


def build_seed_spec() -> dict:
    return _acceptance.build_seed_spec()


def _http_request(method: str, api_base: str, path: str, *, timeout: float, headers: dict[str, str] | None = None, body: Any = None):
    return _acceptance.http_request(method, api_base, path, timeout=timeout, headers=headers, body=body, urlopen_fn=urlopen)


def run_acceptance_chain(api_base: str, seed_spec: dict, *, timeout: float = 30.0) -> dict[str, Any]:
    return _acceptance.run_acceptance_chain(api_base, seed_spec, timeout=timeout, hooks=sys.modules[__name__])


def poll_job(test_dsn: str, job_id: str, *, timeout: float = 900.0, interval: float = 2.0) -> dict[str, Any]:
    return _evidence.poll_job(test_dsn, job_id, timeout=timeout, interval=interval)


def job_evidence(job: dict[str, Any], results_rows: list[dict[str, Any]]) -> dict[str, Any]:
    return _evidence.job_evidence(job, results_rows)


def run(out_path: Path = REPORT_PATH) -> dict[str, Any]:
    return _runner.run(sys.modules[__name__], out_path)


def _int_or_none(value: Any) -> int:
    return _runner._int_or_none(value)


def _terminate_all(procs: dict[str, subprocess.Popen]) -> None:
    return _runner.terminate_all(sys.modules[__name__], procs)


def write_report(out_path: Path, result: dict[str, Any]) -> None:
    return _runner.write_report(sys.modules[__name__], out_path, result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="知卷 L01 单题真实链路受控运行工具（preflight=只读预检；run=执行一次单题真实验收）")
    parser.add_argument("command", choices=("preflight", "run"))
    args = parser.parse_args(argv)
    load_dotenv()
    if args.command == "preflight":
        result = preflight()
        return 0 if result["ready"] else 1
    result = run()
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
