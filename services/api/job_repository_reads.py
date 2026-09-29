"""Job snapshot reads and admission transactions."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any


class JobRepositoryReadMixin:
    def get(self, exam_id: str) -> dict[str, Any] | None:
        with self.psycopg.connect(self.dsn) as conn:
            row = conn.execute("SELECT snapshot FROM generation_jobs WHERE exam_id = %s", (exam_id,)).fetchone()
            return copy.deepcopy(row[0]) if row else None


    def get_by_job_id(self, job_id: str) -> dict[str, Any] | None:
        with self.psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                "SELECT snapshot FROM generation_jobs WHERE snapshot->>'job_id' = %s", (job_id,)
            ).fetchone()
            if not row:
                row = conn.execute("SELECT snapshot FROM generation_job_history WHERE job_id=%s", (job_id,)).fetchone()
            return copy.deepcopy(row[0]) if row else None


    def find_by_plan(self, exam_id: str, spec_revision: int, plan_hash: str) -> dict[str, Any] | None:
        """Return the existing job bound to the same confirmed blueprint, if any.

        Used by the accept path for idempotent replay: a start request for the
        same spec_revision + plan_hash returns the already-created job in any
        state without creating a new job, a new outbox row or any budget probe.
        Read-only: never touches outbox or draft rows.
        """
        with self.psycopg.connect(self.dsn) as conn:
            row = conn.execute(
                "SELECT snapshot FROM generation_jobs WHERE exam_id = %s "
                "AND (snapshot->>'spec_revision')::int = %s "
                "AND (snapshot->'plan_snapshot'->>'plan_hash') = %s",
                (exam_id, spec_revision, plan_hash),
            ).fetchone()
            return copy.deepcopy(row[0]) if row else None


    def create(self, job: dict[str, Any]) -> dict[str, Any]:
        with self.psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (job["exam_id"],))
                revision = conn.execute(
                    "SELECT spec_revision FROM generation_exam_revisions WHERE exam_id = %s",
                    (job["exam_id"],),
                ).fetchone()
                if not revision or revision[0] != job["spec_revision"]:
                    raise RuntimeError("Current specification revision is not registered")
                draft = conn.execute(
                    "SELECT state FROM generation_exam_state WHERE exam_id=%s FOR UPDATE",
                    (job["exam_id"],),
                ).fetchone()
                plan = draft[0].get("blueprint", {}) if draft else {}
                expected_plan = job.get("plan_snapshot", {})
                if (not plan.get("confirmed") or plan.get("spec_revision") != job["spec_revision"]
                        or plan.get("revision") != job["revision"]
                        or plan.get("plan_hash") != expected_plan.get("plan_hash")):
                    raise RuntimeError("Confirmed blueprint changed before job creation")
                row = conn.execute(
                    "SELECT snapshot FROM generation_jobs WHERE exam_id = %s FOR UPDATE",
                    (job["exam_id"],),
                ).fetchone()
                if row:
                    previous = row[0]
                    if previous["revision"] == job["revision"] and previous["spec_revision"] == job["spec_revision"]:
                        return copy.deepcopy(previous)
                    if previous["status"] not in {"COMPLETED", "PARTIAL_FAILED", "CANCELLED", "FAILED"}:
                        raise ValueError("An active job already exists for another revision")
                    conn.execute("INSERT INTO generation_job_history(job_id,exam_id,snapshot) VALUES (%s,%s,%s::jsonb) ON CONFLICT(job_id) DO NOTHING", (previous["job_id"],job["exam_id"],json.dumps(previous)))
                conn.execute(
                    "INSERT INTO generation_jobs (exam_id, snapshot) VALUES (%s, %s::jsonb) "
                    "ON CONFLICT (exam_id) DO UPDATE SET snapshot = EXCLUDED.snapshot",
                    (job["exam_id"], json.dumps(job)),
                )
                conn.execute(
                    "INSERT INTO generation_job_outbox (job_id, event_type) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (job["job_id"], f"dispatch:{job['version']}"),
                )
                return copy.deepcopy(job)


    def replace(self, job: dict[str, Any], expected_version: int, *, dispatch: bool = False) -> dict[str, Any]:
        updated = copy.deepcopy(job)
        updated["version"] = expected_version + 1
        updated["updated_at"] = datetime.now(timezone.utc).isoformat()
        with self.psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                row = conn.execute(
                    "UPDATE generation_jobs SET snapshot = %s::jsonb WHERE exam_id = %s "
                    "AND snapshot->>'job_id' = %s AND (snapshot->>'version')::int = %s "
                    "RETURNING snapshot",
                    (json.dumps(updated), job["exam_id"], job["job_id"], expected_version),
                ).fetchone()
                if not row:
                    raise RuntimeError("Job changed; retry from current snapshot")
                if dispatch:
                    conn.execute(
                        "INSERT INTO generation_job_outbox (job_id, event_type) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (job["job_id"], f"dispatch:{updated['version']}"),
                    )
        return updated
