from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""Queue runtime integration checks."""
from tests.integration.queue_runtime_shared import *

@unittest.skipUnless(REQUIRED, "dedicated broker vhost and test DSN required")
class QueueRuntimeTests(unittest.TestCase):
    worker_proc: subprocess.Popen | None = None

    @classmethod
    def setUpClass(cls):
        from services.api.main import app  # test process shares the test DSN via env
        cls.client_app = app
        cls.author = FakeHermesServer(output_payload=_author_payload("q01", "solution", 100))
        cls.solver = FakeHermesServer(output_payload=SOLVER_PAYLOAD)
        _, author_port = cls.author.start()
        _, solver_port = cls.solver.start()
        env = os.environ.copy()
        env.update({
            "ZHIJUAN_SKIP_DOTENV": "1",
            "DATABASE_URL": DSN,
            "CELERY_BROKER_URL": BROKER,
            "HERMES_API_BASE_URL": f"http://127.0.0.1:{author_port}",
            "HERMES_API_KEY": "fake-author-internal-key",
            "HERMES_SOLVER_API_BASE_URL": f"http://127.0.0.1:{solver_port}",
            "HERMES_SOLVER_API_KEY": "fake-solver-internal-key",
            "ZHIJUAN_DEEPSEEK_MODEL_ID": "deepseek-flash",
            "ZHIJUAN_RUNTIME_ID": RUNTIME_ID,
        })
        cls.worker_env = env
        log = open(ROOT / "acceptance-runs/workflow/handoff-localgen-20260922-2000/w6-queue/worker.log", "ab")
        cls.worker_log = log
        cls.worker_proc = subprocess.Popen(
            [".venv/bin/celery", "-A", "services.worker.jobs:app", "worker",
             "--pool=solo", "--concurrency=1", "--without-gossip", "--without-mingle",
             "--without-heartbeat", "--loglevel=INFO"],
            cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT)
        cls._wait_worker_ready()

    @classmethod
    def tearDownClass(cls):
        if cls.worker_proc is not None and cls.worker_proc.poll() is None:
            cls.worker_proc.terminate()
            try:
                cls.worker_proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                cls.worker_proc.kill()
        if getattr(cls, "worker_log", None) is not None:
            cls.worker_log.close()
        cls.author.stop()
        cls.solver.stop()

    @classmethod
    def _wait_worker_ready(cls, timeout: float = 40.0):
        """Real readiness proof: the worker process writes a fresh heartbeat row."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if cls.worker_proc.poll() is not None:
                raise RuntimeError("worker process exited before becoming ready; see worker.log")
            with psycopg.connect(DSN) as conn:
                row = conn.execute(
                    "SELECT count(*) FROM runtime_heartbeats "
                    "WHERE component='worker' AND runtime_id=%s", (RUNTIME_ID,)).fetchone()
            if row[0] > 0:
                return
            time.sleep(0.5)
        raise RuntimeError("worker heartbeat not observed in time; see worker.log")

    def setUp(self):
        self.author.behaviors.clear()
        self.solver.behaviors.clear()
        self._job_ids = []

    def tearDown(self):
        self.author.behaviors.clear()
        self.solver.behaviors.clear()
        # Dedicated disposable database: wipe ALL job runtime rows so leftover
        # pending outbox rows from any earlier run can never be dispatched by a
        # later test's dispatch_outbox() (messages always carry job ids).
        with psycopg.connect(DSN) as conn:
            conn.execute("TRUNCATE generation_job_results, generation_job_outbox, "
                         "generation_job_history, generation_jobs")
            conn.commit()

    def _seed_confirmed_job(self, title: str) -> dict:
        """Save a 1-slot spec, confirm its plan, create the job via the explicit path."""
        from fastapi.testclient import TestClient
        from services.exam.job_service import GenerationJobService
        client = TestClient(self.client_app)
        spec = json.loads((ROOT / "examples/exam-spec-primary.json").read_text())
        spec.update(title=title, stage="primary", stage_year=4)
        spec["sections"] = [dict(spec["sections"][0], count=1, score_each_x100=100)]
        spec["total_score_x100"] = 100
        tag = client.get("/v1/exams/current/spec").headers["etag"]
        response = client.put("/v1/exams/current/spec", json=spec, headers={"If-Match": tag})
        self.assertEqual(response.status_code, 200, response.text)
        tag = response.headers["etag"]
        plan = client.post("/v1/exams/current/plans/generate", json=spec,
                           headers={"If-Match": tag})
        self.assertEqual(plan.status_code, 200, plan.text)
        plan_id = plan.json()["plan_id"]
        confirmed = client.post(f"/v1/exams/current/plans/{plan_id}/confirm",
                                headers={"If-Match": tag})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        job = GenerationJobService.start_job()
        self.assertEqual(job["status"], "QUEUED")
        self._job_ids.append(job["job_id"])
        return job


    def _wait_terminal(self, job_id: str, timeout: float = 90.0) -> dict:
        from services.api.repositories import PostgresJobRepository
        repo = PostgresJobRepository()
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            job = repo.get_by_job_id(job_id)
            last = job
            if job and job["status"] in {"COMPLETED", "PARTIAL_FAILED", "FAILED",
                                         "CANCELLED", "RECONCILING"}:
                return job
            time.sleep(0.5)
        raise AssertionError(f"job did not settle: {last and last.get('status')}")

    def test_normal_completion_single_admission_per_stage(self):
        from services.worker.jobs import dispatch_outbox
        job = self._seed_confirmed_job("队列集成：正常完成")
        self.assertGreaterEqual(dispatch_outbox(), 1)
        final = self._wait_terminal(job["job_id"])
        self.assertEqual(final["status"], "COMPLETED", str(final.get("logs"))[:400])
        self.assertEqual(self.author.counters["admissions"], 1)
        self.assertEqual(self.solver.counters["admissions"], 1)
        self.assertEqual(self.author.admission_roles, ["author"])
        self.assertEqual(self.solver.admission_roles, ["solver"])
        self.assertEqual(set(self.author.admission_models), {"deepseek-flash"})
        from services.api.repositories import PostgresJobRepository
        results = PostgresJobRepository().results(job["job_id"])
        self.assertEqual(len(results), 1)
        # No trusted math proof: blind agreement must stay REVIEW, never PASS.
        self.assertEqual(results[0]["validation"]["overall_status"], "REVIEW")
        # Duplicate dispatch of the same job must not re-admit anything. The
        # outbox row is already marked dispatched (expected count 0); even a
        # redelivered message finds the job non-QUEUED and exits via CAS.
        dispatch_outbox()
        time.sleep(2)
        self.assertEqual(self.author.counters["admissions"], 1)
        self.assertEqual(self.solver.counters["admissions"], 1)

    def test_cancelled_before_worker_never_admits(self):
        from fastapi.testclient import TestClient
        job = self._seed_confirmed_job("队列集成：先取消")
        client = TestClient(self.client_app)
        cancelled = client.post("/v1/exams/current/generation-jobs/current/cancel")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        from services.worker.jobs import dispatch_outbox
        self.assertGreaterEqual(dispatch_outbox(), 1)
        time.sleep(3)
        final = self._wait_terminal(job["job_id"], timeout=10)
        self.assertEqual(final["status"], "CANCELLED")
        self.assertEqual(self.author.counters["admissions"], 0)
        self.assertEqual(self.solver.counters["admissions"], 0)

    def test_admission_5xx_parks_reconciling_without_repost(self):
        self.author.behaviors["__admission__"] = lambda body: {"reject": 500}
        job = self._seed_confirmed_job("队列集成：受理丢失")
        from services.worker.jobs import dispatch_outbox
        self.assertGreaterEqual(dispatch_outbox(), 1)
        final = self._wait_terminal(job["job_id"])
        self.assertEqual(final["status"], "RECONCILING")
        # Exactly one admission attempt: the unknown 5xx must never be retried.
        self.assertEqual(self.author.counters["admit_failures"], 1)
        self.assertEqual(self.author.counters["admissions"], 0)
        self.assertEqual(self.solver.counters["admissions"], 0)

    def test_worker_receives_same_plan_scores(self):
        from services.api.repositories import PostgresJobRepository
        job = self._seed_confirmed_job("队列集成：分值围栏")
        self.assertEqual(job["total_slots"], 1)
        self.assertEqual(job["slots"][0]["score_x100"], 100)
        stored = PostgresJobRepository().get_by_job_id(job["job_id"])
        self.assertEqual(stored["plan_snapshot"]["revision"], job["revision"])
        self.assertEqual(stored["spec_snapshot"]["total_score_x100"], 100)
        from services.worker.jobs import dispatch_outbox
        self.assertGreaterEqual(dispatch_outbox(), 1)
        final = self._wait_terminal(job["job_id"])
        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["slots"][0]["score_x100"], 100)

if __name__ == "__main__":
    unittest.main()
