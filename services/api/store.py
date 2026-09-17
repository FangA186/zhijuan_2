"""In-memory state store with JSON backing for Zhijuan Exam API."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import copy

ROOT = Path(__file__).resolve().parents[2]
SEED_PATH = Path(__file__).resolve().parent / "seed_data.json"

class ExamStore:
    def __init__(self):
        self._load()

    def _load(self):
        if SEED_PATH.is_file():
            data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        else:
            data = {"spec": {}, "slots": [], "candidates": [], "validation": {}}

        self.spec = data.get("spec", {})
        self.slots = data.get("slots", [])
        self.blueprint = {
            "exam_id": "exam_demo_01",
            "plan_id": "plan_rev_1",
            "revision": 1,
            "confirmed": True,
            "slots": self.slots,
            "total_score_x100": 10000,
            "created_at": "2026-09-17T08:00:00Z",
        }
        self.candidates = data.get("candidates", [])
        self.validation = data.get("validation", {})
        self.adjudications = {}
        self.jobs = {}

    def get_spec(self) -> dict[str, Any]:
        return copy.deepcopy(self.spec)

    def update_spec(self, spec: dict[str, Any]) -> dict[str, Any]:
        self.spec = copy.deepcopy(spec)
        return self.spec

    def get_blueprint(self) -> dict[str, Any]:
        return copy.deepcopy(self.blueprint)

    def confirm_blueprint(self, plan_id: str) -> dict[str, Any]:
        self.blueprint["confirmed"] = True
        self.blueprint["revision"] += 1
        return copy.deepcopy(self.blueprint)

    def get_candidates(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.candidates)

    def get_candidate(self, local_id: str) -> dict[str, Any] | None:
        for c in self.candidates:
            if c.get("public", {}).get("local_id") == local_id:
                return copy.deepcopy(c)
        return None

    def update_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        local_id = candidate.get("public", {}).get("local_id")
        for idx, c in enumerate(self.candidates):
            if c.get("public", {}).get("local_id") == local_id:
                self.candidates[idx] = copy.deepcopy(candidate)
                # Invalidate old validation checks
                if local_id in self.validation:
                    self.validation[local_id]["overall_status"] = "REVIEW"
                    self.validation[local_id]["rule_checks"].append({
                        "rule_id": "RULE_CONTENT_CHANGED",
                        "category": "structure",
                        "name": "题面手动修改",
                        "status": "REVIEW",
                        "detail": "教师手动编辑了题面或答案，原有自动校验依据已过期，需要人工复核。",
                    })
                return candidate
        self.candidates.append(copy.deepcopy(candidate))
        return candidate

    def get_validation(self) -> dict[str, Any]:
        return copy.deepcopy(self.validation)

    def get_adjudications(self) -> dict[str, Any]:
        return copy.deepcopy(self.adjudications)

    def submit_adjudication(self, record: dict[str, Any]) -> None:
        item_id = record.get("item_id")
        if item_id:
            self.adjudications[item_id] = copy.deepcopy(record)

store = ExamStore()
