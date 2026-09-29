"""Read-only budget status endpoint for the local gateway."""
from __future__ import annotations
import hmac
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
try:
    from tools.live_budget_ledger import RUN_NAME, RESERVE_CNY, MAX_OUTPUT_TOKENS
except ModuleNotFoundError:
    from live_budget_ledger import RUN_NAME, RESERVE_CNY, MAX_OUTPUT_TOKENS

class BudgetStatusMixin:
    def models(self, path: str, authorization: str) -> tuple[int, bytes]:
        if not hmac.compare_digest(authorization, f"Bearer {self.internal_token}"):
            return 401, b'{"error":"unauthorized"}'
        if path not in {"/models", "/v1/models"}:
            return 404, b'{"error":"not_found"}'
        return 200, b'{"object":"list","data":[{"id":"deepseek-flash","object":"model","created":0,"owned_by":"deepseek"}]}'

    # ── Internal budget-status endpoint (read-only, C3 contract) ──────────

    def _read_budget_row(self) -> tuple[int, int] | None:
        """Return (calls, reserved_cny) from the budget table, or None."""
        if not self.ledger.exists():
            return None
        with closing(sqlite3.connect(self.ledger, timeout=10, isolation_level=None)) as db:
            row = db.execute(
                "SELECT calls, reserved_cny FROM budget WHERE name=?", (RUN_NAME,)
            ).fetchone()
        return row if row else None

    def _count_pending(self) -> int:
        """Count reservations in RESERVED or UNKNOWN status."""
        if not self.ledger.exists():
            return 0
        with closing(sqlite3.connect(self.ledger, timeout=10, isolation_level=None)) as db:
            row = db.execute(
                "SELECT COUNT(*) FROM reservations WHERE name=? AND status IN (?, ?)",
                (RUN_NAME, "RESERVED", "UNKNOWN"),
            ).fetchone()
        return row[0] if row else 0

    def budget_status(self, authorization: str, query_params: dict[str, str] = None
                      ) -> tuple[int, bytes]:
        """GET /internal/budget — read‑only snapshot of current budget state."""
        if not self.internal_token:
            return 503, json.dumps({
                "error": "budget_proxy_not_configured",
                "reason": "预算代理未启用：ZHIJUAN_BUDGET_PROXY_TOKEN 未配置",
            }, ensure_ascii=False).encode()
        if not hmac.compare_digest(authorization, f"Bearer {self.internal_token}"):
            return 401, b'{"error":"unauthorized"}'

        checked_at = datetime.now(timezone.utc).isoformat()
        row = self._read_budget_row()
        if row is None:
            # Fail closed: a missing/unreadable ledger must not look like a
            # brand-new 20-request/30-CNY quota. Re-read requests must surface
            # BUDGET_UNAVAILABLE so admission cannot proceed on unknown state.
            return 503, json.dumps({
                "error": "budget_proxy_ledger_missing",
                "reason": "预算账本不存在：旧账必须延续，不能换文件清零额度",
            }, ensure_ascii=False).encode()
        calls, reserved_cny = row

        pending_count = self._count_pending()

        # Keep validating the legacy query parameter; it no longer gates calls.
        if query_params and "min_requests" in query_params:
            raw = query_params["min_requests"].strip()
            if not raw.isdigit() or int(raw) < 1:
                return 400, json.dumps({
                    "error": "invalid_min_requests",
                    "reason": "min_requests 必须是正整数",
                }, ensure_ascii=False).encode()

        payload = {
            "run_id": RUN_NAME,
            "output_contract": {"version": "strict-json-v3", "response_format": "strict_function_result",
                                "max_output_tokens": MAX_OUTPUT_TOKENS, "format_retry_limit": 1},
            "calls": calls,
            "max_requests": None,
            "reserved_cny": reserved_cny,
            "max_reserved_cny": None,
            "remaining_requests": None,
            "remaining_cny": None,
            "reserve_per_request_cny": RESERVE_CNY,
            "pending_count": pending_count,
            "limit_enabled": False,
            "sufficient": True,
            "reason_code": "BUDGET_OK",
            "shortfall": {"requests": 0, "cny": 0},
            "estimate_note": "本地请求与金额不设上限；记录只用于对账",
            "checked_at": checked_at,
        }
        return 200, json.dumps(payload, ensure_ascii=False).encode()
