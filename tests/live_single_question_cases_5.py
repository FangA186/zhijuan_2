"""Live single-question offline safety checks, part 5."""
from tests.live_single_question_shared import *

class TerminalNoRetryTests(unittest.TestCase):
    def _mock_pg(self, job: dict):
        psycopg = mock.MagicMock()
        conn = mock.MagicMock()
        cursor = mock.MagicMock()
        cursor.fetchone.return_value = (job,)
        conn.execute.return_value = cursor
        psycopg.connect.return_value.__enter__.return_value = conn
        return psycopg, conn

    def test_poll_returns_reconciling_without_retry(self):
        # poll_job 只读返回终态；RECONCILING 原样返回，不重发（无自动重试循环）。
        job = {"status": "RECONCILING", "job_id": "j-9"}
        psycopg, conn = self._mock_pg(job)
        with mock.patch.dict("sys.modules", {"psycopg": psycopg}):
            result = lsq.poll_job("dsn", "j-9", timeout=5.0, interval=0.01)
        self.assertEqual(result["status"], "RECONCILING")
        # 只读：只 SELECT，绝不写库。
        for call in conn.execute.call_args_list:
            self.assertTrue(str(call.args[0]).startswith("SELECT"), call)

    def test_poll_returns_completed_without_retry(self):
        job = {"status": "COMPLETED", "job_id": "j-10"}
        psycopg, conn = self._mock_pg(job)
        with mock.patch.dict("sys.modules", {"psycopg": psycopg}):
            result = lsq.poll_job("dsn", "j-10", timeout=5.0, interval=0.01)
        self.assertEqual(result["status"], "COMPLETED")

    def test_run_marks_not_responsible_terminal_without_reaccept(self):
        # RECONCILING/FAILED 终态：ok=False、如实记录，绝不重新受理
        # （不再次调用 run_acceptance_chain）。
        env = {"ZHIJUAN_TEST_DATABASE_URL": "postgresql://u@h/zhijuan_accept_w6"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(lsq, "preflight",
                                  return_value={"ready": True, "components": {}}), \
                mock.patch.object(lsq, "budget_query",
                                  return_value={"calls": 16, "reserved_cny": 16,
                                                "sufficient": True, "reason_code": "BUDGET_OK"}), \
                mock.patch.object(lsq, "spawn_process") as spawn, \
                mock.patch.object(lsq, "wait_heartbeats",
                                  return_value={"ok": True, "detail": "beats", "heartbeats": {}}), \
                mock.patch.object(lsq, "run_acceptance_chain",
                                  return_value={"job_id": "j-9", "status": "QUEUED",
                                                "job": {"job_id": "j-9"}}) as accept_chain, \
                mock.patch.object(lsq, "poll_job",
                                  return_value={"status": "RECONCILING", "job_id": "j-9",
                                                "run_refs": {}}) as poll, \
                mock.patch.object(lsq, "write_report") as write_report, \
                mock.patch("builtins.print"):
            result = lsq.run(out_path=Path("/tmp/lsq-r3.json"))
        self.assertFalse(result["ok"])
        self.assertIn("RECONCILING", result["reason"])
        accept_chain.assert_called_once()  # 只受理这一次
        poll.assert_called_once()  # 只轮询，不重发

