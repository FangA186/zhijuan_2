import json
import sqlite3
import os
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tools.live_budget_proxy import BudgetProxy, MAX_BODY_BYTES, RUN_NAME, RESERVE_CNY


def body(**overrides):
    value = {"model": "deepseek-flash", "messages": [{"role": "user", "content": "hello"}]}
    value.update(overrides)
    return json.dumps(value).encode()


def provision_ledger(ledger: Path):
    """Explicitly provision a fresh ledger file, as an operator would before
    starting the proxy. A missing file must never be auto-created by reserve."""
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ledger, timeout=10, isolation_level=None)) as db:
        db.execute("PRAGMA busy_timeout=3000")
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS budget (name TEXT PRIMARY KEY, calls INTEGER NOT NULL, reserved_cny INTEGER NOT NULL)")
        db.execute("""CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, status TEXT NOT NULL, reserved_cny INTEGER NOT NULL,
            http_status INTEGER, prompt_tokens INTEGER, completion_tokens INTEGER,
            total_tokens INTEGER, provider_model TEXT, provider_request_id TEXT)""")
        db.execute("INSERT OR IGNORE INTO budget VALUES (?, 0, 0)", (RUN_NAME,))
        db.execute("COMMIT")


def _seed_ledger(ledger: Path, calls: int, reserved_cny: int, status: str = "RESERVED") -> None:
    """Pre-populate a ledger for testing budget-status read-back."""
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ledger, timeout=10, isolation_level=None)) as db:
        db.execute("PRAGMA busy_timeout=3000")
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS budget (name TEXT PRIMARY KEY, calls INTEGER NOT NULL, reserved_cny INTEGER NOT NULL)")
        db.execute("""CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, status TEXT NOT NULL, reserved_cny INTEGER NOT NULL,
            http_status INTEGER, prompt_tokens INTEGER, completion_tokens INTEGER,
            total_tokens INTEGER, provider_model TEXT, provider_request_id TEXT)""")
        db.execute("INSERT OR IGNORE INTO budget VALUES (?, 0, 0)", (RUN_NAME,))
        db.execute("UPDATE budget SET calls=?, reserved_cny=? WHERE name=?", (calls, reserved_cny, RUN_NAME))
        now = "2026-09-23T00:00:00+00:00"
        for i in range(calls):
            db.execute("""INSERT INTO reservations (name, created_at, updated_at, status, reserved_cny)
                          VALUES (?, ?, ?, ?, ?)""",
                       (RUN_NAME, now, now, status, RESERVE_CNY))
        db.execute("COMMIT")

__all__ = [name for name in globals() if not name.startswith("__")]
