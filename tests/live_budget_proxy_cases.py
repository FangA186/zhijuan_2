"""Proxy request and legacy accounting checks."""
from tests.live_budget_proxy_shared import *

class BudgetProxyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / "budget.sqlite"
        provision_ledger(self.ledger)
        self.calls = []

        def forward(payload, key):
            self.calls.append((json.loads(payload), key))
            return 200, b'{"choices":[]}'

        self.proxy = BudgetProxy(self.ledger, "internal-secret", "provider-secret", forward)

    def process(self, payload):
        return self.proxy.process("/v1/chat/completions", "Bearer internal-secret", payload)

    def count(self):
        if not self.ledger.exists():
            return 0
        with closing(sqlite3.connect(self.ledger)) as db:
            return db.execute("SELECT calls FROM budget WHERE name=?", (RUN_NAME,)).fetchone()[0]

    def reservations(self):
        with closing(sqlite3.connect(self.ledger)) as db:
            return db.execute(
                "SELECT id, status, reserved_cny, prompt_tokens, completion_tokens, total_tokens, provider_model, provider_request_id "
                "FROM reservations ORDER BY id").fetchall()

    def test_reserves_before_forward_and_clamps_output(self):
        def forward(payload, key):
            self.assertEqual(self.count(), 1)
            self.assertEqual(key, "provider-secret")
            sent = json.loads(payload)
            self.assertEqual(sent["max_tokens"], 4096)
            self.assertEqual(sent["thinking"], {"type": "disabled"})
            self.assertEqual(sent["reasoning_effort"], "none")
            self.assertFalse(sent["stream"])
            return 200, b'{}'
        self.proxy.forward = forward
        self.assertEqual(self.process(body(max_tokens=100000, thinking={"type": "enabled"}))[0], 200)

    def test_hermes_nonstream_chat_shape(self):
        # Shape produced by Hermes OpenAI chat transport with model.streaming: false
        # and no enabled tool schemas; still a Hermes AIAgent call.
        request = body(messages=[
            {"role": "system", "content": "You are a question author."},
            {"role": "user", "content": "Return one JSON question."},
        ], stream=False, temperature=0.2, response_format={"type": "json_object"})
        self.assertEqual(self.process(request)[0], 200)
        self.assertEqual(self.calls[0][0]["response_format"], {"type": "json_object"})

    def test_json_mode_cannot_be_disabled_by_a_caller(self):
        self.assertEqual(self.process(body(response_format={"type": "text"}))[0], 200)
        self.assertEqual(self.calls[-1][0]["response_format"], {"type": "json_object"})
        status, raw = self.proxy.budget_status("Bearer internal-secret")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["output_contract"]["version"], "strict-json-v3")

    def test_records_usage_summary_without_response_body(self):
        self.proxy.forward = lambda payload, key: (200, json.dumps({
            "id": "chat-1", "model": "deepseek-flash",
            "usage": {"prompt_tokens": 12, "completion_tokens": 34, "total_tokens": 46},
            "choices": [{"message": {"content": "private exam response"}}],
        }).encode())
        self.assertEqual(self.process(body())[0], 200)
        self.assertEqual(self.reservations()[0], (1, "SUCCEEDED", 1, 12, 34, 46, "deepseek-flash", "chat-1"))
        self.assertNotIn(b"private exam response", self.ledger.read_bytes())

    def test_models_metadata_is_local_and_free(self):
        status, payload = self.proxy.models("/v1/models", "Bearer internal-secret")
        self.assertEqual(status, 200)
        self.assertEqual([m["id"] for m in json.loads(payload)["data"]], ["deepseek-flash"])
        self.assertEqual(self.count(), 0)
        self.assertFalse(self.calls)

    def test_rejects_routing_tools_stream_and_oversize_without_reserving(self):
        bad = [
            body(model="deepseek-v4-pro"),
            body(stream=True),
            body(tools=[]),
            body(messages=[{"role": "user", "content": [{"type": "image_url"}]}]),
            b" " * (MAX_BODY_BYTES + 1),
        ]
        for payload in bad:
            self.assertNotEqual(self.process(payload)[0], 200)
        self.assertEqual(self.proxy.process("/other", "Bearer internal-secret", body())[0], 404)
        self.assertEqual(self.proxy.process("/v1/chat/completions", "Bearer wrong", body())[0], 401)
        self.assertEqual(self.count(), 0)
        self.assertFalse(self.calls)

    def test_unknown_result_keeps_reservation_and_does_not_echo_secrets(self):
        self.proxy.forward = lambda payload, key: (_ for _ in ()).throw(RuntimeError("provider-secret"))
        status, response = self.process(body())
        self.assertEqual(status, 502)
        self.assertEqual(self.count(), 1)
        self.assertNotIn(b"provider-secret", response)
        self.assertNotIn(b"internal-secret", response)
        self.assertEqual(self.reservations()[0][1], "UNKNOWN")

    def test_restart_and_upstream_failure_keep_reservation(self):
        self.proxy.forward = lambda payload, key: (429, b'{"secret":"provider-secret"}')
        status, response = self.process(body())
        self.assertEqual(status, 429)
        self.assertNotIn(b"provider-secret", response)
        restarted = BudgetProxy(self.ledger, "internal-secret", "provider-secret",
                                lambda payload, key: (200, b"{}"))
        self.assertEqual(restarted.process("/chat/completions", "Bearer internal-secret", body())[0], 200)
        self.assertEqual(self.count(), 2)
        self.assertEqual([row[1] for row in self.reservations()], ["UPSTREAM_ERROR", "SUCCEEDED_USAGE_UNKNOWN"])

    def test_parallel_requests_are_all_accounted_without_a_cap(self):
        with ThreadPoolExecutor(max_workers=24) as pool:
            statuses = list(pool.map(lambda _: self.process(body())[0], range(30)))
        self.assertEqual(statuses.count(200), 30)
        self.assertEqual(self.count(), 30)
        self.assertEqual(len(self.reservations()), 30)


class LegacyLimitEnvironmentTests(unittest.TestCase):
    def test_old_limit_env_variables_no_longer_change_accounting(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "ZHIJUAN_BUDGET_MAX_REQUESTS": "1",
            "ZHIJUAN_BUDGET_MAX_RESERVED_CNY": "1",
        }):
            ledger = Path(tmp) / "acceptance.sqlite"
            provision_ledger(ledger)
            proxy = BudgetProxy(ledger, "token", "provider-key", lambda payload, key: (200, b"{}"))
            for _ in range(3):
                self.assertEqual(proxy.process("/v1/chat/completions", "Bearer token", body())[0], 200)
            with closing(sqlite3.connect(ledger)) as db:
                self.assertEqual(db.execute("SELECT calls FROM budget WHERE name=?", (RUN_NAME,)).fetchone()[0], 3)


