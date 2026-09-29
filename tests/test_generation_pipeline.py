"""Offline lifecycle checks; no model call or database required."""
from __future__ import annotations

import asyncio
import copy
import json
import unittest
from unittest.mock import patch

from services.exam.job_service import GenerationJobService


class FakeRepository:
    def __init__(self):
        self.job = None
        self.dispatches = 0

    def get(self, exam_id):
        return copy.deepcopy(self.job) if self.job and self.job["exam_id"] == exam_id else None

    def results(self, job_id):
        return []

    def create(self, job):
        if self.job and self.job["status"] not in {"CANCELLED", "COMPLETED", "FAILED"}:
            return copy.deepcopy(self.job)
        self.job = copy.deepcopy(job)
        self.dispatches += 1
        return self.get(job["exam_id"])

    def replace(self, job, expected_version, *, dispatch=False):
        if self.job["version"] != expected_version:
            raise RuntimeError("stale version")
        self.job = copy.deepcopy(job)
        self.job["version"] += 1
        self.dispatches += int(dispatch)
        return copy.deepcopy(self.job)


class GenerationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepository()
        GenerationJobService._repository = self.repo
        self.bp = {"confirmed": True, "revision": 2, "spec_revision": 3,
                   "slots": [{"slot_id": "slot_q01", "order": 1, "kind": "single_choice"}]}
        self.patches = [
            patch("services.exam.job_service.BlueprintService.get_blueprint", return_value=self.bp),
            patch("services.exam.job_service.store.get_canonical_spec", return_value={"subject": "math"}, create=True),
            patch("services.exam.job_service.store.get_spec_revision", return_value=3, create=True),
            patch("services.exam.job_service.store.get_blueprint", return_value=self.bp),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in self.patches:
            item.stop()
        GenerationJobService._repository = None

    def test_explicit_start_and_read_only_stream(self):
        self.assertIsNone(GenerationJobService.get_current_job())
        job = GenerationJobService.start_job()
        self.assertEqual(job["status"], "QUEUED")
        self.assertIsNone(job["tokens_used"])
        self.assertNotIn("spec_snapshot", job)
        self.assertNotIn("plan_snapshot", job)
        self.assertEqual(GenerationJobService.start_job()["job_id"], job["job_id"])
        self.assertEqual(self.repo.dispatches, 1)

        async def first_event():
            stream = GenerationJobService.stream_job_events()
            try:
                return await stream.__anext__()
            finally:
                await stream.aclose()
        event = asyncio.run(first_event())
        self.assertEqual(json.loads(event.split("data: ", 1)[1])["status"], "QUEUED")
        self.assertEqual(self.repo.dispatches, 1)
        with self.assertRaises(RuntimeError):
            GenerationJobService.step_job()

    def test_revision_gate_and_cancel_resume(self):
        self.bp["spec_revision"] = 1
        with self.assertRaises(ValueError):
            GenerationJobService.start_job()
        self.bp["spec_revision"] = 3
        GenerationJobService.start_job()
        GenerationJobService.pause_job()
        self.assertEqual(GenerationJobService.resume_job()["status"], "QUEUED")
        self.assertEqual(self.repo.dispatches, 2)
        self.assertEqual(GenerationJobService.cancel_job()["status"], "CANCELLED")
        with self.assertRaises(ValueError):
            GenerationJobService.resume_job()


if __name__ == "__main__":
    unittest.main()

class WorkerBoundaryTests(unittest.TestCase):
    def test_run_refs_are_stable_and_failed_check_is_not_completed(self):
        from services.worker.jobs import run_job

        class Repo(FakeRepository):
            def get_by_job_id(self, job_id):
                return self.get("current")

            def results(self, job_id):
                if job_id != 'job1': raise AssertionError('Only current job may be read')
                return [{'candidate': {'public': {'local_id': 'q00', 'prompt': []}, 'private': {'answers': ['private']}}}]

            def record_run_event(self, job_id, slot_id, version, event):
                self.assert_version(version)
                self.job.setdefault("run_refs", {}).setdefault(slot_id, {})[event["phase"]] = event
                self.job["version"] += 1
                return self.job["version"]

            def assert_version(self, version):
                if self.job["version"] != version:
                    raise RuntimeError("stale version")

            def complete_slot(self, job_id, slot_id, version, candidate, validation):
                self.assert_version(version)
                self.job["slots"][0]["status"] = "FAIL" if validation["overall_status"] == "FAIL" else "READY"
                self.job["version"] += 1
                return self.get("current")

        repo = Repo()
        repo.job = {"job_id": "job1", "exam_id": "current", "version": 1, "status": "QUEUED",
                    "started_at": None, "spec_snapshot": {"subject": "math"},
                    "spec_revision": 3, "revision": 5,
                    "slots": [{"slot_id": "slot_q01", "order": 1, "status": "PENDING"}], "logs": []}

        def generate(local_id, exam_id, *, spec, slot, task_refs, run_event, cancellation_requested, previous_questions):
            self.assertFalse(cancellation_requested())
            self.assertEqual(previous_questions, [{'local_id': 'q00', 'prompt': []}])
            self.assertEqual(task_refs["author"], "job1:slot_q01:author")
            self.assertEqual(slot["spec_revision"], 3)
            self.assertEqual(slot["plan_revision"], 5)
            self.assertEqual(slot["question_revision_id"], "job1:slot_q01")
            run_event({"event": "phase_started", "phase": "author", "task_ref": task_refs["author"]})
            run_event({"event": "hermes_run_admitted", "phase": "author",
                       "task_ref": task_refs["author"], "run_id": "real-run-123"})
            return {"candidate": {}, "validation": {"overall_status": "FAIL"}}

        run_job("job1", repository=repo, generate=generate)
        self.assertEqual(repo.job["status"], "PARTIAL_FAILED")
        self.assertEqual(repo.job["slots"][0]["status"], "FAIL")
        self.assertEqual(repo.job["run_refs"]["slot_q01"]["author"]["run_id"], "real-run-123")

    def test_cancel_during_generation_cannot_commit_result(self):
        from services.worker.jobs import run_job

        class Repo(FakeRepository):
            def get_by_job_id(self, job_id):
                return self.get("current")

            def complete_slot(self, *args):
                raise AssertionError("cancelled result must not commit")

        repo = Repo()
        repo.job = {
            "job_id": "job1", "exam_id": "current", "version": 1, "status": "QUEUED",
            "started_at": None, "spec_snapshot": {"subject": "math"},
            "spec_revision": 3, "revision": 5,
            "slots": [{"slot_id": "slot_q01", "order": 1, "status": "PENDING"}],
            "logs": [],
        }

        def generate(*args, **kwargs):
            self.assertEqual(kwargs["slot"]["spec_revision"], 3)
            self.assertEqual(kwargs["slot"]["plan_revision"], 5)
            self.assertEqual(kwargs["slot"]["question_revision_id"], "job1:slot_q01")
            repo.job["status"] = "CANCELLED"
            repo.job["version"] += 1
            return {"candidate": {"public": {}}, "validation": {"overall_status": "PASS"}}

        run_job("job1", repository=repo, generate=generate)
        self.assertEqual(repo.job["status"], "CANCELLED")
