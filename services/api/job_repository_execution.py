"""Atomic execution result and Hermes event persistence."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any
from .job_run_events import apply_run_event


class JobRepositoryExecutionMixin:
    def complete_slot(self, job_id: str, slot_id: str, expected_version: int,
                      candidate: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
        """Save private result and public progress together, rejecting stale/cancelled work."""
        with self.psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                # Job id resolves the exam before the shared advisory lock.
                exam_row = conn.execute(
                    "SELECT exam_id FROM generation_jobs WHERE snapshot->>'job_id' = %s", (job_id,)
                ).fetchone()
                if not exam_row:
                    raise RuntimeError("Job no longer exists")
                conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (exam_row[0],))
                row = conn.execute(
                    "SELECT snapshot FROM generation_jobs WHERE snapshot->>'job_id' = %s FOR UPDATE",
                    (job_id,),
                ).fetchone()
                if not row:
                    raise RuntimeError("Job no longer exists")
                job = row[0]
                if job["version"] != expected_version or job["status"] != "RUNNING":
                    raise RuntimeError("Job version changed or execution cancelled")
                revision = conn.execute(
                    "SELECT spec_revision FROM generation_exam_revisions WHERE exam_id = %s",
                    (job["exam_id"],),
                ).fetchone()
                if not revision or revision[0] != job["spec_revision"]:
                    raise RuntimeError("Specification revision changed")
                target = next((s for s in job["slots"] if s["slot_id"] == slot_id), None)
                if not target or target["status"] != "AUTHORING":
                    raise RuntimeError("Slot is not authoring")
                target["question_revision_id"] = validation.get("revision", {}).get("question_revision_id")
                status = validation.get("overall_status", "REVIEW")
                target["status"] = "READY" if status == "PASS" else "FAIL" if status == "FAIL" else "REVIEW_REQUIRED"
                job["completed_slots"] = sum(s["status"] in {"READY", "REVIEW_REQUIRED", "FAIL"} for s in job["slots"])
                job["version"] += 1
                conn.execute(
                    "INSERT INTO generation_job_results (job_id, slot_id, candidate, validation) "
                    "VALUES (%s, %s, %s::jsonb, %s::jsonb) ON CONFLICT (job_id, slot_id) "
                    "DO UPDATE SET candidate = EXCLUDED.candidate, validation = EXCLUDED.validation",
                    (job_id, slot_id, json.dumps(candidate), json.dumps(validation)),
                )
                conn.execute(
                    "UPDATE generation_jobs SET snapshot = %s::jsonb WHERE exam_id = %s",
                    (json.dumps(job), job["exam_id"]),
                )
                return copy.deepcopy(job)


    def record_run_event(self, job_id: str, slot_id: str, expected_version: int,
                         event: dict[str, Any]) -> int:
        """Persist external admission identifiers before another phase can proceed."""
        with self.psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                exam_row = conn.execute(
                    "SELECT exam_id FROM generation_jobs WHERE snapshot->>'job_id' = %s", (job_id,)
                ).fetchone()
                if not exam_row:
                    raise RuntimeError("Job no longer exists")
                conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (exam_row[0],))
                row = conn.execute(
                    "SELECT snapshot FROM generation_jobs WHERE exam_id = %s FOR UPDATE", (exam_row[0],)
                ).fetchone()
                job = row[0]
                if job["job_id"] != job_id or job["version"] != expected_version or job["status"] != "RUNNING":
                    raise RuntimeError("Job changed or cancelled")
                slot = next((s for s in job["slots"] if s["slot_id"] == slot_id), None)
                if not slot or slot["status"] != "AUTHORING":
                    raise RuntimeError("Slot is not authoring")
                apply_run_event(job, slot, event)
                job["version"] += 1
                job["updated_at"] = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "UPDATE generation_jobs SET snapshot = %s::jsonb WHERE exam_id = %s",
                    (json.dumps(job), exam_row[0]),
                )
                return job["version"]
