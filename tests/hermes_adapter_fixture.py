"""Unit tests for Hermes DeepSeek Adapter and Blind Solver Runtime."""

import json
import unittest
from pathlib import Path
from services.hermes_adapter.skills_loader import load_skill, list_available_skills
from services.hermes_adapter.schema_validator import (
    validate_candidate,
    validate_public_question,
    SchemaValidationError,
)
from services.hermes_adapter.comparator import compare_answers
from services.hermes_adapter.blind_runtime import BlindSolverRuntime, SecurityIsolationError
from services.hermes_adapter.adapter import HermesDeepSeekAdapter


class HermesAdapterFixture:
    def setUp(self):
        self.sample_valid_candidate = {
            "public": {
                "local_id": "q_01",
                "kind": "single_choice",
                "prompt": [{"type": "text", "text": "方程 $x^2-4x+k=0$ 有两不等实根，求k范围："}],
                "options": [
                    {"id": "opt_A", "content": [{"type": "text", "text": "$k < 4$"}]},
                    {"id": "opt_B", "content": [{"type": "text", "text": "$k > 4$"}]}
                ],
                "score_x100": 400,
                "material_ids": [],
                "children": [],
                "answer_space_lines": 2
            },
            "private": {
                "answers": [
                    {
                        "local_question_id": "q_01",
                        "answer_kind": "selection",
                        "correct_option_ids": ["opt_A"],
                        "accepted_answers": [
                            {
                                "value": "A",
                                "format": "text",
                                "conditions": "唯一正确选项"
                            }
                        ],
                        "solution": [
                            {
                                "type": "text",
                                "text": "判别式 16 - 4k > 0 得到 k < 4，故选 A。"
                            }
                        ],
                        "rubric": [
                            {
                                "id": "rub_01",
                                "description": "列出判别式并求得选项 A",
                                "score_x100": 400,
                                "acceptable_variants": []
                            }
                        ]
                    }
                ]
            }
        }


    def _solver_body(self, **overrides):
        question = {"local_id": "q1", "kind": "solution", "prompt": [{"type": "text", "text": "x"}],
                    "options": [], "score_x100": 100, "material_ids": [], "children": [],
                    "answer_space_lines": 1}
        body = {"provider": "deepseek", "model": "deepseek-chat",
                "instructions": "Role: solver. Return one JSON object.", "input": json.dumps(
                    {"public_question": question}, ensure_ascii=False)}
        body.update(overrides)
        return body



__all__ = [name for name in globals() if not name.startswith("__")]
