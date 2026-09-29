"""Outbox dispatch and stale job reconciliation."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any


class JobRepositoryOutboxMixin:
    def pending_dispatches(self, limit: int = 20) -> list[tuple[int, str]]:
        with self.psycopg.connect(self.dsn) as conn:
            rows = conn.execute(
                "SELECT id, job_id FROM generation_job_outbox WHERE dispatched_at IS NULL ORDER BY id LIMIT %s", (limit,)
            ).fetchall()
            return [(int(row[0]), str(row[1])) for row in rows]


    def mark_dispatched(self, outbox_id: int) -> None:
        with self.psycopg.connect(self.dsn) as conn:
            conn.execute(
                "UPDATE generation_job_outbox SET dispatched_at = now() WHERE id = %s",
                (outbox_id,),
            )


    def invalidate_exam(self, exam_id: str, new_spec_revision: int) -> None:
        """Called in the same specification update flow before any new job can commit."""
        with self.psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (exam_id,))
                conn.execute(
                    "INSERT INTO generation_exam_revisions (exam_id, spec_revision) VALUES (%s, %s) "
                    "ON CONFLICT (exam_id) DO UPDATE SET spec_revision = EXCLUDED.spec_revision",
                    (exam_id, new_spec_revision),
                )
                row = conn.execute(
                    "SELECT snapshot FROM generation_jobs WHERE exam_id = %s FOR UPDATE", (exam_id,)
                ).fetchone()
                if row and row[0]["status"] not in {"CANCELLED", "FAILED", "COMPLETED", "PARTIAL_FAILED"}:
                    job = row[0]
                    job["status"] = "CANCELLED"
                    job["version"] += 1
                    job["updated_at"] = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        "UPDATE generation_jobs SET snapshot = %s::jsonb WHERE exam_id = %s",
                        (json.dumps(job), exam_id),
                    )


    def reconcile_stale(self, older_than_seconds: int = 1800) -> int:
        """Quarantine interrupted runs; never replay a possibly billed model call."""
        count = 0
        with self.psycopg.connect(self.dsn) as conn:
            with conn.transaction():
                rows = conn.execute(
                    "SELECT exam_id, snapshot FROM generation_jobs "
                    "WHERE snapshot->>'status' = 'RUNNING' "
                    "AND (snapshot->>'updated_at')::timestamptz < now() - (%s * interval '1 second') "
                    "FOR UPDATE SKIP LOCKED",
                    (older_than_seconds,),
                ).fetchall()
                for exam_id, job in rows:
                    job["status"] = "RECONCILING"
                    job["version"] += 1
                    job["updated_at"] = datetime.now(timezone.utc).isoformat()
                    conn.execute(
                        "UPDATE generation_jobs SET snapshot = %s::jsonb WHERE exam_id = %s",
                        (json.dumps(job), exam_id),
                    )
                    count += 1
        return count


    def results(self, job_id: str) -> list[dict[str, Any]]:
        with self.psycopg.connect(self.dsn) as conn:
            rows = conn.execute(
                "SELECT slot_id, candidate, validation FROM generation_job_results WHERE job_id = %s ORDER BY slot_id",
                (job_id,),
            ).fetchall()
            return [{"slot_id": row[0], "candidate": row[1], "validation": row[2]} for row in rows]
