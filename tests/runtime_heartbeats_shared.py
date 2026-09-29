"""Offline tests for the runtime heartbeat storage helpers and background loops.

All checks run without a PostgreSQL server: the heartbeat SQL is exercised
through a minimal in-memory SQLite stand-in whose surface matches the
`upsert_heartbeat` / `fresh_components` contracts, and the thread / scheduler
loops are driven with injected poll functions instead of real connections.
Real-PostgreSQL integration coverage is owned by the main verification flow
and deliberately does not belong in this file.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import unittest
from unittest.mock import patch

from services.api.runtime_heartbeats import upsert_heartbeat, fresh_components
from services.worker.heartbeat import (
    HeartbeatThread,
    instance_id,
    runtime_id,
    gateway_role_fingerprint,
    GATEWAY_ROLE_CONFIG_VERSION,
)


class _SqliteHeartbeatStub:
    """Adapter between the C2 function calls and an in-memory SQLite stand-in.

    Emulates the PG behaviour that matters for the contracts: the DB owns the
    timestamp (a monotonic clock advanced inside the stub, standing in for
    PG's now()), last_seen_at is not settable by the caller, re-inserts update
    the existing row instead of duplicating, and ages are signed seconds with
    missing rows simply absent from the result set. Tests may reposition
    ``_clock`` directly to simulate the passage of time.
    """

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            "CREATE TABLE runtime_heartbeats ("
            " runtime_id text NOT NULL,"
            " component text NOT NULL,"
            " instance_id text NOT NULL,"
            " last_seen_at_epoch real NOT NULL,"
            " metadata_json text NOT NULL DEFAULT '{}',"
            " UNIQUE (runtime_id, component, instance_id)"
            ")"
        )
        self._lock = threading.RLock()
        self._clock = 0.0

    def now(self) -> float:
        """DB-side timestamp: monotonically advancing, never app-controllable."""
        with self._lock:
            self._clock += 1.0
            return self._clock

    def execute(self, sql, params=()):
        upper = sql.strip().upper()
        if upper.startswith("INSERT INTO RUNTIME_HEARTBEATS"):
            runtime_id, component, instance_id, metadata_json = params
            with self._lock:
                write_at = self.now()
                self.conn.execute(
                    "INSERT INTO runtime_heartbeats "
                    "(runtime_id, component, instance_id, last_seen_at_epoch, metadata_json) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT (runtime_id, component, instance_id) DO UPDATE SET "
                    "last_seen_at_epoch = excluded.last_seen_at_epoch, metadata_json = excluded.metadata_json",
                    (runtime_id, component, instance_id, write_at, metadata_json),
                )
            self.conn.commit()
            return _ResultStub()
        if upper.startswith("SELECT COMPONENT"):
            with self._lock:
                read_at = self.now()
                rows = self.conn.execute(
                    "SELECT component, instance_id, last_seen_at_epoch, metadata_json "
                    "FROM runtime_heartbeats WHERE runtime_id = ?",
                    (params[0],),
                ).fetchall()
            results = []
            for component, instance_id, last_epoch, metadata_json in rows:
                results.append((component, instance_id, last_epoch,
                                json.loads(metadata_json), read_at - last_epoch))
            return _RowsStub(results)
        raise AssertionError(f"unexpected SQL in stub: {sql}")


class _ResultStub:
    def fetchone(self):
        return None


class _RowsStub:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows



__all__ = [name for name in globals() if not name.startswith("__")]
