"""Local runtime checks, part 2."""
from tests.local_runtime_shared import *

class BudgetCheckDirectTests(unittest.TestCase):
    """Direct tests of budget_check() with mocked HTTP."""

    def _mock_env(self, token="test-token", url="http://127.0.0.1:8650/internal/budget"):
        """Set up environment variables needed by budget_check."""
        env = {
            "ZHIJUAN_BUDGET_PROXY_TOKEN": token,
            "ZHIJUAN_BUDGET_INTERNAL_URL": url,
        }
        return mock.patch.dict(os.environ, env, clear=False)

    def _mock_urlopen(self, status=200, body=None):
        """Create a mock urlopen returning the given status and JSON body."""
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b"{}"
        mock_resp = mock.MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.status = status
        mock_resp.read.return_value = body_bytes
        return mock.patch.object(lr, "urlopen", return_value=mock_resp)

    def test_budget_ok(self):
        """sufficient=true, reason_code=BUDGET_OK → (True, ..., None)."""
        with self._mock_env():
            with self._mock_urlopen(body={
                "sufficient": True,
                "reason_code": "BUDGET_OK",
                "remaining_requests": 5,
                "remaining_cny": 10,
            }):
                ok, detail, code = lr.budget_check(timeout=2.0)
        self.assertTrue(ok)
        self.assertIsNone(code)
        self.assertIn("预算接口可达", detail)

    def test_budget_insufficient_sufficient_false(self):
        """sufficient=false → (False, ..., BUDGET_INSUFFICIENT)."""
        with self._mock_env():
            with self._mock_urlopen(body={
                "sufficient": False,
                "reason_code": "BUDGET_INSUFFICIENT",
                "remaining_requests": 0,
                "remaining_cny": 0,
            }):
                ok, detail, code = lr.budget_check(timeout=2.0)
        self.assertFalse(ok)
        self.assertEqual(code, "BUDGET_INSUFFICIENT")
        self.assertIn("reason_code=BUDGET_INSUFFICIENT", detail)

    def test_budget_insufficient_reason_code(self):
        """sufficient=true but reason_code=BUDGET_INSUFFICIENT → (False, ..., BUDGET_INSUFFICIENT).
        This covers edge cases where the proxy sets both fields inconsistently."""
        with self._mock_env():
            with self._mock_urlopen(body={
                "sufficient": True,
                "reason_code": "BUDGET_INSUFFICIENT",
            }):
                ok, detail, code = lr.budget_check(timeout=2.0)
        self.assertFalse(ok)
        self.assertEqual(code, "BUDGET_INSUFFICIENT")

    def test_budget_unreachable(self):
        """urlopen raises → (False, ..., BUDGET_UNAVAILABLE)."""
        with self._mock_env():
            with mock.patch.object(lr, "urlopen", side_effect=OSError("Connection refused")):
                ok, detail, code = lr.budget_check(timeout=2.0)
        self.assertFalse(ok)
        self.assertEqual(code, "BUDGET_UNAVAILABLE")
        self.assertIn("不可达", detail)

    def test_budget_no_token(self):
        """Empty token → (False, ..., NOT_CONFIGURED)."""
        with self._mock_env(token=""):
            ok, detail, code = lr.budget_check(timeout=2.0)
        self.assertFalse(ok)
        self.assertEqual(code, "NOT_CONFIGURED")
        self.assertIn("未配置", detail)

    def test_budget_sends_min_requests_param(self):
        """budget_check must send ?min_requests=1 to get real sufficiency evaluation."""
        with self._mock_env():
            # Capture the actual request URL
            real_urlopen = lr.urlopen
            captured_url = None

            def capturing_urlopen(req, **kw):
                nonlocal captured_url
                captured_url = req.full_url if hasattr(req, 'full_url') else getattr(req, 'data', None)
                # Return a sufficient response so the test passes
                mock_resp = mock.MagicMock()
                mock_resp.__enter__.return_value = mock_resp
                mock_resp.status = 200
                mock_resp.read.return_value = json.dumps({
                    "sufficient": True, "reason_code": "BUDGET_OK",
                }).encode("utf-8")
                return mock_resp

            with mock.patch.object(lr, "urlopen", side_effect=capturing_urlopen):
                lr.budget_check(timeout=2.0)

        self.assertIsNotNone(captured_url)
        self.assertIn("min_requests=1", captured_url)

class StartGenerationSafetyTests(unittest.TestCase):
    def test_start_requires_running_api(self):
        with mock.patch.object(lr, "api_health", return_value=(False, "8000 /health 不可达")):
            result = lr.start_generation()
        self.assertFalse(result["ok"])
        self.assertEqual(result["step"], "api")
        self.assertIn("不代启", result.get("next_action", ""))

    def test_start_refuses_when_pg_not_running(self):
        with mock.patch.object(lr, "api_health", return_value=(True, "8000 可达")):
            with mock.patch.object(lr, "container_state", return_value=("exited", "pg: Exited")):
                result = lr.start_generation()
        self.assertFalse(result["ok"])
        self.assertEqual(result["step"], "pg")

    def test_start_never_touches_unknown_containers(self):
        with self.assertRaises(RuntimeError):
            lr.container_state("zygf-gitea", 2.0)

    def test_docker_exec_only_allows_rabbitmqctl_vhost_ops(self):
        with self.assertRaises(RuntimeError):
            lr.docker_exec_mq(["rabbitmqctl", "delete_vhost", "zhijuan-local"])

class StopGenerationSafetyTests(unittest.TestCase):
    def test_stop_refuses_with_active_jobs(self):
        with mock.patch.object(
            lr, "_active_jobs",
            return_value=([("job-1", "RUNNING"), ("job-2", "QUEUED")], None),
        ):
            result = lr.stop_generation()
        self.assertFalse(result["ok"])
        self.assertEqual(result["step"], "active_jobs")
        self.assertIn("拒绝", result["detail"])

    def test_stop_refuses_on_active_job_db_error(self):
        with mock.patch.object(lr, "_active_jobs", return_value=([], "无法读取 generation_jobs: ConnectionRefused")):
            result = lr.stop_generation()
        self.assertFalse(result["ok"])
        self.assertEqual(result["step"], "database")

    def test_stop_refuses_foreign_first_pid(self):
        def fake_active():
            return [], None
        with mock.patch.object(lr, "_active_jobs", fake_active):
            with mock.patch.object(lr, "_read_pid_file", side_effect=lambda kind: 4242 if kind == "worker" else 0):
                with mock.patch.object(lr, "_cmdline_for_pid", return_value="/usr/bin/python unrelated.py"):
                    result = lr.stop_generation()
        self.assertFalse(result["ok"])
        self.assertEqual(result["step"], "ownership")

    def test_stop_kills_only_owned_and_stops_mq(self):
        calls = []
        with mock.patch.object(lr, "_active_jobs", return_value=([], None)):
            with mock.patch.object(lr, "_read_pid_file", side_effect=lambda kind: 1111 if kind == "worker" else 2222):
                with mock.patch.object(lr, "_cmdline_for_pid", return_value=".venv/bin/celery -A services.worker.jobs:app worker --pool=solo"):
                    with mock.patch.object(lr, "_terminate_owned", side_effect=lambda pid, grace=10.0: (calls.append(("term", pid)) or f"PID {pid} 已终止")):
                        with mock.patch.object(lr, "_remove_pid_file", side_effect=lambda kind: calls.append(("rm", kind))):
                            with mock.patch.object(lr, "container_state", return_value=("running", "mq: running")):
                                with mock.patch.object(lr.subprocess, "run", return_value=subprocess.CompletedProcess(args=["docker","stop","x"], returncode=0, stdout="zhijuan-workflow-20260922-mq\n", stderr="")) as run:
                                    result = lr.stop_generation()
        self.assertTrue(result["ok"])
        # 收尾顺序固定为 调度器→Worker（services.worker.scheduler PID 2222 先停）。
        self.assertEqual(calls, [("term", 2222), ("rm", "scheduler"), ("term", 1111), ("rm", "worker")])
        self.assertEqual(run.call_args.args[0], ["docker", "stop", "zhijuan-workflow-20260922-mq"])

    def test_no_active_and_no_pid_files_reports_empty(self):
        with mock.patch.object(lr, "_active_jobs", return_value=([], None)):
            with mock.patch.object(lr, "_read_pid_file", return_value=None):
                result = lr.stop_generation()
        self.assertTrue(result["ok"])
        self.assertIn("无需收尾", result["next_action"])

