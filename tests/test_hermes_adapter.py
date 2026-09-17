"""Unit tests for Hermes DeepSeek Adapter and Blind Solver Runtime."""

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

class TestHermesAdapter(unittest.TestCase):

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

    def test_skills_loader(self):
        skills = list_available_skills()
        self.assertIn("question-author", skills)
        self.assertIn("blind-solver", skills)
        self.assertIn("exam-planner", skills)

        author_skill = load_skill("question-author")
        self.assertEqual(author_skill.name, "question-author")
        self.assertTrue(len(author_skill.system_prompt) > 50)

    def test_schema_validator_valid_candidate(self):
        # Should not raise
        validate_candidate(self.sample_valid_candidate)

    def test_schema_validator_invalid_candidate(self):
        invalid_candidate = {
            "public": {"local_id": "q_01"},  # missing required fields
            "private": {"answers": []}
        }
        with self.assertRaises(SchemaValidationError):
            validate_candidate(invalid_candidate)

    def test_blind_runtime_isolation_clean_input(self):
        runtime = BlindSolverRuntime(adapter=None)
        clean = runtime.prepare_blind_input(self.sample_valid_candidate["public"])
        self.assertEqual(clean["local_id"], "q_01")
        self.assertNotIn("private", clean)
        self.assertNotIn("answers", clean)

    def test_blind_runtime_isolation_rejects_leakage(self):
        runtime = BlindSolverRuntime(adapter=None)
        leaked_input = dict(self.sample_valid_candidate["public"])
        leaked_input["answers"] = ["A"]  # Attempted answer injection

        with self.assertRaises(SecurityIsolationError):
            runtime.prepare_blind_input(leaked_input)

    def test_comparator_match(self):
        report = compare_answers(
            reference_answer="A",
            reference_option_ids=["opt_A"],
            derived_answer="A",
            derived_option_ids=["opt_A"],
            model_id="deepseek-chat",
            duration_ms=1200,
            steps=[{"step_number": 1, "description": "计算得出 A"}]
        )
        self.assertTrue(report.match_reference)
        self.assertTrue(report.is_same_model)
        self.assertEqual(report.solver_role, "blind-solver")
        self.assertIn("SAME_MODEL", report.notes)

    def test_comparator_mismatch(self):
        report = compare_answers(
            reference_answer="A",
            reference_option_ids=["opt_A"],
            derived_answer="B",
            derived_option_ids=["opt_B"],
            model_id="deepseek-chat",
        )
        self.assertFalse(report.match_reference)
        self.assertIn("分歧", report.notes)

    def test_adapter_health_and_capabilities(self):
        adapter = HermesDeepSeekAdapter(api_key="test_key")
        health = adapter.health()
        self.assertEqual(health["provider"], "deepseek")
        self.assertTrue(health["api_configured"])

        caps = adapter.capabilities()
        self.assertTrue(caps["structured_json"])
        self.assertIn("deepseek-chat", caps["supported_models"])

    def test_status_map(self):
        from services.hermes_adapter.status_map import map_provider_status
        self.assertEqual(map_provider_status("completed", 200), "SUCCEEDED")
        self.assertEqual(map_provider_status("completed", 200, has_schema_error=True), "FAILED")
        self.assertEqual(map_provider_status("completed", 200, is_cancelled=True), "CANCELLED")
        self.assertEqual(map_provider_status("timed_out", 408), "TIMED_OUT")
        self.assertEqual(map_provider_status("budget_exceeded", 429), "BUDGET_EXCEEDED")
        self.assertEqual(map_provider_status("unknown_state", 200), "UNKNOWN")

    def test_runtime_factory_isolation(self):
        from services.hermes_adapter.runtime_factory import RuntimeFactory
        factory = RuntimeFactory()
        solver_rt = factory.get_runtime_for_role("solver")
        self.assertIsInstance(solver_rt, BlindSolverRuntime)

        author_rt = factory.get_runtime_for_role("author")
        self.assertIsInstance(author_rt, HermesDeepSeekAdapter)

    def test_http_adapter_cancellation(self):
        from services.hermes_adapter.http_adapter import HermesHttpAdapter
        from reference_code.adapter_contract import RunRequest
        adapter = HermesHttpAdapter()
        adapter.cancel("task_to_cancel")

        req = RunRequest(
            task_ref="task_to_cancel",
            provider="deepseek",
            model_id="deepseek-chat",
            role="author",
            input_payload={},
            schema_name="candidate",
            skill_bundle_hash="h1",
            policy_hash="p1",
            max_iterations=1,
            deadline_utc="",
            capability_grant_ref="g1",
        )
        res = adapter.run_stage(req, emit_event=lambda e: None, cancellation_requested=lambda: False)
        self.assertEqual(res.status, "CANCELLED")

if __name__ == "__main__":
    unittest.main()

