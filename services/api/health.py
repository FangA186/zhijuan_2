"""Health and readiness probes."""
from __future__ import annotations

import os
import httpx
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi import APIRouter
from services.hermes_adapter.adapter import HermesDeepSeekAdapter

from .health_gateway_probes import _probe_author, _probe_budget, _probe_solver
from .health_probes import (
    BUDGET_REQUIRED_FIELDS, REASON_ORDER, REQUIRED_GENERATION_TABLES, _DEFAULT_REASON,
    _probe_broker, _probe_database, _probe_heartbeats, heartbeat_ttl_seconds,
    probe_timeout, readiness_cache_ttl, runtime_id,
)
from .settings import settings

router = APIRouter(tags=["Health"])


def generation_configuration() -> dict:
    author = os.getenv('HERMES_API_BASE_URL', '').rstrip('/')
    solver = os.getenv('HERMES_SOLVER_API_BASE_URL', '').rstrip('/')
    checks = {
        'database': bool(os.getenv('DATABASE_URL')),
        'queue': os.getenv('CELERY_BROKER_URL', '').startswith(('amqp://', 'amqps://')),
        'author': bool(author and os.getenv('HERMES_API_KEY')),
        'isolated_solver': bool(solver and solver != author and os.getenv('HERMES_SOLVER_API_KEY')),
    }
    return {'configured': all(checks.values()), 'checks': checks, 'runtime_verified': False}

def _config_signature() -> tuple:
    """Environment fingerprint guarding the readiness cache; changing any of
    these values invalidates the cached probe result (never re-serve an old
    green verdict for a different configuration)."""
    return (
        os.getenv("DATABASE_URL"),
        os.getenv("CELERY_BROKER_URL"),
        os.getenv("HERMES_API_BASE_URL"),
        os.getenv("HERMES_API_KEY"),
        os.getenv("HERMES_SOLVER_API_BASE_URL"),
        os.getenv("HERMES_SOLVER_API_KEY"),
        os.getenv("ZHIJUAN_DEEPSEEK_MODEL_ID", "deepseek-chat"),
        settings.deepseek_model_id,
        runtime_id(),
        heartbeat_ttl_seconds(),
        probe_timeout(),
        os.getenv("ZHIJUAN_BUDGET_INTERNAL_URL", "http://127.0.0.1:8650/internal/budget"),
        bool(os.getenv("ZHIJUAN_BUDGET_PROXY_TOKEN")),
    )

_READINESS_CACHE_LOCK = threading.Lock()

_READINESS_CACHE: dict = {}

def clear_readiness_cache() -> None:
    with _READINESS_CACHE_LOCK:
        _READINESS_CACHE.clear()

def runtime_readiness() -> dict:
    """Probe every generation component and build the contract C1 document.

    Results are cached for ZHIJUAN_READINESS_CACHE_TTL (default 3s) so frontend
    polling does not hammer the dependencies; a cache miss re-probes everything
    and the cache entry is fully replaced, so an old ok=true is never carried
    into a failing probe cycle.
    """
    global _READINESS_CACHE
    with _READINESS_CACHE_LOCK:
        cached = _READINESS_CACHE
        if (cached and cached["signature"] == _config_signature()
                and time.monotonic() - cached["checked_at"] < readiness_cache_ttl()):
            return cached["result"]
    result = _probe_all()
    with _READINESS_CACHE_LOCK:
        _READINESS_CACHE = {"signature": _config_signature(), "checked_at": time.monotonic(), "result": result}
    return result

def _probe_all() -> dict:
    configuration = generation_configuration()
    timeout = probe_timeout()

    def run(name: str, future) -> dict:
        try:
            value = future.result(timeout=timeout)
            if isinstance(value, dict):
                return value
        except Exception:
            pass
        return {"ok": False, "detail": f"{name} 探测超时", "reason": _DEFAULT_REASON[name]}

    # "heartbeats" is a composite probe; a timeout degrades both worker and
    # dispatcher instead of calling _DEFAULT_REASON["heartbeats"].
    probe_count = 6
    with ThreadPoolExecutor(max_workers=probe_count) as pool:
        database = run("database", pool.submit(_probe_database, timeout))
        broker = run("broker", pool.submit(_probe_broker, timeout))
        heartbeats_future = pool.submit(_probe_heartbeats, timeout)
        try:
            raw_heartbeat = heartbeats_future.result(timeout=timeout)
            if not isinstance(raw_heartbeat, dict):
                raw_heartbeat = None
        except Exception:
            raw_heartbeat = None
        author = run("author", pool.submit(_probe_author, timeout))
        solver = run("solver", pool.submit(_probe_solver, timeout))
        budget = run("budget", pool.submit(_probe_budget, timeout))

    def heartbeat_status(component: str) -> dict:
        if raw_heartbeat is not None and component in raw_heartbeat and isinstance(raw_heartbeat[component], dict):
            entry = raw_heartbeat[component]
            if entry.get("ok") is True:
                return entry
            if "reason" not in entry:
                entry = dict(entry, reason=_DEFAULT_REASON[component])
            return entry
        return {"ok": False, "detail": f"{component} 心跳检查失败", "reason": _DEFAULT_REASON[component]}

    worker = heartbeat_status("worker")
    dispatcher = heartbeat_status("dispatcher")

    # author==solver (including a trailing-slash-only difference) is always a
    # misconfiguration, even when both endpoints happen to answer.
    author_base = os.getenv("HERMES_API_BASE_URL", "").rstrip("/") or None
    solver_base = os.getenv("HERMES_SOLVER_API_BASE_URL", "").rstrip("/") or None
    if author_base and solver_base and author_base == solver_base:
        solver = {"ok": False, "detail": "author 与 solver 指向同一网关", "reason": "ISOLATION_MISCONFIG"}

    probes = {"database": database, "broker": broker, "worker": worker, "dispatcher": dispatcher,
              "author": author, "solver": solver, "budget": budget}
    components = {name: {key: value for key, value in probe.items() if key != "reason"}
                  for name, probe in probes.items()}

    reasons = []
    for probe in probes.values():
        if probe.get("reason") and probe["reason"] not in reasons:
            reasons.append(probe["reason"])
    if not configuration["configured"] and "NOT_CONFIGURED" not in reasons:
        reasons.append("NOT_CONFIGURED")
    reasons.sort(key=lambda code: REASON_ORDER.index(code))

    configured = configuration["configured"]
    return {
        "configured": configured,
        "checks": configuration["checks"],
        "runtime_verified": True,
        "ready": configured and not reasons,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "reason_codes": reasons,
        "components": components,
    }

@router.get("/health")
@router.get("/healthz")
@router.get("/v1/health")
def liveness():
    adapter = HermesDeepSeekAdapter(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        default_model=settings.deepseek_model_id,
    )
    health = adapter.health()
    return {
        "status": "HEALTHY",
        "service": settings.app_title,
        "version": settings.app_version,
        "hermes": health,
        "generation": generation_configuration(),
    }

@router.get("/readyz")
@router.get("/v1/readyz")
def readiness():
    generation = runtime_readiness()
    if not generation["configured"]:
        status = "NOT_CONFIGURED"
    elif generation["ready"]:
        status = "READY"
    else:
        status = "NOT_READY"
    return {
        "status": status,
        "model_configured": bool(settings.deepseek_api_key),
        "generation": generation,
    }
