"""Exercise runtime names used across newly separated modules without I/O."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.api.job_repository_reads import JobRepositoryReadMixin
from tools.local_runtime_probes import api_health


class SplitImportTests(unittest.TestCase):
    def test_job_replace_sets_timestamp_before_sql(self):
        conn = MagicMock()
        conn.__enter__.return_value = conn
        conn.execute.return_value.fetchone.return_value = ({"ok": True},)
        repo = SimpleNamespace(psycopg=SimpleNamespace(connect=lambda _: conn), dsn="fixture")
        job = {"exam_id": "fixture", "job_id": "job-1", "version": 1}
        updated = JobRepositoryReadMixin.replace(repo, job, 1)
        self.assertEqual(updated["version"], 2)
        self.assertIn("+00:00", updated["updated_at"])

    def test_health_probe_uses_injected_transport(self):
        response = MagicMock(status=200)
        response.__enter__.return_value = response
        self.assertEqual(api_health(1.0, urlopen_fn=lambda *_a, **_kw: response),
                         (True, "8000 /health 可达"))


if __name__ == "__main__":
    unittest.main()
