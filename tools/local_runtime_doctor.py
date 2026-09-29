"""Readiness aggregation and safe doctor output."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from tools.local_runtime_config import ALLOWED_CONTAINERS

def _next_action_for(name: str, ok: bool, code: str | None, detail: str) -> str:
    if ok:
        return "无需操作"
    if name == "api":
        return "在仓库根启动 API（本工具不代启 API/Vite）：.venv/bin/uvicorn services.api.main:app --port 8000"
    if name == "database":
        if code == "NOT_CONFIGURED":
            return "在 configs/local-runtime.env.example 配置 DATABASE_URL"
        return "确认 PG 容器 zhijuan-workflow-20260922-pg 运行中且 database/*.sql 迁移已执行"
    if name == "broker":
        if code == "NOT_CONFIGURED":
            return "配置 CELERY_BROKER_URL（指向 amqp://…/zhijuan-local）"
        return "运行 tools/local_runtime.py start-generation 会尝试 docker start zhijuan-workflow-20260922-mq（仅当其 Exited）"
    if name in ("worker", "dispatcher"):
        return "运行 tools/local_runtime.py start-generation 启动 Worker 与调度器"
    if name == "author":
        return "确认 author 网关（默认 127.0.0.1:8644）已启动"
    if name == "solver":
        return "确认 solver-entry（默认 127.0.0.1:8643）已启动"
    if name == "budget":
        return "启动费用代理并配置 ZHIJUAN_BUDGET_PROXY_TOKEN（C3 只读 /internal/budget）"
    return f"{name} 失败: {detail}"


def doctor(hooks) -> dict[str, Any]:
    """只读健康巡诊：输出组件名/状态/下一动作，不输出任何秘密。"""
    timeout = float(os.getenv("ZHIJUAN_READINESS_PROBE_TIMEOUT", "2.0"))
    runtime_id = os.getenv("ZHIJUAN_RUNTIME_ID", "zhijuan-local")
    checked_at = datetime.now(timezone.utc).isoformat()

    probes: list[tuple[str, tuple[bool, str, str | None]]] = [
        ("database", hooks.database_check(os.getenv("DATABASE_URL"), timeout)),
        ("broker", hooks.broker_check(timeout)),
        ("worker", hooks.heartbeat_check("worker", timeout)),
        ("dispatcher", hooks.heartbeat_check("dispatcher", timeout)),
        ("author", hooks.tcp_base_check(os.getenv("HERMES_API_BASE_URL"), timeout, "author")),
        ("solver", hooks.tcp_base_check(os.getenv("HERMES_SOLVER_API_BASE_URL"), timeout, "solver")),
        ("budget", hooks.budget_check(timeout)),
    ]
    api_ok, api_detail = hooks.api_health(timeout)

    components: dict[str, Any] = {}
    for name, (ok, detail, code) in probes:
        components[name] = {"ok": ok, "detail": detail,
                            "next_action": hooks._next_action_for(name, ok, code, detail)}
    components["api"] = {"ok": api_ok, "detail": api_detail,
                         "next_action": hooks._next_action_for("api", api_ok, None, api_detail)}

    reason_codes: list[str] = []
    for name, (ok, detail, code) in probes:
        if not ok and code:
            if code not in reason_codes:
                reason_codes.append(code)

    containers: dict[str, str] = {}
    for name in ALLOWED_CONTAINERS:
        state, status_line = hooks.container_state(name)
        containers[name] = status_line

    ready = api_ok and all(components[name]["ok"] for name, _ in probes)
    result = {
        "tool": "local_runtime-doctor",
        "runtime_id": runtime_id,
        "checked_at": checked_at,
        "ready": ready,
        "reason_codes": reason_codes,
        "containers": containers,
        "components": components,
    }
    hooks._print_doctor(result)
    return result


def _print_doctor(result: dict[str, Any]) -> None:
    print(f"[doctor] checked_at={result['checked_at']}")
    for name, comp in result["components"].items():
        mark = "OK" if comp["ok"] else "FAIL"
        print(f"  {name:10s} [{mark}] {comp['detail']}")
        if not comp["ok"] and comp.get("next_action"):
            print(f"            -> {comp['next_action']}")
    for name, status_line in result["containers"].items():
        print(f"  容器     {status_line}")
    print(f"[doctor] ready={result['ready']} reason_codes={result['reason_codes']}")
