"""Live single-question offline safety checks, part 1."""
from tests.live_single_question_shared import *

class DotenvSafetyTests(unittest.TestCase):
    def test_load_dotenv_skips_when_flag_set(self):
        with mock.patch.dict(os.environ, {"ZHIJUAN_SKIP_DOTENV": "1"}, clear=True):
            loaded = lsq.load_dotenv(Path("/nonexistent/.env"))
            self.assertEqual(loaded, {})

    def test_parse_env_key_value_preserves_spaced_conninfo(self):
        text = (
            "# comment\n"
            "DATABASE_URL=user=u password=secret value dbname=zhijuan_accept_w6 host=127.0.0.1 port=55432\n"
            "CELERY_BROKER_URL=amqp://u:p@127.0.0.1:55672/zhijuan-accept-w6\n"
        )
        values = lsq.parse_env_key_value(text)
        self.assertEqual(values["DATABASE_URL"],
                         "user=u password=secret value dbname=zhijuan_accept_w6 host=127.0.0.1 port=55432")
        self.assertEqual(values["CELERY_BROKER_URL"], "amqp://u:p@127.0.0.1:55672/zhijuan-accept-w6")
        self.assertNotIn("# comment", values)

class TestDatabaseFenceTests(unittest.TestCase):
    """数据库防呆：只允许 zhijuan_accept_w6，zhijuan_local/其他库一律拒绝。"""

    def test_accepts_dedicated_accept_database(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["ZHIJUAN_TEST_DATABASE_URL"] = "postgresql://u@h/zhijuan_accept_w6"
            psycopg = mock.MagicMock()
            psycopg.connect.return_value.__enter__.return_value = _fake_pg_conn(
                "zhijuan_accept_w6", list(lsq.REQUIRED_TABLES))
            with mock.patch.dict("sys.modules", {"psycopg": psycopg}):
                result = lsq.verify_test_database(timeout=5.0)
        self.assertTrue(result["ok"], result)
        self.assertTrue(psycopg.connect.called)

    def test_rejects_zhijuan_local(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["ZHIJUAN_TEST_DATABASE_URL"] = "postgresql://u@h/zhijuan_local"
            psycopg = mock.MagicMock()
            psycopg.connect.return_value.__enter__.return_value = _fake_pg_conn(
                "zhijuan_local", list(lsq.REQUIRED_TABLES))
            with mock.patch.dict("sys.modules", {"psycopg": psycopg}):
                result = lsq.verify_test_database(timeout=5.0)
        self.assertFalse(result["ok"])
        self.assertIn("zhijuan_local", result["detail"])

    def test_rejects_other_database(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["ZHIJUAN_TEST_DATABASE_URL"] = "postgresql://u@h/some_other_db"
            psycopg = mock.MagicMock()
            psycopg.connect.return_value.__enter__.return_value = _fake_pg_conn(
                "some_other_db", list(lsq.REQUIRED_TABLES))
            with mock.patch.dict("sys.modules", {"psycopg": psycopg}):
                result = lsq.verify_test_database(timeout=5.0)
        self.assertFalse(result["ok"])
        self.assertIn("不是 zhijuan_accept_w6", result["detail"])

    def test_rejects_missing_tables(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ["ZHIJUAN_TEST_DATABASE_URL"] = "postgresql://u@h/zhijuan_accept_w6"
            psycopg = mock.MagicMock()
            psycopg.connect.return_value.__enter__.return_value = _fake_pg_conn(
                "zhijuan_accept_w6", ["generation_jobs", "runtime_heartbeats"])
            with mock.patch.dict("sys.modules", {"psycopg": psycopg}):
                result = lsq.verify_test_database(timeout=5.0)
        self.assertFalse(result["ok"])
        self.assertIn("缺少表", result["detail"])

    def test_not_configured(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ZHIJUAN_TEST_DATABASE_URL", None)
            result = lsq.verify_test_database(timeout=5.0)
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "NOT_CONFIGURED")

