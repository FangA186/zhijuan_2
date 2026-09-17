"""Comparator for Blind Solver vs Candidate Reference Answers.

Produces structured BlindSolveReport and enforces SAME_MODEL attribution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class BlindSolveReport:
    solver_role: str
    model_id: str
    is_same_model: bool
    derived_answer: str
    selected_option_ids: list[str]
    steps: list[dict[str, Any]]
    match_reference: bool
    notes: str
    duration_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "solver_role": self.solver_role,
            "model_id": self.model_id,
            "is_same_model": self.is_same_model,
            "derived_answer": self.derived_answer,
            "selected_option_ids": self.selected_option_ids,
            "steps": self.steps,
            "match_reference": self.match_reference,
            "notes": self.notes,
            "duration_ms": self.duration_ms,
        }

def normalize_text(text: str) -> str:
    """Normalize text for answer comparison."""
    if not text:
        return ""
    # Remove leading/trailing whitespaces and common punctuation
    return text.strip().upper().replace(" ", "").replace("，", ",").replace("。", "")

def compare_answers(
    reference_answer: str,
    reference_option_ids: list[str] | None,
    derived_answer: str,
    derived_option_ids: list[str] | None,
    model_id: str,
    duration_ms: int = 0,
    steps: list[dict[str, Any]] | None = None,
) -> BlindSolveReport:
    """Compare author's reference answer with blind solver's derived answer."""
    # Option ID match takes precedence for multiple-choice questions
    match = False
    if reference_option_ids and derived_option_ids:
        match = sorted(reference_option_ids) == sorted(derived_option_ids)
    elif normalize_text(reference_answer) == normalize_text(derived_answer):
        match = True
    elif reference_answer.strip() in derived_answer.strip() or derived_answer.strip() in reference_answer.strip():
        # Soft match
        match = True

    notes = (
        "盲解答案与命题作者参考答案一致。已标注 [SAME_MODEL] 同模型提示。"
        if match
        else "盲解答案与命题作者参考答案存在分歧，需进入待复核 (REVIEW) 流程。"
    )

    return BlindSolveReport(
        solver_role="blind-solver",
        model_id=model_id,
        is_same_model=True,  # Default v1.3/v1.4 uses single-provider DeepSeek
        derived_answer=derived_answer,
        selected_option_ids=derived_option_ids or [],
        steps=steps or [],
        match_reference=match,
        notes=notes,
        duration_ms=duration_ms,
    )
