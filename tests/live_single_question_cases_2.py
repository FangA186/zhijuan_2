"""Live single-question offline safety checks, part 2."""
from tests.live_single_question_shared import *

class BudgetFenceTests(unittest.TestCase):
    def _budget_env(self):
        env = {
            "ZHIJUAN_BUDGET_PROXY_TOKEN": "test-token",
            "ZHIJUAN_BUDGET_INTERNAL_URL": "http://127.0.0.1:8650",
            "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0",
        }
        return mock.patch.dict(os.environ, env, clear=True)

    def test_budget_ok_passes(self):
        with self._budget_env():
            with _mock_urlopen(200, {"sufficient": True, "reason_code": "BUDGET_OK",
                                     "calls": 16, "reserved_cny": 16}):
                payload = lsq.budget_query(min_requests=2)
        self.assertEqual(payload["reason_code"], "BUDGET_OK")

    def test_budget_insufficient_false_rejected(self):
        with self._budget_env():
            with _mock_urlopen(200, {"sufficient": False, "reason_code": "BUDGET_INSUFFICIENT"}):
                with self.assertRaises(RuntimeError) as ctx:
                    lsq.budget_query(min_requests=2)
        self.assertIn("预算不足", str(ctx.exception))

    def test_budget_ok_but_wrong_reason_code_rejected(self):
        # fail-closed：sufficient=true 但 reason_code 非 BUDGET_OK 必须拒绝。
        with self._budget_env():
            with _mock_urlopen(200, {"sufficient": True, "reason_code": "BUDGET_INSUFFICIENT"}):
                with self.assertRaises(RuntimeError) as ctx:
                    lsq.budget_query(min_requests=2)
        self.assertIn("reason_code", str(ctx.exception))

    def test_budget_unreachable_rejected(self):
        with self._budget_env():
            with mock.patch.object(lsq, "urlopen", side_effect=OSError("refused")):
                with self.assertRaises(RuntimeError) as ctx:
                    lsq.budget_query(min_requests=2)
        self.assertIn("不可达", str(ctx.exception))

    def test_budget_sends_bearer_and_min_requests(self):
        captured = {}

        def capturing_urlopen(req, **kwargs):
            captured["auth"] = req.get_header("Authorization")
            captured["url"] = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            resp = mock.MagicMock()
            resp.status = 200
            resp.__enter__.return_value = resp
            resp.read.return_value = json.dumps({"sufficient": True, "reason_code": "BUDGET_OK"}).encode()
            return resp

        with self._budget_env():
            with mock.patch.object(lsq, "urlopen", side_effect=capturing_urlopen):
                lsq.budget_query(min_requests=2)
        self.assertEqual(captured["auth"], "Bearer test-token")
        self.assertIn("min_requests=2", captured["url"])
        self.assertIn("/internal/budget", captured["url"])

    def test_no_token_configured_rejected(self):
        env = {
            "ZHIJUAN_BUDGET_INTERNAL_URL": "http://127.0.0.1:8650",
            "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                lsq.budget_query(min_requests=2)
        self.assertIn("未配置", str(ctx.exception))

    # -- 评审发现1：未配置 ZHIJUAN_BUDGET_INTERNAL_URL 必须 fail-closed，
    #    绝不回退硬编码地址（`http://127.0.0.1:8650` 可能命中非知卷服务）。

    def test_budget_endpoint_appends_path_when_base(self):
        with mock.patch.dict(os.environ,
                             {"ZHIJUAN_BUDGET_INTERNAL_URL": "http://127.0.0.1:8650"},
                             clear=True):
            self.assertEqual(lsq._budget_endpoint(),
                             "http://127.0.0.1:8650/internal/budget")

    def test_budget_endpoint_keeps_existing_path_once(self):
        with mock.patch.dict(os.environ,
                             {"ZHIJUAN_BUDGET_INTERNAL_URL":
                              "http://127.0.0.1:8650/internal/budget"},
                             clear=True):
            self.assertEqual(lsq._budget_endpoint(),
                             "http://127.0.0.1:8650/internal/budget")

    def test_budget_endpoint_unset_raises_no_url(self):
        # 绝不打印/带出任何候选 URL —— 断言异常消息不包含任何 "http"。
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                lsq._budget_endpoint()
        self.assertIn("ZHIJUAN_BUDGET_INTERNAL_URL", str(ctx.exception))
        self.assertNotIn("http", str(ctx.exception))

    def test_budget_query_unset_url_fails_closed(self):
        # token 已配但 URL 未配：预算查询必须抛错（fail-closed），
        # 且 _http_get（urlopen）绝对不能被调用。
        with mock.patch.dict(os.environ,
                             {"ZHIJUAN_BUDGET_PROXY_TOKEN": "t",
                              "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0"},
                             clear=True), \
                mock.patch.object(lsq, "urlopen") as urlopen:
            with self.assertRaises(RuntimeError) as ctx:
                lsq.budget_query(min_requests=2)
        self.assertIn("ZHIJUAN_BUDGET_INTERNAL_URL", str(ctx.exception))
        urlopen.assert_not_called()

    def test_child_env_does_not_hardcode_budget_url(self):
        # child_env 注入给子进程的 ZHIJUAN_BUDGET_INTERNAL_URL 不得带
        # 硬编码默认值：未配置时原样注入空串，由子进程 fail-closed。
        env = {"ZHIJUAN_BUDGET_PROXY_TOKEN": "t"}
        with mock.patch.dict(os.environ, env, clear=True):
            child = lsq.child_env(broker="amqp://u@h/zhijuan-accept-w6")
        self.assertEqual(child["ZHIJUAN_BUDGET_INTERNAL_URL"], "")

    def test_preflight_reports_budget_unavailable_when_url_unset(self):
        # 全部其余组件就绪时，仅 URL 未配置也须 ready=false 且 code=
        # BUDGET_UNAVAILABLE（preflight 的 except RuntimeError 分支）。
        env = {
            "HERMES_API_BASE_URL": "http://127.0.0.1:8644",
            "HERMES_API_KEY": "k",
            "HERMES_SOLVER_API_BASE_URL": "http://127.0.0.1:8643",
            "HERMES_SOLVER_API_KEY": "k2",
            "ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/zhijuan_accept_w6",
            # token 已配，但 ZHIJUAN_BUDGET_INTERNAL_URL 未配 —— 必须 fail-closed
            "ZHIJUAN_BUDGET_PROXY_TOKEN": "t",
            "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0",
        }
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(lsq, "probe_author",
                                  return_value=(True, "author ok", None)), \
                mock.patch.object(lsq, "probe_solver",
                                  return_value=(True, "solver ok", None)), \
                mock.patch.object(lsq, "verify_test_database",
                                  return_value={"ok": True, "detail": "PG 就绪",
                                                "code": None}), \
                mock.patch.object(lsq, "broker_url_ok",
                                  return_value=(True, "broker ok", None)), \
                mock.patch.object(lsq, "port_in_use", return_value=False), \
                mock.patch("builtins.print"):
            pre = lsq.preflight()
        self.assertFalse(pre["ready"])
        self.assertFalse(pre["components"]["budget"]["ok"])
        self.assertEqual(pre["components"]["budget"]["code"], "BUDGET_UNAVAILABLE")
        self.assertIn("ZHIJUAN_BUDGET_INTERNAL_URL", pre["components"]["budget"]["detail"])

