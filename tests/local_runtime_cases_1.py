"""Local runtime checks, part 1."""
from tests.local_runtime_shared import *

class DotenvParsingTests(unittest.TestCase):
    def test_key_value_parser_keeps_spaces_inside_conninfo(self):
        text = (
            "# comment line\n"
            "\n"
            "DATABASE_URL=user=zhijuan_workflow password=secret value dbname=zhijuan_local host=127.0.0.1 port=55432\n"
            "CELERY_BROKER_URL=amqp://u:p@127.0.0.1:55672/zhijuan-local\n"
            "ZHIJUAN_RUNTIME_ID=zhijuan-local\n"
        )
        values = lr.parse_env_key_value(text)
        self.assertEqual(
            values["DATABASE_URL"],
            "user=zhijuan_workflow password=secret value dbname=zhijuan_local host=127.0.0.1 port=55432",
        )
        self.assertEqual(values["CELERY_BROKER_URL"], "amqp://u:p@127.0.0.1:55672/zhijuan-local")
        self.assertEqual(values.get("ZHIJUAN_RUNTIME_ID"), "zhijuan-local")
        # comment and blank lines never become keys
        self.assertNotIn("# comment line", values)
        self.assertEqual(len(values), 3)

    def test_load_dotenv_does_not_override_existing_environ(self):
        with mock.patch.dict(os.environ, {"ZHIJUAN_RUNTIME_ID": "already-set"}, clear=True):
            loaded = lr.load_dotenv(Path("/nonexistent/.env"))
            self.assertEqual(loaded, {})
            self.assertEqual(os.environ["ZHIJUAN_RUNTIME_ID"], "already-set")

    def test_skip_dotenv_flag_prevents_loading(self):
        with mock.patch.dict(os.environ, {"ZHIJUAN_SKIP_DOTENV": "1"}, clear=True):
            loaded = lr.load_dotenv(Path("/nonexistent/.env"))
            self.assertEqual(loaded, {})

    def test_load_dotenv_reads_real_style_file_with_spaces(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "DATABASE_URL=user=u password=p dbname=zhijuan_local host=127.0.0.1 port=55432\n"
                "HERMES_API_BASE_URL=http://127.0.0.1:8644\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {}, clear=True):
                values = lr.load_dotenv(env_file)
            self.assertTrue(values["DATABASE_URL"].startswith("user=u password=p dbname=zhijuan_local"))

class PidOwnershipTests(unittest.TestCase):
    def test_verify_pid_ownership_accepts_worker_cmdline(self):
        fake_out = subprocess.CompletedProcess(
            args=["ps"], returncode=0,
            stdout=".venv/bin/celery -A services.worker.jobs:app worker --pool=solo --concurrency=1\n",
            stderr="",
        )
        with mock.patch.object(lr.subprocess, "run", return_value=fake_out) as run:
            ok, detail = lr.verify_pid_ownership(1234)
        self.assertTrue(ok)
        self.assertIn("services.worker.jobs", detail)
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][:2], ["ps", "-p"])
        self.assertIn("1234", run.call_args.args[0])

    def test_verify_pid_ownership_accepts_scheduler_cmdline(self):
        fake_out = subprocess.CompletedProcess(
            args=["ps"], returncode=0,
            stdout=".venv/bin/python -m services.worker.scheduler\n",
            stderr="",
        )
        with mock.patch.object(lr.subprocess, "run", return_value=fake_out):
            ok, detail = lr.verify_pid_ownership(5678)
        self.assertTrue(ok)
        self.assertIn("services.worker.scheduler", detail)

    def test_verify_pid_ownership_rejects_unrelated_process(self):
        fake_out = subprocess.CompletedProcess(
            args=["ps"], returncode=0,
            stdout="/usr/bin/launchctl\n",
            stderr="",
        )
        with mock.patch.object(lr.subprocess, "run", return_value=fake_out):
            ok, detail = lr.verify_pid_ownership(99999)
        self.assertFalse(ok)
        self.assertIn("拒绝", detail)

    def test_verify_pid_ownership_rejects_missing_process(self):
        fake_out = subprocess.CompletedProcess(
            args=["ps"], returncode=1, stdout="", stderr="pid not found",
        )
        with mock.patch.object(lr.subprocess, "run", return_value=fake_out):
            ok, detail = lr.verify_pid_ownership(12345)
        self.assertFalse(ok)
        self.assertIn("不存在", detail)

class DoctorOutputStructureTests(unittest.TestCase):
    def _mock_all_probes_ok(self):
        patchers = [
            mock.patch.object(lr, "database_check", return_value=(True, "PG 就绪", None)),
            mock.patch.object(lr, "broker_check", return_value=(True, "RabbitMQ 可达", None)),
            mock.patch.object(lr, "heartbeat_check", side_effect=lambda comp, t: (True, f"{comp} 新鲜", None)),
            mock.patch.object(lr, "tcp_base_check", side_effect=lambda url, t, label: (True, f"{label} 可达", None)),
            mock.patch.object(lr, "budget_check", return_value=(True, "预算可达", None)),
            mock.patch.object(lr, "api_health", return_value=(True, "8000 可达")),
            mock.patch.object(lr, "container_state", side_effect=lambda name, t=10.0: ("running", f"{name}: running")),
            mock.patch.object(lr.os, "getenv", wraps=os.getenv),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)

    def test_doctor_returns_full_component_schema_and_reason_codes_empty(self):
        self._mock_all_probes_ok()
        with mock.patch("builtins.print"):
            result = lr.doctor()
        self.assertTrue(result["ready"])
        self.assertEqual(result["reason_codes"], [])
        for name in ("database", "broker", "worker", "dispatcher", "author", "solver", "budget", "api"):
            comp = result["components"][name]
            self.assertIn("ok", comp)
            self.assertIn("detail", comp)
            self.assertIn("next_action", comp)
            self.assertTrue(comp["ok"])

    def test_doctor_failure_produces_reason_codes_and_actions(self):
        patchers = [
            mock.patch.object(lr, "database_check", return_value=(True, "PG 就绪", None)),
            mock.patch.object(
                lr, "broker_check",
                return_value=(False, "55672 不可达", "BROKER_UNAVAILABLE"),
            ),
            mock.patch.object(
                lr, "heartbeat_check",
                side_effect=lambda comp, t: (False, f"{comp} 无心跳", "WORKER_UNAVAILABLE" if comp == "worker" else "DISPATCHER_UNAVAILABLE"),
            ),
            mock.patch.object(
                lr, "tcp_base_check",
                return_value=(True, "author/solver 可达", None),
            ),
            mock.patch.object(lr, "budget_check", return_value=(True, "预算可达", None)),
            mock.patch.object(lr, "api_health", return_value=(True, "8000 可达")),
            mock.patch.object(lr, "container_state", side_effect=lambda name, t=10.0: ("running", f"{name}: running")),
            mock.patch("builtins.print"),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)
        result = lr.doctor()
        self.assertFalse(result["ready"])
        self.assertIn("BROKER_UNAVAILABLE", result["reason_codes"])
        self.assertIn("WORKER_UNAVAILABLE", result["reason_codes"])
        self.assertIn("DISPATCHER_UNAVAILABLE", result["reason_codes"])
        self.assertFalse(result["components"]["broker"]["ok"])
        self.assertIn("start-generation", result["components"]["broker"]["next_action"])

    def test_doctor_never_prints_secrets(self):
        self._mock_all_probes_ok()
        with mock.patch("builtins.print") as print_mock:
            lr.doctor()
        printed = "".join(str(call) for call in print_mock.call_args_list)
        self.assertNotIn("password", printed)
        self.assertNotIn("sk-", printed)
        self.assertNotIn("token", printed.lower())

