"""Persistent accounting for the local DeepSeek gateway."""
from __future__ import annotations
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

RUN_NAME = "zhijuan-workflow-20260922"
UPSTREAM = "https://api.deepseek.com/chat/completions"
MAX_BODY_BYTES = 200_000
MAX_OUTPUT_TOKENS = 4096
DEFAULT_LEDGER_PATH = Path("/tmp/zhijuan-workflow-20260922/budget/acceptance.sqlite")
ALLOWED_KEYS = {"model", "messages", "max_tokens", "stream", "temperature", "top_p",
                "response_format", "thinking", "reasoning_effort", "stop"}


RESERVE_CNY = 1


class _LedgerMissingError(RuntimeError):
    """Raised when a required ledger file does not exist yet."""


def reserve(ledger: Path) -> int:
    """Atomically record one request before any upstream I/O.

    Fail-closed bootstrap: a missing ledger file is never silently re-created
    (that would reset historical usage). Provision the ledger explicitly at
    the expected path first; callers treat a missing file as misconfiguration.
    """
    if not ledger.exists():
        raise _LedgerMissingError(
            f"budget ledger does not exist: {ledger}; provision it explicitly before any upstream I/O")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(ledger, timeout=30, isolation_level=None)) as db:
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS budget (name TEXT PRIMARY KEY, calls INTEGER NOT NULL, reserved_cny INTEGER NOT NULL)")
        db.execute("""CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, status TEXT NOT NULL, reserved_cny INTEGER NOT NULL,
            http_status INTEGER, prompt_tokens INTEGER, completion_tokens INTEGER,
            total_tokens INTEGER, provider_model TEXT, provider_request_id TEXT)""")
        db.execute("INSERT OR IGNORE INTO budget VALUES (?, 0, 0)", (RUN_NAME,))
        db.execute("UPDATE budget SET calls=calls+1, reserved_cny=reserved_cny+? WHERE name=?",
                   (RESERVE_CNY, RUN_NAME))
        now = datetime.now(timezone.utc).isoformat()
        reservation_id = db.execute(
            "INSERT INTO reservations (name, created_at, updated_at, status, reserved_cny) VALUES (?, ?, ?, ?, ?)",
            (RUN_NAME, now, now, "RESERVED", RESERVE_CNY)).lastrowid
        db.execute("COMMIT")
    os.chmod(ledger, 0o600)
    return reservation_id


def record_result(ledger: Path, reservation_id: int, status: str, http_status: int | None = None,
                  response: bytes = b"") -> None:
    usage: dict = {}
    provider_model = provider_request_id = None
    content_json_valid = finish_reason = None
    if status == "SUCCEEDED":
        try:
            result = json.loads(response)
            usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
            provider_model = result.get("model")
            provider_request_id = result.get("id")
            choices = result.get("choices") or []
            if choices:
                finish_reason = str(choices[0].get("finish_reason", ""))[:40]
                try:
                    json.loads(choices[0].get("message", {}).get("content", ""))
                    content_json_valid = 1
                except (ValueError, TypeError):
                    content_json_valid = 0
        except (ValueError, AttributeError):
            pass
    def token(key: str) -> int | None:
        value = usage.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
    if status == "SUCCEEDED" and any(token(k) is None for k in (
        "prompt_tokens", "completion_tokens", "total_tokens")):
        status = "SUCCEEDED_USAGE_UNKNOWN"
    with closing(sqlite3.connect(ledger, timeout=30, isolation_level=None)) as db:
        db.execute("BEGIN IMMEDIATE")
        columns = {row[1] for row in db.execute("PRAGMA table_info(reservations)")}
        for name, kind in (("content_json_valid", "INTEGER"), ("finish_reason", "TEXT")):
            if name not in columns:
                db.execute(f"ALTER TABLE reservations ADD COLUMN {name} {kind}")
        db.execute("""UPDATE reservations SET content_json_valid=?, finish_reason=? WHERE id=? AND name=?""",
                   (content_json_valid, finish_reason, reservation_id, RUN_NAME))
        db.execute("""UPDATE reservations SET updated_at=?, status=?, http_status=?,
            prompt_tokens=?, completion_tokens=?, total_tokens=?, provider_model=?, provider_request_id=?
            WHERE id=? AND name=?""", (
            datetime.now(timezone.utc).isoformat(), status, http_status,
            token("prompt_tokens"), token("completion_tokens"), token("total_tokens"),
            provider_model[:200] if isinstance(provider_model, str) else None,
            provider_request_id[:200] if isinstance(provider_request_id, str) else None,
            reservation_id, RUN_NAME))
        db.execute("COMMIT")


