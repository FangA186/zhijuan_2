"""Generation job lifecycle. HTTP reads never perform model work."""
from __future__ import annotations

import asyncio
import copy
import json
import uuid
from typing import Any

from ..api.repositories import PostgresJobRepository
from ..api.store import store
from .blueprint_service import BlueprintService
from .job_contracts import AcceptError, _now


class GenerationJobService:
    _repository: Any = None  # Tests may inject a fake; production defaults to PostgreSQL.

    @classmethod
    def repository(cls):
        return cls._repository if cls._repository is not None else PostgresJobRepository()

    @staticmethod
    def _public(job: dict[str, Any] | None) -> dict[str, Any] | None:
        if job is None:
            return None
        return {key: copy.deepcopy(value) for key, value in job.items()
                if key not in {"spec_snapshot", "plan_snapshot", "run_refs", "budget_snapshot", "activity", "activity_seq", "activity_dropped"}}

    @staticmethod
    def _plan_hash(bp: dict[str, Any]) -> Any:
        return bp.get("plan_hash")

    @classmethod
    def start_job(cls, exam_id: str = "current") -> dict[str, Any]:
        """Legacy direct creation; acceptance gates live in ``accept_job``.

        Kept for callers that already performed the revision/plan checks
        (notably the worker-facing tests); it never contacts the budget proxy
        nor any model. New HTTP admission must use ``accept_job``.
        """
        bp = BlueprintService.get_blueprint(exam_id)
        spec = store.get_canonical_spec()
        if not bp.get("confirmed") or not bp.get("slots"):
            raise ValueError("A confirmed blueprint with slots is required")
        spec_revision = store.get_spec_revision()
        if spec_revision is None or bp.get("spec_revision") != spec_revision:
            raise ValueError("Blueprint spec_revision does not match the current specification")
        slots = [{**copy.deepcopy(slot), "status": "PENDING"} for slot in bp["slots"]]
        job = {
            "job_id": str(uuid.uuid4()), "exam_id": exam_id,
            "revision": bp["revision"], "spec_revision": spec_revision,
            "status": "QUEUED", "version": 1, "total_slots": len(slots),
            "completed_slots": 0, "tokens_used": None, "estimated_cost_cny": None,
            "usage_status": "UNKNOWN", "started_at": None, "updated_at": _now(),
            "slots": slots, "logs": [],
            "spec_snapshot": copy.deepcopy(spec),
            "plan_snapshot": copy.deepcopy(bp),
        }
        return cls._public(cls.repository().create(job))

    @classmethod
    def accept_job(cls, exam_id: str = "current") -> dict[str, Any]:
        """Admission chain for start_generation_job (C5 contract).

        Order: current range & If-Match (route) -> confirmed blueprint ->
        idempotent replay (same spec_revision+plan_hash returns the existing
        job in any state; zero side effects, never bills) -> real readiness ->
        advisory lock re-check of the persisted blueprint ->
        single transaction writing job + outbox.
        The HTTP thread never calls a model.
        """
        bp = BlueprintService.get_blueprint(exam_id)
        if not bp or not bp.get("confirmed"):
            raise AcceptError(409, "PLAN_NOT_CONFIRMED", "请先生成并确认蓝图")
        spec_revision = store.get_spec_revision()
        if spec_revision is None or bp.get("spec_revision") != spec_revision:
            raise AcceptError(412, "ETAG_MISMATCH", "蓝图与当前规格版本不一致，请重新加载")
        plan_hash = cls._plan_hash(bp)
        if not plan_hash:
            raise AcceptError(409, "PLAN_NOT_CONFIRMED", "蓝图缺少 plan_hash，请重新生成并确认")

        existing = cls.repository().find_by_plan(exam_id, spec_revision, plan_hash)
        if existing is not None:
            return cls._public(copy.deepcopy(existing))

        readiness = cls.runtime_readiness()
        if not readiness.get("ready"):
            reason_codes = readiness.get("reason_codes") or ["NOT_CONFIGURED"]
            raise AcceptError(503, "GENERATION_NOT_READY", "生成服务尚未就绪，暂不能开始出题",
                              reason_codes=reason_codes)

        slots = [{**copy.deepcopy(slot), "status": "PENDING"} for slot in bp["slots"]]
        job = {
            "job_id": str(uuid.uuid4()), "exam_id": exam_id,
            "revision": bp["revision"], "spec_revision": spec_revision,
            "status": "QUEUED", "version": 1, "total_slots": len(slots),
            "completed_slots": 0, "tokens_used": None, "estimated_cost_cny": None,
            "usage_status": "UNKNOWN", "started_at": None, "updated_at": _now(),
            "slots": slots, "logs": [],
            "spec_snapshot": copy.deepcopy(store.get_canonical_spec()),
            "plan_snapshot": copy.deepcopy(bp),
        }
        return cls._public(cls.repository().create(job))

    @classmethod
    def replay_job(cls, exam_id: str = "current") -> dict[str, Any] | None:
        """Look up the existing job for the current confirmed blueprint.

        Used after a lost 202 response: never creates anything and never
        touches the budget proxy.
        """
        bp = BlueprintService.get_blueprint(exam_id)
        if not bp or not bp.get("confirmed"):
            return None
        spec_revision = store.get_spec_revision()
        plan_hash = cls._plan_hash(bp)
        if spec_revision is None or not plan_hash:
            return None
        job = cls.repository().find_by_plan(exam_id, spec_revision, plan_hash)
        return cls._public(copy.deepcopy(job)) if job is not None else None

    @classmethod
    def runtime_readiness(cls) -> dict[str, Any]:
        """Delegate to the C1 readiness probe; fail closed when unavailable."""
        try:
            from ..api.health import runtime_readiness
            result = runtime_readiness()
            if isinstance(result, dict) and isinstance(result.get("ready"), bool):
                return result
        except Exception:
            pass
        return {"ready": False, "configured": False, "checked_at": None,
                "reason_codes": ["NOT_CONFIGURED"], "components": {}}

    @classmethod
    def get_current_job(cls, exam_id: str = "current") -> dict[str, Any] | None:
        job = cls.repository().get(exam_id)
        if not job:
            return None
        plan = store.get_blueprint()
        if (job.get("spec_revision") != store.get_spec_revision()
                or job.get("revision") != plan.get("revision")
                or job.get("plan_snapshot", {}).get("plan_hash") != plan.get("plan_hash")):
            return None
        return cls._public(job)

    @classmethod
    def _transition(cls, exam_id: str, allowed: set[str], status: str, dispatch: bool = False) -> dict[str, Any]:
        repo = cls.repository()
        job = repo.get(exam_id)
        if not job:
            raise ValueError("No generation job found")
        if job["status"] not in allowed:
            raise ValueError(f"Cannot transition {job['status']} to {status}")
        previous = job["version"]
        job["status"] = status
        job["updated_at"] = _now()
        job["logs"].append({"timestamp": job["updated_at"], "role": "system", "level": "info", "message": status})
        return cls._public(repo.replace(job, previous, dispatch=dispatch))

    @classmethod
    def pause_job(cls, exam_id: str = "current") -> dict[str, Any]:
        return cls._transition(exam_id, {"QUEUED", "RUNNING"}, "PAUSED")

    @classmethod
    def resume_job(cls, exam_id: str = "current") -> dict[str, Any]:
        job = cls.get_current_job(exam_id)
        if job and any(slot["status"] == "AUTHORING" for slot in job["slots"]):
            return cls._transition(exam_id, {"PAUSED"}, "RECONCILING")
        return cls._transition(exam_id, {"PAUSED"}, "QUEUED", dispatch=True)

    @classmethod
    def cancel_job(cls, exam_id: str = "current") -> dict[str, Any]:
        return cls._transition(exam_id, {"QUEUED", "RUNNING", "PAUSED", "RECONCILING"}, "CANCELLED")

    @classmethod
    def step_job(cls, exam_id: str = "current", slot_id: str | None = None) -> dict[str, Any]:
        raise RuntimeError("Manual job steps are disabled; the worker owns execution")

    @classmethod
    async def stream_job_events(cls, exam_id: str = "current"):
        previous_version = None
        while True:
            job = cls.get_current_job(exam_id)
            if job is None:
                yield 'event: error\ndata: {"detail":"No generation job found"}\n\n'
                return
            if job["version"] != previous_version:
                yield f"event: init\ndata: {json.dumps(job, ensure_ascii=False)}\n\n"
                previous_version = job["version"]
            if job["status"] in {"COMPLETED", "PARTIAL_FAILED", "CANCELLED", "FAILED"}:
                event = "completed" if job["status"] == "COMPLETED" else "cancelled" if job["status"] == "CANCELLED" else "failed"
                yield f"event: {event}\ndata: {json.dumps(job, ensure_ascii=False)}\n\n"
                return
            await asyncio.sleep(1)
