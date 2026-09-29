"""Live single-question offline safety checks, part 3."""
from tests.live_single_question_shared import *

class RunFailureRedactionTests(unittest.TestCase):
    """评审发现2：run() 异常处理绝不得把 str(exc) 带进 reason / 输出。

    psycopg 认证失败消息可能含数据库用户名（已实验验证），因此只保
    留异常类型名，与 verify_test_database 的 fail-closed 写法一致。
    """

    def test_run_exception_reason_never_embeds_str_exc(self):
        # 触发 run() 在步骤6之前失败：poll_job 抛带用户名/口令的 psycopg 错误。
        env = {"ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/zhijuan_accept_w6"}
        secret_like = "postgresql://accept_user:SUPERSECRET@127.0.0.1:55432/auth"
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(lsq, "preflight",
                                  return_value={"ready": True, "components": {}}), \
                mock.patch.object(lsq, "budget_query",
                                  return_value={"calls": 16, "reserved_cny": 16,
                                                "sufficient": True,
                                                "reason_code": "BUDGET_OK"}), \
                mock.patch.object(lsq, "spawn_process") as spawn, \
                mock.patch.object(lsq, "wait_heartbeats",
                                  return_value={"ok": True, "detail": "beats",
                                                "heartbeats": {}}), \
                mock.patch.object(lsq, "run_acceptance_chain",
                                  return_value={"job_id": "j-x", "status": "QUEUED",
                                                "job": {"job_id": "j-x"}}) as accept_chain, \
                mock.patch.object(lsq, "poll_job",
                                  side_effect=psycopg_authentication_error(
                                      secret_like)) as poll, \
                mock.patch("builtins.print") as printed, \
                mock.patch.object(lsq, "write_report") as write_report:
            result = lsq.run(out_path=Path("/tmp/lsq-redact.json"))
        # 证据 JSON 里也绝不含 str(exc)：patch 掉 write_report 检查传入结果。
        self.assertFalse(result["ok"])
        self.assertIn("运行中止", result["reason"])
        self.assertEqual(result["reason"], "运行中止: OperationalError")
        self.assertNotIn("OperationalError: ", result["reason"])
        for text in (secret_like, "accept_user", "SUPERSECRET", "55432"):
            self.assertNotIn(text, result["reason"])
            self.assertNotIn(text, str(printed))
        # 原始异常文本也绝不进入 write_report 的 reason 字段。
        call_args = write_report.call_args
        self.assertIsNotNone(call_args)
        written = call_args[0][1]
        for text in (secret_like, "accept_user", "SUPERSECRET", "55432"):
            self.assertNotIn(text, json.dumps(written, ensure_ascii=False))
        # 仍只受理一次、只轮询（fail-closed 不重发）。
        accept_chain.assert_called_once()
        poll.assert_called_once()

class AuthorSolverProbeTests(unittest.TestCase):
    def test_author_unreachable_fails_preflight(self):
        env = {
            "HERMES_API_BASE_URL": "http://127.0.0.1:8644",
            "HERMES_API_KEY": "k",
            "HERMES_SOLVER_API_BASE_URL": "http://127.0.0.1:8643",
            "HERMES_SOLVER_API_KEY": "k2",
            "ZHIJUAN_BUDGET_PROXY_TOKEN": "t",
            "ZHIJUAN_BUDGET_INTERNAL_URL": "http://127.0.0.1:8650",
            "ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/zhijuan_accept_w6",
            "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0",
        }
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(lsq, "budget_query",
                                  return_value={"sufficient": True, "reason_code": "BUDGET_OK"}), \
                mock.patch.object(lsq, "verify_test_database",
                                  return_value={"ok": True, "detail": "PG 就绪", "code": None}), \
                mock.patch.object(lsq, "broker_url_ok",
                                  return_value=(True, "broker ok", None)), \
                mock.patch.object(lsq, "port_in_use", return_value=False), \
                mock.patch.object(lsq, "_http_get") as http_get, \
                mock.patch("builtins.print"):
            http_get.side_effect = OSError("author refused")
            pre = lsq.preflight()
        self.assertFalse(pre["ready"])
        self.assertIn("AUTHOR_UNAVAILABLE", pre["reason_codes"])
        self.assertFalse(pre["components"]["author"]["ok"])
        self.assertIn("author", pre["components"]["author"]["detail"])

    def test_solver_401_fails_preflight(self):
        env = {
            "HERMES_API_BASE_URL": "http://127.0.0.1:8644",
            "HERMES_API_KEY": "k",
            "HERMES_SOLVER_API_BASE_URL": "http://127.0.0.1:8643",
            "HERMES_SOLVER_API_KEY": "k2",
            "ZHIJUAN_BUDGET_PROXY_TOKEN": "t",
            "ZHIJUAN_BUDGET_INTERNAL_URL": "http://127.0.0.1:8650",
            "ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/zhijuan_accept_w6",
            "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0",
        }

        def side_effect(url, **kwargs):
            if url.startswith("http://127.0.0.1:8644"):
                return 200, {"status": "ok"}
            return 401, {"error": "unauthorized"}

        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(lsq, "budget_query",
                                  return_value={"sufficient": True, "reason_code": "BUDGET_OK"}), \
                mock.patch.object(lsq, "verify_test_database",
                                  return_value={"ok": True, "detail": "PG 就绪", "code": None}), \
                mock.patch.object(lsq, "broker_url_ok",
                                  return_value=(True, "broker ok", None)), \
                mock.patch.object(lsq, "port_in_use", return_value=False), \
                mock.patch.object(lsq, "_http_get", side_effect=side_effect), \
                mock.patch("builtins.print"):
            pre = lsq.preflight()
        self.assertFalse(pre["ready"])
        self.assertIn("SOLVER_UNAVAILABLE", pre["reason_codes"])
        self.assertFalse(pre["components"]["solver"]["ok"])
        self.assertIn("401", pre["components"]["solver"]["detail"])

    def test_budget_error_fails_preflight_even_if_gateways_ok(self):
        env = {
            "HERMES_API_BASE_URL": "http://127.0.0.1:8644",
            "HERMES_API_KEY": "k",
            "HERMES_SOLVER_API_BASE_URL": "http://127.0.0.1:8643",
            "HERMES_SOLVER_API_KEY": "k2",
            "ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/zhijuan_accept_w6",
            "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0",
        }
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(lsq, "budget_query",
                                  side_effect=RuntimeError("预算不足（sufficient=False reason_code=BUDGET_INSUFFICIENT）")), \
                mock.patch.object(lsq, "probe_author", return_value=(True, "author ok", None)), \
                mock.patch.object(lsq, "probe_solver", return_value=(True, "solver ok", None)), \
                mock.patch.object(lsq, "verify_test_database",
                                  return_value={"ok": True, "detail": "PG 就绪", "code": None}), \
                mock.patch.object(lsq, "broker_url_ok", return_value=(True, "broker ok", None)), \
                mock.patch.object(lsq, "port_in_use", return_value=False), \
                mock.patch("builtins.print"):
            pre = lsq.preflight()
        self.assertFalse(pre["ready"])
        self.assertFalse(pre["components"]["budget"]["ok"])

    def test_port_busy_fails_preflight(self):
        env = {
            "HERMES_API_BASE_URL": "http://127.0.0.1:8644",
            "HERMES_API_KEY": "k",
            "HERMES_SOLVER_API_BASE_URL": "http://127.0.0.1:8643",
            "HERMES_SOLVER_API_KEY": "k2",
            "ZHIJUAN_BUDGET_PROXY_TOKEN": "t",
            "ZHIJUAN_BUDGET_INTERNAL_URL": "http://127.0.0.1:8650",
            "ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/zhijuan_accept_w6",
            "ZHIJUAN_READINESS_PROBE_TIMEOUT": "2.0",
        }
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(lsq, "budget_query",
                                  return_value={"sufficient": True, "reason_code": "BUDGET_OK"}), \
                mock.patch.object(lsq, "probe_author", return_value=(True, "author ok", None)), \
                mock.patch.object(lsq, "probe_solver", return_value=(True, "solver ok", None)), \
                mock.patch.object(lsq, "verify_test_database",
                                  return_value={"ok": True, "detail": "PG 就绪", "code": None}), \
                mock.patch.object(lsq, "broker_url_ok", return_value=(True, "broker ok", None)), \
                mock.patch.object(lsq, "port_in_use", return_value=True), \
                mock.patch("builtins.print"):
            pre = lsq.preflight()
        self.assertFalse(pre["ready"])
        self.assertFalse(pre["components"]["port_8020"]["ok"])
        self.assertIn("PORT_IN_USE", pre["reason_codes"])

