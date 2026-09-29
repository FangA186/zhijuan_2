"""Read-only author, solver, and budget gateway probes."""
from __future__ import annotations

import os
import httpx
from .health_probes import BUDGET_REQUIRED_FIELDS


def _probe_author(timeout: float) -> dict:
    base_url = os.getenv("HERMES_API_BASE_URL", "").rstrip("/")
    if not base_url:
        return {"ok": False, "detail": "author 网关地址未配置", "reason": "AUTHOR_UNAVAILABLE"}
    # vendor/hermes-agent/gateway/platforms/api_server.py registers a real,
    # unauthenticated, free GET /health (line ~1537/_handle_health).
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.get(base_url + "/health")
    except Exception:
        return {"ok": False, "detail": "无法连接 author 网关", "reason": "AUTHOR_UNAVAILABLE"}
    if response.status_code != 200:
        return {"ok": False, "detail": f"author 网关状态异常 HTTP {response.status_code}", "reason": "AUTHOR_UNAVAILABLE"}
    return {"ok": True}


def _probe_solver(timeout: float) -> dict:
    base_url = os.getenv("HERMES_SOLVER_API_BASE_URL", "").rstrip("/")
    api_key = os.getenv("HERMES_SOLVER_API_KEY", "")
    if not base_url or not api_key:
        return {"ok": False, "detail": "solver 网关未配置", "reason": "SOLVER_UNAVAILABLE"}
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.get(base_url + "/internal/readiness",
                                  headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
    except Exception:
        return {"ok": False, "detail": "无法连接 solver 网关", "reason": "SOLVER_UNAVAILABLE"}
    if response.status_code != 200:
        return {"ok": False, "detail": f"solver 网关状态异常 HTTP {response.status_code}", "reason": "SOLVER_UNAVAILABLE"}
    # A reachable gateway does not prove the isolated upstream is usable: the
    # gateway itself reports upstream_configured (non-secret) and we fail closed
    # unless the body confirms both status==OK and upstream_configured==true.
    try:
        data = response.json()
    except ValueError:
        return {"ok": False, "detail": "solver 就绪响应不是合法 JSON", "reason": "SOLVER_UNAVAILABLE"}
    if not isinstance(data, dict) or data.get("status") != "OK" or data.get("upstream_configured") is not True:
        return {"ok": False, "detail": "solver 网关上游未配置或就绪响应缺字段", "reason": "SOLVER_UNAVAILABLE"}
    return {"ok": True}


def _probe_budget(timeout: float) -> dict:
    url = os.getenv("ZHIJUAN_BUDGET_INTERNAL_URL", "http://127.0.0.1:8650/internal/budget")
    token = os.getenv("ZHIJUAN_BUDGET_PROXY_TOKEN", "")
    if not token:
        return {"ok": False, "detail": "预算代理令牌未配置", "reason": "BUDGET_UNAVAILABLE"}
    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            response = client.get(url + "?min_requests=1",
                                  headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
    except Exception:
        return {"ok": False, "detail": "预算代理不可达", "reason": "BUDGET_UNAVAILABLE"}
    if response.status_code != 200:
        return {"ok": False, "detail": f"预算代理状态异常 HTTP {response.status_code}", "reason": "BUDGET_UNAVAILABLE"}
    try:
        data = response.json()
    except ValueError:
        return {"ok": False, "detail": "预算响应不是合法 JSON", "reason": "BUDGET_UNAVAILABLE"}
    if not isinstance(data, dict) or any(field not in data for field in BUDGET_REQUIRED_FIELDS):
        return {"ok": False, "detail": "预算响应缺少必要字段", "reason": "BUDGET_UNAVAILABLE"}
    if not isinstance(data["sufficient"], bool) or data["reason_code"] not in ("BUDGET_OK", "BUDGET_INSUFFICIENT"):
        return {"ok": False, "detail": "预算响应字段非法", "reason": "BUDGET_UNAVAILABLE"}
    if data["sufficient"] is False:
        # Budget service is reachable but has no headroom: distinct code so the
        # front end can explain, but the component is not usable for generation.
        return {"ok": False, "detail": "预算额度不足", "reason": "BUDGET_INSUFFICIENT"}
    return {"ok": True}


