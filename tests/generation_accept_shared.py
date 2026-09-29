"""Offline acceptance-gate tests for start_generation_job (C5 contract).

Covers the gate order: If-Match (428/412) -> confirmed blueprint (409
PLAN_NOT_CONFIRMED) -> idempotent replay (202 zero side effects) -> real
readiness (503 GENERATION_NOT_READY with reason_codes) -> success (202 with
job_id) -> advisory-lock re-check rejection. No real database or model.

Uses fastapi TestClient with a fake repository.
"""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.main import app
from services.exam.job_service import GenerationJobService


def _ready_blueprint(spec_revision: int = 3, plan_hash: str = "plan-hash-1",
                     slots: int = 2) -> dict:
    return {
        "confirmed": True,
        "revision": 2,
        "spec_revision": spec_revision,
        "plan_revision": 2,
        "plan_hash": plan_hash,
        "slots": [{"slot_id": f"slot_q0{i}", "order": i, "kind": "single_choice"}
                  for i in range(1, slots + 1)],
    }


class FakeRepo:
    """Minimal in-memory repository tracking create/find_by_plan side effects."""

    def __init__(self):
        self.job = None
        self.created = 0
        self.outbox_rows = 0
        self.fail_recheck = False

    def find_by_plan(self, exam_id, spec_revision, plan_hash):
        if self.job is None:
            return None
        if (self.job["exam_id"] == exam_id
                and self.job["spec_revision"] == spec_revision
                and self.job.get("plan_snapshot", {}).get("plan_hash") == plan_hash):
            return copy.deepcopy(self.job)
        return None

    def create(self, job):
        if self.fail_recheck:
            raise RuntimeError("Confirmed blueprint changed before job creation")
        if self.job is not None:
            raise RuntimeError("An active job already exists for another revision")
        self.job = copy.deepcopy(job)
        self.created += 1
        self.outbox_rows += 1
        return copy.deepcopy(self.job)


class GenerationAcceptConfig:
    """Patch harness around the store/blueprint/services.

    Patches are started in the constructor and stopped by test cleanup.
    """

    def __init__(self, testcase, bp, spec_revision=3, ready=None):
        self.testcase = testcase
        self.repo = FakeRepo()
        self.patches = [
            patch.object(GenerationJobService, "_repository", self.repo),
            patch("services.api.routes.exams.generation_configuration",
                  return_value={"configured": True}),
            patch("services.exam.job_service.BlueprintService.get_blueprint",
                  return_value=bp),
            patch("services.exam.job_service.store.get_spec_revision",
                  return_value=spec_revision, create=True),
            patch("services.exam.job_service.store.get_canonical_spec",
                  return_value={"subject": "math"}, create=True),
        ]
        if ready is not None:
            self.patches.append(patch.object(GenerationJobService, "runtime_readiness",
                                             return_value=ready))
        _start_all(self.patches)
        testcase.addCleanup(_stop_all, self.patches)


def _start_all(patches):
    for item in patches:
        item.start()


def _stop_all(patches):
    for item in patches:
        item.stop()



__all__ = [name for name in globals() if not name.startswith("__")]
