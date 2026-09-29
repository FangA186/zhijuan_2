from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Generation admission contract tests."""
from tests.generation_accept_shared import *

class GenerationAcceptTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _tag(self):
        return '"3"'

    def _post(self, tag=None, exam_id="current"):
        headers = {} if tag is None else {"If-Match": tag}
        return self.client.post(f"/v1/exams/{exam_id}/generation-jobs", headers=headers)

    def test_missing_if_match_is_428(self):
        GenerationAcceptConfig(self, _ready_blueprint())
        response = self._post(tag=None)
        self.assertEqual(response.status_code, 428)

    def test_stale_if_match_is_412(self):
        GenerationAcceptConfig(self, _ready_blueprint())
        response = self._post(tag='"999"')
        self.assertEqual(response.status_code, 412)

    def test_unconfirmed_plan_is_409_plan_not_confirmed(self):
        bp = _ready_blueprint()
        bp["confirmed"] = False
        GenerationAcceptConfig(self, bp)
        response = self._post(tag=self._tag())
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "PLAN_NOT_CONFIRMED")

    def test_generation_not_ready_is_503_with_reason_codes(self):
        bp = _ready_blueprint()
        config = GenerationAcceptConfig(
            self, bp, ready={"ready": False, "configured": True,
                             "reason_codes": ["WORKER_UNAVAILABLE", "BROKER_UNAVAILABLE"],
                             "components": {"worker": {"ok": False}}, "checked_at": None})
        response = self._post(tag=self._tag())
        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["code"], "GENERATION_NOT_READY")
        self.assertIn("WORKER_UNAVAILABLE", body["reason_codes"])
        self.assertEqual(config.repo.created, 0)

    def test_budget_gateway_unavailable_still_fails_readiness(self):
        bp = _ready_blueprint()
        config = GenerationAcceptConfig(
            self, bp, ready={"ready": False, "configured": True,
                             "reason_codes": ["BUDGET_UNAVAILABLE"],
                             "components": {"budget": {"ok": False}}, "checked_at": None})
        response = self._post(tag=self._tag())
        self.assertEqual(response.status_code, 503)
        self.assertIn("BUDGET_UNAVAILABLE", response.json()["reason_codes"])
        self.assertEqual(config.repo.created, 0)

    def test_acceptance_has_no_per_paper_budget_preflight(self):
        bp = _ready_blueprint(slots=23)
        config = GenerationAcceptConfig(self, bp, ready={"ready": True, "configured": True,
                                                         "reason_codes": [], "components": {},
                                                         "checked_at": None})
        with patch("services.exam.job_service._fetch_budget", create=True,
                   side_effect=AssertionError("per-paper budget preflight must not run")):
            response = self._post(tag=self._tag())
        self.assertEqual(response.status_code, 202)
        self.assertEqual(config.repo.created, 1)
        self.assertEqual(len(config.repo.job["slots"]), 23)
        self.assertNotIn("budget_snapshot", config.repo.job)

    def test_idempotent_replay_returns_existing_job_with_zero_side_effects(self):
        bp = _ready_blueprint()
        config = GenerationAcceptConfig(self, bp, ready={"ready": True, "configured": True,
                                                         "reason_codes": [], "components": {},
                                                         "checked_at": None})
        first = self._post(tag=self._tag())
        self.assertEqual(first.status_code, 202)
        job_id = first.json()["job_id"]
        # Simulate an already-created job (the service must replay it).
        second = self._post(tag=self._tag())
        self.assertEqual(second.status_code, 202)
        self.assertEqual(second.json()["job_id"], job_id)
        self.assertEqual(config.repo.created, 1)
        self.assertEqual(config.repo.outbox_rows, 1)

    def test_success_returns_202_with_job_id_and_status(self):
        bp = _ready_blueprint(slots=2)
        config = GenerationAcceptConfig(self, bp, ready={"ready": True, "configured": True,
                                                         "reason_codes": [], "components": {},
                                                         "checked_at": None})
        response = self._post(tag=self._tag())
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["status"], "QUEUED")
        self.assertTrue(body["job_id"])
        self.assertEqual(config.repo.created, 1)
        self.assertEqual(config.repo.outbox_rows, 1)
        # No private snapshots leaked to the client.
        self.assertNotIn("spec_snapshot", body)
        self.assertNotIn("plan_snapshot", body)
        self.assertNotIn("budget_snapshot", body)
        self.assertNotIn("budget_snapshot", config.repo.job)

    def test_advisory_lock_recheck_rejects_changed_plan(self):
        """Repository create re-verifies the persisted blueprint and rejects."""
        bp = _ready_blueprint()
        config = GenerationAcceptConfig(self, bp, ready={"ready": True, "configured": True,
                                                         "reason_codes": [], "components": {},
                                                         "checked_at": None})
        config.repo.fail_recheck = True
        response = self._post(tag=self._tag())
        self.assertEqual(response.status_code, 500)  # Generic internal error, no raw text
        self.assertEqual(config.repo.created, 0)


if __name__ == "__main__":
    unittest.main()
