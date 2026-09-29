"""Read-only budget status checks."""
from tests.live_budget_proxy_shared import *

class BudgetStatusInternalTests(unittest.TestCase):
    """Tests for the read-only GET /internal/budget endpoint (C3 contract)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / "budget.sqlite"
        provision_ledger(self.ledger)
        # Proxy with a token configured
        self.proxy = BudgetProxy(self.ledger, "internal-token", "provider-key",
                                 lambda p, k: (200, b"{}"))

    def _status(self, query_params: dict[str, str] | None = None,
                auth: str | None = None) -> tuple[int, any]:
        """Call budget_status and return (status_code, parsed_json)."""
        auth = auth or "Bearer internal-token"
        status, payload = self.proxy.budget_status(auth, query_params)
        return status, json.loads(payload)

    # ── Auth / availability ──────────────────────────────────────────────

    def test_no_token_returns_503(self):
        """Proxy with empty internal_token returns 503 for /internal/budget."""
        proxy = BudgetProxy(self.ledger, "", "provider-key", lambda p, k: (200, b"{}"))
        status, payload = proxy.budget_status("Bearer anything")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(payload)["error"], "budget_proxy_not_configured")

    def test_wrong_token_returns_401(self):
        """Invalid Bearer token returns 401."""
        status, _ = self._status(auth="Bearer wrong-token")
        self.assertEqual(status, 401)

    def test_missing_bearer_prefix_returns_401(self):
        """Authorization header without Bearer prefix returns 401."""
        status, _ = self._status(auth="internal-token")
        self.assertEqual(status, 401)

    # ── Empty / fresh ledger ─────────────────────────────────────────────

    def test_fresh_ledger_returns_zeros(self):
        """A provisioned-but-virgin ledger returns calls=0, reserved_cny=0."""
        status, data = self._status()
        self.assertEqual(status, 200)
        self.assertEqual(data["calls"], 0)
        self.assertEqual(data["reserved_cny"], 0)
        self.assertIsNone(data["max_requests"])
        self.assertIsNone(data["max_reserved_cny"])
        self.assertIsNone(data["remaining_requests"])
        self.assertIsNone(data["remaining_cny"])
        self.assertFalse(data["limit_enabled"])
        self.assertEqual(data["reserve_per_request_cny"], RESERVE_CNY)
        self.assertEqual(data["pending_count"], 0)
        self.assertTrue(data["sufficient"])
        self.assertEqual(data["reason_code"], "BUDGET_OK")
        self.assertIn("checked_at", data)
        self.assertEqual(data["run_id"], RUN_NAME)

    def test_missing_ledger_fails_closed_http(self):
        """A missing ledger must never look like a fresh quota."""
        proxy = BudgetProxy(Path(self.tmp.name) / "elsewhere.sqlite",
                            "internal-token", "provider-key", lambda p, k: (200, b"{}"))
        status, payload = proxy.budget_status("Bearer internal-token")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(payload)["error"], "budget_proxy_ledger_missing")

    def test_missing_ledger_fails_closed_status_only(self):
        """budget_status returns 503 even when no min_requests is requested."""
        other = Path(self.tmp.name) / "another-missing.sqlite"
        proxy = BudgetProxy(other, "internal-token", "provider-key", lambda p, k: (200, b"{}"))
        status, payload = proxy.budget_status("Bearer internal-token", {})
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(payload)["error"], "budget_proxy_ledger_missing")

    def test_missing_ledger_blocks_reserve(self):
        """process() refuses a missing ledger instead of creating a fresh one."""
        proxy = BudgetProxy(Path(self.tmp.name) / "missing-reserve.sqlite",
                            "internal-secret", "provider-secret",
                            lambda p, k: (200, b"{}"))
        status, payload = proxy.process("/v1/chat/completions", "Bearer internal-secret", body())
        self.assertEqual(status, 503)
        self.assertIn(b"budget_proxy_ledger_missing", payload)
        self.assertFalse(proxy.ledger.exists())  # never auto-created

    # ── Preexisting ledger preservation ──────────────────────────────────

    def test_preexisting_ledger_preserved(self):
        """Pre-seeded 16 calls / 16 CNY ledger is read back unchanged."""
        _seed_ledger(self.ledger, 16, 16, "SUCCEEDED")
        status, data = self._status()
        self.assertEqual(status, 200)
        self.assertEqual(data["calls"], 16)
        self.assertEqual(data["reserved_cny"], 16)
        self.assertIsNone(data["remaining_requests"])
        self.assertIsNone(data["remaining_cny"])
        self.assertEqual(data["pending_count"], 0)

    def test_pending_count_includes_reserved_and_unknown(self):
        """Reservations with RESERVED or UNKNOWN status count toward pending_count."""
        _seed_ledger(self.ledger, 5, 5, "RESERVED")
        # Add one UNKNOWN and one SUCCEEDED
        with closing(sqlite3.connect(self.ledger, timeout=10, isolation_level=None)) as db:
            now = "2026-09-23T00:00:00+00:00"
            db.execute("INSERT INTO reservations (name, created_at, updated_at, status, reserved_cny) VALUES (?, ?, ?, ?, ?)",
                       (RUN_NAME, now, now, "UNKNOWN", RESERVE_CNY))
            db.execute("INSERT INTO reservations (name, created_at, updated_at, status, reserved_cny) VALUES (?, ?, ?, ?, ?)",
                       (RUN_NAME, now, now, "SUCCEEDED", RESERVE_CNY))
            db.execute("UPDATE budget SET calls=7, reserved_cny=7 WHERE name=?", (RUN_NAME,))
        status, data = self._status()
        self.assertEqual(status, 200)
        self.assertEqual(data["calls"], 7)
        # 5 RESERVED + 1 UNKNOWN = 6 pending
        self.assertEqual(data["pending_count"], 6)

    # ── Legacy min_requests no longer imposes a quota ────────────────────

    def test_large_plan_is_not_rejected_by_historical_usage(self):
        _seed_ledger(self.ledger, 65, 65, "SUCCEEDED")
        status, data = self._status({"min_requests": "46"})
        self.assertEqual(status, 200)
        self.assertTrue(data["sufficient"])
        self.assertEqual(data["reason_code"], "BUDGET_OK")
        self.assertEqual(data["shortfall"]["requests"], 0)
        self.assertEqual(data["shortfall"]["cny"], 0)

    # ── Readiness remains true after the former cap ─────────────────────

    def test_old_cap_does_not_block_new_calls(self):
        _seed_ledger(self.ledger, 80, 80, "SUCCEEDED")
        status, data = self._status()
        self.assertEqual(status, 200)
        self.assertTrue(data["sufficient"])
        self.assertEqual(data["reason_code"], "BUDGET_OK")
        self.assertEqual(self.proxy.process("/v1/chat/completions", "Bearer internal-token", body())[0], 200)
        with closing(sqlite3.connect(self.ledger)) as db:
            self.assertEqual(db.execute("SELECT calls FROM budget WHERE name=?", (RUN_NAME,)).fetchone()[0], 81)

    # ── GET is idempotent — does not reserve ─────────────────────────────

    def test_get_idempotent_no_reservation(self):
        """Calling budget_status does not create any reservation row."""
        _seed_ledger(self.ledger, 5, 5, "SUCCEEDED")
        before = self.proxy._count_pending()
        for _ in range(5):
            self._status()
        with closing(sqlite3.connect(self.ledger)) as db:
            rows = db.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
            calls = db.execute("SELECT calls FROM budget WHERE name=?", (RUN_NAME,)).fetchone()[0]
            rsv = db.execute("SELECT reserved_cny FROM budget WHERE name=?", (RUN_NAME,)).fetchone()[0]
        self.assertEqual(rows, 5)  # unchanged from seed
        self.assertEqual(calls, 5)
        self.assertEqual(rsv, 5)

    # ── Response does not contain secrets or sensitive content ────────────

    def test_response_no_secrets(self):
        """Response JSON must not contain keys, prompts, or exam content."""
        _seed_ledger(self.ledger, 3, 3, "SUCCEEDED")
        _, payload = self.proxy.budget_status("Bearer internal-token")
        raw = payload.decode()
        self.assertNotIn("secret", raw)
        self.assertNotIn("internal-token", raw)
        self.assertNotIn("provider-key", raw)
        self.assertNotIn("sk-", raw)
        self.assertNotIn("content", raw)
        self.assertNotIn("hello", raw)
        # Must not echo any reservation detail fields that hold secrets
        body = json.loads(raw)
        self.assertNotIn("messages", body)
        self.assertNotIn("prompt", body)

    # ── Invalid inputs ───────────────────────────────────────────────────

    def test_invalid_min_requests_string_rejected(self):
        """Non-numeric min_requests returns 400."""
        status, data = self._status({"min_requests": "abc"})
        self.assertEqual(status, 400)

    def test_invalid_min_requests_zero_rejected(self):
        """min_requests=0 returns 400 (must be positive)."""
        status, data = self._status({"min_requests": "0"})
        self.assertEqual(status, 400)

    def test_invalid_min_requests_negative_rejected(self):
        """min_requests=-1 returns 400."""
        status, data = self._status({"min_requests": "-1"})
        self.assertEqual(status, 400)

    def test_invalid_min_requests_float_rejected(self):
        """min_requests=2.5 returns 400 (not an integer)."""
        status, data = self._status({"min_requests": "2.5"})
        self.assertEqual(status, 400)

