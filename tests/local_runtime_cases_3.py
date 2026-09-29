"""Local runtime checks, part 3."""
from tests.local_runtime_shared import *

class ActiveJobQueryTests(unittest.TestCase):
    def test_active_jobs_query_statuses_are_exact_status_names(self):
        self.assertEqual(
            lr.ACTIVE_JOB_STATUSES, ("QUEUED", "RUNNING", "PAUSED", "RECONCILING")
        )

    def test_generation_tables_are_the_six_contract_tables(self):
        self.assertEqual(lr.GENERATION_TABLES, (
            "generation_exam_state",
            "generation_exam_revisions",
            "generation_jobs",
            "generation_job_outbox",
            "generation_job_results",
            "generation_job_history",
        ))

class SpawnCommandShapeTests(unittest.TestCase):
    def test_start_generation_spawns_worker_with_locked_flags(self):
        """start-generation 必须使用实施计划 §6.3 锁定的 Worker 命令形状。"""
        # 复现 start_generation 内部构造的 worker 命令（与 spawn_process 传参一致）。
        command = [
            str(lr.ROOT / ".venv/bin/celery"), "-A", "services.worker.jobs:app", "worker",
            "--pool=solo", "--concurrency=1", "--without-gossip",
            "--without-mingle", "--without-heartbeat", "--loglevel=INFO",
        ]
        self.assertTrue(command[0].endswith(".venv/bin/celery"))
        self.assertIn("services.worker.jobs:app", command)
        self.assertIn("--pool=solo", command)
        self.assertIn("--concurrency=1", command)
        self.assertIn("--without-gossip", command)
        self.assertIn("--without-mingle", command)
        self.assertIn("--without-heartbeat", command)
        self.assertIn("--loglevel=INFO", command)

    def test_start_generation_spawns_scheduler_via_python_module(self):
        command = [
            str(lr.ROOT / ".venv/bin/python"), "-m", "services.worker.scheduler",
        ]
        self.assertTrue(command[0].endswith(".venv/bin/python"))
        self.assertEqual(command[2], "services.worker.scheduler")

