"""Blind Solver Runtime with strict isolation guarantees.

Invariant:
- Blind solver NEVER receives reference answers, explanations, or authoring scratchpads.
- Any attempt to pass private fields triggers a hard SecurityIsolationError.
"""
from __future__ import annotations

import copy
import time
from typing import Any
from .schema_validator import validate_public_question
from .comparator import compare_answers, BlindSolveReport

class SecurityIsolationError(RuntimeError):
    """Raised when an attempt is made to leak private answers into the blind solver."""

class BlindSolverRuntime:
    def __init__(self, adapter: Any):
        self.adapter = adapter

    def prepare_blind_input(self, question_public: dict[str, Any]) -> dict[str, Any]:
        """Strip any private fields and validate public question schema."""
        # Hard isolation check: Reject any payload containing private fields
        for forbidden in (
            "private", "answers", "solution", "rubric", "accepted_answers",
            "correct_option_ids", "answer_text", "explanation", "scoring_rubric",
        ):
            if forbidden in question_public:
                raise SecurityIsolationError(f"Security invariant violated: forbidden field '{forbidden}' found in blind-solver input")

        # Deep copy to ensure no shared memory references
        clean_input = copy.deepcopy(question_public)
        validate_public_question(clean_input)
        return clean_input

    def run_blind_solve(
        self,
        question_candidate: dict[str, Any],
        model_id: str = "deepseek-chat",
    ) -> BlindSolveReport:
        """Run independent blind solve and compare against candidate reference answer."""
        public_data = question_candidate.get("public")
        if not public_data:
            raise ValueError("Candidate missing 'public' field")

        # Ensure no answer leakage
        isolated_input = self.prepare_blind_input(public_data)

        # Retrieve reference answer for later comparison
        private_data = question_candidate.get("private", {})
        answers = private_data.get("answers", [])
        ans_obj = answers[0] if answers else {}
        ref_opts = ans_obj.get("correct_option_ids", []) or ans_obj.get("selected_option_ids", [])
        ref_ans = ""
        if ans_obj.get("accepted_answers"):
            ref_ans = ans_obj["accepted_answers"][0].get("value", "")
        elif ans_obj.get("answer_text"):
            ref_ans = ans_obj.get("answer_text", "")

        start_time = time.perf_counter()

        # Call adapter under the solver role
        result = self.adapter.execute_solver_role(
            public_question=isolated_input,
            model_id=model_id,
        )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        derived_ans = result.get("derived_answer", "")
        derived_opts = result.get("selected_option_ids", [])
        steps = result.get("steps", [])

        # Produce comparison report
        return compare_answers(
            reference_answer=ref_ans,
            reference_option_ids=ref_opts,
            derived_answer=derived_ans,
            derived_option_ids=derived_opts,
            model_id=model_id,
            duration_ms=duration_ms,
            steps=steps,
        )
