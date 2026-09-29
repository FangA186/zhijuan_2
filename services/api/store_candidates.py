"""Candidate, validation, and adjudication operations for ExamStore."""
from __future__ import annotations

import copy
from typing import Any


class ExamStoreCandidateMixin:
    def get_candidates(self) -> list[dict[str, Any]]:
        with self._lock:
            self._refresh()
            return copy.deepcopy(self.candidates) if (self.candidate_spec_revision == self.spec_revision
                and self.candidate_plan_revision == self.blueprint.get("revision")) else []


    def get_candidate(self, local_id: str) -> dict[str, Any] | None:
        for c in self.get_candidates():
            if c.get("public", {}).get("local_id") == local_id:
                return copy.deepcopy(c)
        return None


    def update_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        if self.candidate_spec_revision != self.spec_revision or self.candidate_plan_revision != self.blueprint.get("revision"):
            raise ValueError("Old draft questions cannot be edited under a changed specification or blueprint")
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
        return copy.deepcopy(self.validation) if (self.candidate_spec_revision == self.spec_revision
            and self.candidate_plan_revision == self.blueprint.get("revision")) else {}


    def get_adjudications(self) -> dict[str, Any]:
        return copy.deepcopy(self.adjudications) if (self.candidate_spec_revision == self.spec_revision
            and self.candidate_plan_revision == self.blueprint.get("revision")) else {}


    def submit_adjudication(self, record: dict[str, Any]) -> None:
        item_id = record.get("item_id")
        if item_id:
            self.adjudications[item_id] = copy.deepcopy(record)
