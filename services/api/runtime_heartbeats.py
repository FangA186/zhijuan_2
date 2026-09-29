"""Heartbeat storage helpers. Table schema: database/005_local_runtime_heartbeats.sql."""
from __future__ import annotations

from typing import Any


def upsert_heartbeat(conn, runtime_id: str, component: str, instance_id: str, metadata: dict) -> None:
    """Record a heartbeat for a component instance.

    last_seen_at is always assigned by the database (`now()`), never by the
    application clock, so a clock-skewed process cannot fake freshness.

    Metadata carries only non-secret identifiers: model_id and the gateway role
    endpoint host:port, plus a config-version constant. Never put tokens or keys here.
    """
    conn.execute(
        "INSERT INTO runtime_heartbeats (runtime_id, component, instance_id, metadata) "
        "VALUES (%s, %s, %s, %s::jsonb) "
        "ON CONFLICT (runtime_id, component, instance_id) DO UPDATE SET "
        "last_seen_at = now(), metadata = EXCLUDED.metadata",
        (runtime_id, component, instance_id, _stringify(metadata)),
    )


def fresh_components(conn, runtime_id: str, ttl_seconds: float) -> dict[str, Any]:
    """Return the fresh (not expired) heartbeats for one runtime only.

    Only heartbeats written by the same runtime_id and still younger than
    ``ttl_seconds`` are returned; heartbeats from other deployments or from
    restarted (stale) instances are ignored. Component keys are de-duplicated to
    the most recently seen instance, and each entry carries ok, age_seconds and
    metadata as defined by contract C2.
    """
    # Distinguish expired rows from missing rows: PG returns signed seconds.
    rows = conn.execute(
        "SELECT component, instance_id, last_seen_at, metadata, "
        "EXTRACT(EPOCH FROM (now() - last_seen_at))::float AS age_seconds "
        "FROM runtime_heartbeats WHERE runtime_id = %s",
        (runtime_id,),
    ).fetchall()
    result: dict[str, Any] = {}
    for component, instance_id, last_seen_at, metadata, age_seconds in rows:
        # A heartbeat timestamped in the future is treated as stale, never fresh.
        if age_seconds is None:
            continue
        if age_seconds < 0:
            continue
        previous = result.get(component)
        if previous is not None and previous["age_seconds"] < age_seconds:
            continue
        result[component] = {
            "ok": age_seconds <= ttl_seconds,
            "age_seconds": float(age_seconds),
            "metadata": dict(metadata or {}),
        }
    return result


def _stringify(metadata: dict) -> str:
    import json
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True)
