"""Run only with ZHIJUAN_TEST_DATABASE_URL pointed at an isolated disposable PostgreSQL DB."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import unittest
import uuid

from services.api.repositories import PostgresJobRepository


@unittest.skipUnless(os.getenv("ZHIJUAN_TEST_DATABASE_URL"), "isolated PostgreSQL DSN required")
class PostgresJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = PostgresJobRepository(os.environ["ZHIJUAN_TEST_DATABASE_URL"])
        schema = Path(__file__).resolve().parents[2] / "database/003_generation_jobs.sql"
        state_schema = Path(__file__).resolve().parents[2] / "database/004_generation_exam_state.sql"
        with cls.repo.psycopg.connect(cls.repo.dsn) as conn:
            conn.execute(schema.read_text())
            conn.execute(state_schema.read_text())

    def confirmed_plan(self, exam_id, revision=2):
        plan = {"confirmed": True, "spec_revision": 3, "revision": revision,
                "plan_hash": f"fixture-plan-{revision}"}
        state = {"spec_revision": 3, "blueprint": plan}
        with self.repo.psycopg.connect(self.repo.dsn) as conn:
            conn.execute(
                "INSERT INTO generation_exam_state(exam_id,version,state) VALUES (%s,1,%s::jsonb) "
                "ON CONFLICT(exam_id) DO UPDATE SET version=generation_exam_state.version+1,state=EXCLUDED.state",
                (exam_id, json.dumps(state)),
            )
        return plan

    def new_job(self, exam_id, revision=2):
        return {"job_id": str(uuid.uuid4()), "exam_id": exam_id, "version": 1,
                "revision": revision, "spec_revision": 3, "status": "QUEUED",
                "plan_snapshot": {"plan_hash": f"fixture-plan-{revision}"},
                "slots": [{"slot_id": "q1", "order": 1, "status": "PENDING"}],
                "completed_slots": 0, "updated_at": "2026-09-22T00:00:00+00:00"}

    def setUp(self):
        self.exam_ids = []

    def tearDown(self):
        with self.repo.psycopg.connect(self.repo.dsn) as conn:
            for exam_id in self.exam_ids:
                rows = conn.execute("SELECT snapshot->>'job_id' FROM generation_jobs WHERE exam_id=%s UNION SELECT job_id FROM generation_job_history WHERE exam_id=%s", (exam_id,exam_id)).fetchall()
                for (job_id,) in rows:
                    conn.execute("DELETE FROM generation_job_results WHERE job_id=%s", (job_id,))
                    conn.execute("DELETE FROM generation_job_outbox WHERE job_id=%s", (job_id,))
                conn.execute("DELETE FROM generation_job_history WHERE exam_id=%s", (exam_id,))
                conn.execute("DELETE FROM generation_jobs WHERE exam_id=%s", (exam_id,))
                conn.execute("DELETE FROM generation_exam_revisions WHERE exam_id=%s", (exam_id,))
                conn.execute("DELETE FROM generation_exam_state WHERE exam_id=%s", (exam_id,))

    def test_concurrent_create_and_revision_fence(self):
        exam_id = f"jobs-it-20260922-{uuid.uuid4()}"
        self.exam_ids.append(exam_id)
        self.repo.invalidate_exam(exam_id, 3)
        self.confirmed_plan(exam_id)
        with ThreadPoolExecutor(max_workers=8) as pool:
            jobs = list(pool.map(self.repo.create, (self.new_job(exam_id) for _ in range(8))))
        self.assertEqual(len({job["job_id"] for job in jobs}), 1)
        self.assertEqual(self.repo.pending_dispatches()[-1][1], jobs[0]["job_id"])
        job = self.repo.get(exam_id)
        job["status"] = "RUNNING"
        job["slots"][0]["status"] = "AUTHORING"
        job = self.repo.replace(job, job["version"])
        self.repo.invalidate_exam(exam_id, 4)
        with self.assertRaises(RuntimeError):
            self.repo.complete_slot(job["job_id"], "q1", job["version"], {}, {"overall_status": "PASS"})
        self.assertEqual(self.repo.results(job["job_id"]), [])

    def test_fail_result_is_preserved_as_fail(self):
        exam_id = f"jobs-it-20260922-{uuid.uuid4()}"
        self.exam_ids.append(exam_id)
        self.repo.invalidate_exam(exam_id, 3)
        self.confirmed_plan(exam_id)
        job = self.repo.create(self.new_job(exam_id))
        job["status"] = "RUNNING"
        job["slots"][0]["status"] = "AUTHORING"
        job = self.repo.replace(job, job["version"])
        result = self.repo.complete_slot(job["job_id"], "q1", job["version"],
                                         {"public": {"local_id": "q1"}}, {"overall_status": "FAIL"})
        self.assertEqual(result["slots"][0]["status"], "FAIL")
        self.assertEqual(self.repo.results(job["job_id"])[0]["validation"]["overall_status"], "FAIL")

    def test_run_admission_then_cancel_blocks_late_result(self):
        exam_id = f"jobs-it-20260922-{uuid.uuid4()}"
        self.exam_ids.append(exam_id)
        self.repo.invalidate_exam(exam_id, 3)
        self.confirmed_plan(exam_id)
        job = self.repo.create(self.new_job(exam_id))
        job["status"] = "RUNNING"
        job["slots"][0]["status"] = "AUTHORING"
        job = self.repo.replace(job, job["version"])
        ref = f"{job['job_id']}:q1:author"
        version = self.repo.record_run_event(job["job_id"], "q1", job["version"],
                                             {"event": "phase_started", "phase": "author", "task_ref": ref})
        version = self.repo.record_run_event(job["job_id"], "q1", version,
                                             {"event": "hermes_run_admitted", "phase": "author",
                                              "task_ref": ref, "run_id": "hermes-test-run"})
        self.assertEqual(self.repo.get(exam_id)["run_refs"]["q1"]["author"]["run_id"], "hermes-test-run")
        current = self.repo.get(exam_id)
        current["status"] = "CANCELLED"
        self.repo.replace(current, current["version"])
        with self.assertRaises(RuntimeError):
            self.repo.complete_slot(job["job_id"], "q1", version, {}, {"overall_status": "PASS"})
        self.assertEqual(self.repo.results(job["job_id"]), [])

    def test_terminal_replay_is_idempotent_and_new_plan_retains_old_run_refs(self):
        exam_id=f"jobs-it-20260922-{uuid.uuid4()}"
        self.exam_ids.append(exam_id)
        self.repo.invalidate_exam(exam_id,3)
        self.confirmed_plan(exam_id)
        original=self.repo.create(self.new_job(exam_id))
        original["status"]="CANCELLED"
        original["run_refs"]={"q1":{"author":{"run_id":"test-only-preserved-run"}}}
        original=self.repo.replace(original,original["version"])
        replay=self.repo.create(self.new_job(exam_id))
        self.assertEqual(replay["job_id"],original["job_id"])
        self.assertEqual(replay["status"],"CANCELLED")
        self.confirmed_plan(exam_id,3)
        next_job=self.new_job(exam_id,3)
        self.repo.create(next_job)
        historical=self.repo.get_by_job_id(original["job_id"])
        self.assertEqual(historical["run_refs"],original["run_refs"])
        self.assertEqual(self.repo.get(exam_id)["job_id"],next_job["job_id"])

    def test_find_by_plan_returns_existing_job_by_plan_snapshot_hash(self):
        """find_by_plan matches plan_snapshot->>'plan_hash' (top-level plan_hash
        is never written), so a lost-202 replay returns the same job_id without
        re-running readiness/budget gates."""
        exam_id = f"jobs-it-20260922-{uuid.uuid4()}"
        self.exam_ids.append(exam_id)
        self.repo.invalidate_exam(exam_id, 3)
        self.confirmed_plan(exam_id)
        job = self.repo.create(self.new_job(exam_id))
        self.assertNotIn("plan_hash", job)  # top level carries no plan_hash
        self.assertEqual(job["plan_snapshot"]["plan_hash"], "fixture-plan-2")
        found = self.repo.find_by_plan(exam_id, job["spec_revision"],
                                       job["plan_snapshot"]["plan_hash"])
        self.assertIsNotNone(found)
        self.assertEqual(found["job_id"], job["job_id"])
        self.assertEqual(found["status"], "QUEUED")
        # Wrong plan_hash / spec_revision matches nothing.
        self.assertIsNone(self.repo.find_by_plan(exam_id, job["spec_revision"], "other-plan"))
        self.assertIsNone(self.repo.find_by_plan(exam_id, job["spec_revision"] + 1,
                                                 job["plan_snapshot"]["plan_hash"]))
        # Idempotent replay: a terminal status still replays the original job.
        current = self.repo.get(exam_id)
        current["status"] = "COMPLETED"
        self.repo.replace(current, current["version"])
        replayed = self.repo.find_by_plan(exam_id, current["spec_revision"],
                                          current["plan_snapshot"]["plan_hash"])
        self.assertEqual(replayed["job_id"], job["job_id"])
        self.assertIsNotNone(replayed["plan_snapshot"])


if __name__ == "__main__":
    unittest.main()
