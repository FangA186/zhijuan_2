"""Core state, revision, and blueprint persistence operations."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = Path(__file__).resolve().parent / "seed_data.json"


class ExamStoreState:
    _state_fields = ("spec", "sidecar", "spec_revision", "slots", "blueprint", "candidates", "candidate_spec_revision", "candidate_plan_revision", "validation", "adjudications", "publications", "published_exams")

    def __init__(self):
        self._lock = RLock()
        self._store_version = 0
        self._load()
        self._refresh()


    def _load(self):
        if SEED_PATH.is_file():
            data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        else:
            data = {"spec": {}, "slots": [], "candidates": [], "validation": {}}

        raw_spec = data.get("spec", {})
        fields = json.loads((ROOT / "contracts/exam-spec.schema.json").read_text())["properties"]
        self.spec = {k: v for k, v in raw_spec.items() if k in fields}
        self.sidecar = {k: raw_spec[k] for k in ("material_id", "textbook_cover", "chinese_config", "english_config") if k in raw_spec}
        # Legacy seed only: stage_year is an ordinal within its stage in the approved fixtures.
        self.seed_migration_notes = []
        stage, year = self.spec.get("stage"), self.spec.get("stage_year")
        if stage == "junior" and isinstance(year, int) and 7 <= year <= 9:
            self.spec["stage_year"] = year - 6
            self.seed_migration_notes.append("Legacy junior seed stage_year converted to within-stage ordinal")
        elif stage == "senior" and isinstance(year, int) and 10 <= year <= 12:
            self.spec["stage_year"] = year - 9
            self.seed_migration_notes.append("Legacy senior seed stage_year converted to within-stage ordinal")
        self.spec_revision = 1
        self.slots = data.get("slots", [])
        self.blueprint = {
            "exam_id": "exam_demo_01",
            "plan_id": "plan_rev_1",
            "revision": 1,
            "confirmed": False,
            "spec_revision": None,
            "slots": self.slots,
            "total_score_x100": 10000,
            "created_at": "2026-09-17T08:00:00Z",
        }
        self.candidates = data.get("candidates", [])
        self.candidate_spec_revision = self.spec_revision
        self.candidate_plan_revision = self.blueprint.get("revision")
        self.validation = {}  # Seed data is a draft, not trusted check evidence.
        self.adjudications = {}
        self.jobs = {}
        self.publications = {}
        self.published_exams = []


    def _refresh(self) -> None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            return
        import psycopg
        with psycopg.connect(dsn) as conn:
            row = conn.execute("SELECT version, state FROM generation_exam_state WHERE exam_id='current'").fetchone()
        if row:
            self._store_version = row[0]
            for key in self._state_fields:
                if key in row[1]:
                    setattr(self, key, copy.deepcopy(row[1][key]))


    def _persist(self) -> None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            return  # Explicit local draft mode; job creation still requires PostgreSQL.
        import psycopg
        state = {key: getattr(self, key) for key in self._state_fields}
        with psycopg.connect(dsn) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('current', 0))")
            row = conn.execute("SELECT version, state FROM generation_exam_state WHERE exam_id='current' FOR UPDATE").fetchone()
            actual = row[0] if row else 0
            if actual != self._store_version:
                raise ValueError("Draft changed in another process; reload before saving")
            previous = row[1] if row else {}
            old_plan = previous.get("blueprint", {})
            if (previous.get("spec_revision") == self.spec_revision
                    and old_plan.get("plan_hash") != self.blueprint.get("plan_hash")):
                active = conn.execute(
                    "SELECT 1 FROM generation_jobs WHERE exam_id='current' "
                    "AND (snapshot->>'spec_revision')::int=%s "
                    "AND snapshot->>'status' IN ('QUEUED','RUNNING','PAUSED','RECONCILING')",
                    (self.spec_revision,),
                ).fetchone()
                if active:
                    raise ValueError("An active generation job must finish or be cancelled before replanning")
            conn.execute("INSERT INTO generation_exam_state(exam_id,version,state) VALUES ('current',%s,%s::jsonb) ON CONFLICT(exam_id) DO UPDATE SET version=EXCLUDED.version,state=EXCLUDED.state", (actual+1, json.dumps(state)))
            conn.execute("INSERT INTO generation_exam_revisions(exam_id,spec_revision) VALUES ('current',%s) ON CONFLICT(exam_id) DO UPDATE SET spec_revision=EXCLUDED.spec_revision", (self.spec_revision,))
            conn.execute("UPDATE generation_jobs SET snapshot=jsonb_set(jsonb_set(snapshot,'{status}','\"CANCELLED\"'::jsonb),'{version}',to_jsonb((snapshot->>'version')::int+1)) WHERE exam_id='current' AND (snapshot->>'spec_revision')::int<>%s AND snapshot->>'status' IN ('QUEUED','RUNNING','PAUSED','RECONCILING')", (self.spec_revision,))
        self._store_version += 1


    def get_spec(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            return copy.deepcopy({**self.spec, **self.sidecar})


    def get_canonical_spec(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            return copy.deepcopy(self.spec)


    def get_spec_revision(self) -> int:
        with self._lock:
            self._refresh()
            return self.spec_revision


    def update_spec(self, spec: dict[str, Any], *, sidecar: dict | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            if expected_revision is not None and expected_revision != self.spec_revision:
                raise ValueError("Specification revision does not match")
            next_sidecar = copy.deepcopy(sidecar or {})
            if spec != self.spec or next_sidecar != self.sidecar:
                self.spec = copy.deepcopy(spec)
                self.sidecar = next_sidecar
                self.spec_revision += 1
                self.blueprint["confirmed"] = False
                self.blueprint["confirmed_by"] = None
                self.blueprint["confirmed_at"] = None
                self.validation.clear()
                self.adjudications.clear()
            self._persist()
            return copy.deepcopy({**self.spec, **self.sidecar})


    def get_blueprint(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            return copy.deepcopy(self.blueprint)


    @staticmethod
    def _plan_hash(plan: dict) -> str:
        fields = {"exam_id": plan["exam_id"], "spec_revision": plan["spec_revision"], "plan_revision": plan["plan_revision"], "spec": plan["canonical_spec"], "slots": plan["slots"]}
        return hashlib.sha256(json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


    def save_blueprint(self, plan: dict) -> dict:
        with self._lock:
            self._refresh()
            if plan.get("spec_revision") != self.spec_revision or plan.get("canonical_spec") != self.spec:
                raise ValueError("Specification changed while planning")
            if plan.get("plan_hash") != self._plan_hash(plan):
                raise ValueError("Plan hash mismatch")
            self.blueprint = copy.deepcopy(plan)
            self.slots = copy.deepcopy(plan["slots"])
            self.validation.clear()
            self.adjudications.clear()
            self._persist()
            return copy.deepcopy(self.blueprint)


    def confirm_blueprint(self, plan_id: str, expected_revision: int | None = None) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            if plan_id != self.blueprint.get("plan_id") or self.blueprint.get("spec_revision") != self.spec_revision:
                raise ValueError("Plan or specification is stale")
            if expected_revision is not None and expected_revision != self.spec_revision:
                raise ValueError("Specification revision does not match")
            if self.blueprint.get("plan_hash") != self._plan_hash(self.blueprint):
                raise ValueError("Plan content changed after generation")
            self.blueprint.update(confirmed=True, confirmed_by="local-teacher", confirmed_at=datetime.now(timezone.utc).isoformat())
            self._persist()
            return copy.deepcopy(self.blueprint)
