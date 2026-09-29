"""Read-only database, queue, and worker health probes."""
from __future__ import annotations

import os
from services.api.settings import settings


REQUIRED_GENERATION_TABLES = frozenset({
    "generation_exam_state", "generation_exam_revisions", "generation_jobs",
    "generation_job_outbox", "generation_job_results", "generation_job_history",
})


REASON_ORDER = ("NOT_CONFIGURED", "DATABASE_UNAVAILABLE", "BROKER_UNAVAILABLE", "WORKER_UNAVAILABLE",
                "DISPATCHER_UNAVAILABLE", "AUTHOR_UNAVAILABLE", "SOLVER_UNAVAILABLE", "BUDGET_UNAVAILABLE",
                "BUDGET_INSUFFICIENT", "MODEL_MISMATCH", "ISOLATION_MISCONFIG", "HEARTBEAT_STALE")


_DEFAULT_REASON = {
    "database": "DATABASE_UNAVAILABLE", "broker": "BROKER_UNAVAILABLE",
    "worker": "WORKER_UNAVAILABLE", "dispatcher": "DISPATCHER_UNAVAILABLE",
    "author": "AUTHOR_UNAVAILABLE", "solver": "SOLVER_UNAVAILABLE",
    "budget": "BUDGET_UNAVAILABLE",
}


BUDGET_REQUIRED_FIELDS = ("run_id", "calls", "max_requests", "reserved_cny", "max_reserved_cny",
                          "remaining_requests", "remaining_cny", "reserve_per_request_cny",
                          "pending_count", "sufficient", "reason_code", "checked_at")


def runtime_id() -> str:
    return os.getenv("ZHIJUAN_RUNTIME_ID", "zhijuan-local")


def heartbeat_ttl_seconds() -> float:
    return float(os.getenv("ZHIJUAN_HEARTBEAT_TTL_SECONDS", "20"))


def probe_timeout() -> float:
    return float(os.getenv("ZHIJUAN_READINESS_PROBE_TIMEOUT", "2.0"))


def readiness_cache_ttl() -> float:
    return float(os.getenv("ZHIJUAN_READINESS_CACHE_TTL", "3.0"))


def _probe_database(timeout: float) -> dict:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return {"ok": False, "detail": "DATABASE_URL 未配置", "reason": "DATABASE_UNAVAILABLE"}
    try:
        import psycopg
        with psycopg.connect(dsn, connect_timeout=max(1, int(timeout))) as conn:
            row = conn.execute("SELECT 1").fetchone()
            tables = {name for (name,) in conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()")}
    except Exception:
        return {"ok": False, "detail": "无法连接数据库", "reason": "DATABASE_UNAVAILABLE"}
    if row != (1,):
        return {"ok": False, "detail": "数据库连接异常", "reason": "DATABASE_UNAVAILABLE"}
    missing = sorted(REQUIRED_GENERATION_TABLES - tables)
    if missing:
        return {"ok": False, "detail": "缺少表: " + ", ".join(missing), "reason": "DATABASE_UNAVAILABLE"}
    return {"ok": True}


def _probe_broker(timeout: float) -> dict:
    broker_url = os.getenv("CELERY_BROKER_URL", "")
    if not broker_url.startswith(("amqp://", "amqps://")):
        return {"ok": False, "detail": "CELERY_BROKER_URL 未配置或非 AMQP", "reason": "BROKER_UNAVAILABLE"}
    try:
        from kombu import Connection
        # transport_options.connect_timeout caps the socket connect so the
        # probe honors a short timeout even though kombu's ensure_connection
        # timeout argument only bounds retry pacing.
        connection = Connection(broker_url, transport_options={"connect_timeout": timeout})
        try:
            connection.ensure_connection(max_retries=0, timeout=timeout)
        finally:
            connection.release()
    except Exception:
        return {"ok": False, "detail": "无法连接消息队列", "reason": "BROKER_UNAVAILABLE"}
    # A reachable broker does not imply a consumer; worker/dispatcher liveness
    # is judged by their heartbeats, not by this connection probe.
    return {"ok": True}


def _probe_heartbeats(timeout: float) -> dict:
    """Read Worker/Dispatcher heartbeats through contract C2 fresh_components."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        fail = {"ok": False, "detail": "数据库未配置，无法核对组件心跳", "reason": "DATABASE_UNAVAILABLE"}
        return {"worker": fail, "dispatcher": fail}
    try:
        import psycopg
        from services.api.runtime_heartbeats import fresh_components
    except Exception:
        fail = {"ok": False, "detail": "心跳模块不可用", "reason": "WORKER_UNAVAILABLE"}
        return {"worker": fail, "dispatcher": dict(fail, detail="心跳模块不可用", reason="DISPATCHER_UNAVAILABLE")}
    try:
        with psycopg.connect(dsn, connect_timeout=max(1, int(timeout))) as conn:
            fresh = fresh_components(conn, runtime_id(), heartbeat_ttl_seconds())
    except Exception:
        fail = {"ok": False, "detail": "无法读取心跳表", "reason": "WORKER_UNAVAILABLE"}
        return {"worker": fail, "dispatcher": dict(fail, detail="无法读取心跳表", reason="DISPATCHER_UNAVAILABLE")}
    if not isinstance(fresh, dict):
        fail = {"ok": False, "detail": "心跳返回格式异常", "reason": "WORKER_UNAVAILABLE"}
        return {"worker": fail, "dispatcher": dict(fail, detail="心跳返回格式异常", reason="DISPATCHER_UNAVAILABLE")}

    def component_status(component: str) -> dict:
        entry = fresh.get(component)
        component_available = "WORKER_UNAVAILABLE" if component == "worker" else "DISPATCHER_UNAVAILABLE"
        if not isinstance(entry, dict) or entry.get("ok") is not True:
            return {"ok": False, "detail": f"{component} 心跳缺失或已过期", "reason": component_available}
        metadata = entry.get("metadata")
        stale = entry.get("age_seconds")
        if isinstance(stale, (int, float)) and stale >= heartbeat_ttl_seconds():
            return {"ok": False, "detail": f"{component} 心跳已过期", "reason": "HEARTBEAT_STALE"}
        model_id = metadata.get("model_id") if isinstance(metadata, dict) else None
        if model_id and model_id != settings.deepseek_model_id:
            return {"ok": False, "detail": f"{component} 模型不一致", "reason": "MODEL_MISMATCH"}
        return {"ok": True}

    return {"worker": component_status("worker"), "dispatcher": component_status("dispatcher")}


