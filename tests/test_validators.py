import unittest

from services.validators import validate_candidate
from services.hermes_adapter.comparator import compare_answers


class ValidatorTests(unittest.TestCase):
    def candidate(self):
        return {
            "public": {"local_id": "q1", "kind": "single_choice", "prompt": [{"type": "text", "text": "1+1?"}],
                       "options": [{"id": x, "content": [{"type": "text", "text": x}]} for x in ("A", "B")],
                       "score_x100": 200, "material_ids": [], "children": [], "answer_space_lines": 0},
            "private": {"answers": [{"local_question_id": "q1", "answer_kind": "selection", "correct_option_ids": ["B"],
                                    "accepted_answers": [], "solution": [{"type": "text", "text": "2"}],
                                    "rubric": [{"id": "r1", "description": "correct", "score_x100": 200,
                                                "acceptable_variants": []}]}]}}

    def test_review_without_math_proof(self):
        result = validate_candidate(self.candidate(), {"slot_id": "s1", "kind": "single_choice", "score_x100": 200}, {})
        self.assertEqual(result["overall_status"], "REVIEW")
        self.assertEqual([r["status"] for r in result["rule_checks"]], ["PASS", "PASS", "PASS", "PASS", "PASS", "REVIEW", "REVIEW"])
        self.assertEqual(next(r["status"] for r in result["rule_checks"] if r["check_code"] == "ASSET_INTEGRITY"), "PASS")
        self.assertEqual(len(result["content_hash"]), 64)

    def test_bad_answer_and_score_fail(self):
        candidate = self.candidate()
        candidate["private"]["answers"][0]["correct_option_ids"] = ["Z"]
        candidate["private"]["answers"][0]["rubric"][0]["score_x100"] = 100
        result = validate_candidate(candidate, {"kind": "single_choice", "score_x100": 300}, {})
        self.assertEqual(result["overall_status"], "FAIL")

    def test_comparison_no_substring_or_empty_match(self):
        self.assertFalse(compare_answers("12", [], "2", [], "m").match_reference)
        self.assertFalse(compare_answers("", [], "", [], "m").match_reference)

    def test_hash_binds_trusted_context_and_ignores_timestamps(self):
        candidate = self.candidate()
        slot = {"slot_id": "s1", "kind": "single_choice", "score_x100": 200,
                "spec_revision": 3, "plan_revision": 4, "question_revision_id": "rev-1"}
        spec = {"subject": "math", "created_at": "yesterday"}
        first = validate_candidate(candidate, slot, spec, materials={"m1": "text"})
        candidate["revision"] = "MODEL-FORGED"
        self.assertEqual(first["revision"]["question_revision_id"], "rev-1")
        changed_material = validate_candidate(self.candidate(), slot, spec, materials={"m1": "changed"})
        self.assertNotEqual(first["content_hash"], changed_material["content_hash"])
        changed_slot = validate_candidate(self.candidate(), {**slot, "question_revision_id": "rev-2"}, spec, materials={"m1": "text"})
        self.assertNotEqual(first["content_hash"], changed_slot["content_hash"])
        timestamp_only = validate_candidate(self.candidate(), slot, {**spec, "created_at": "today"}, materials={"m1": "text"})
        self.assertEqual(first["content_hash"], timestamp_only["content_hash"])

    def test_blind_evidence_cannot_promote_pass(self):
        report = compare_answers("B", ["B"], "B", ["B"], "deepseek")
        result = validate_candidate(self.candidate(), {"kind": "single_choice", "score_x100": 200}, {}, report)
        self.assertEqual(result["overall_status"], "REVIEW")
        self.assertIn("SAME_MODEL", result["rule_checks"][-1]["evidence_summary"])

    def test_schema_error_does_not_leak_private_answer(self):
        candidate = self.candidate()
        candidate["private"]["answers"][0]["accepted_answers"] = [{"value": "SECRET-ANSWER", "format": "invalid", "conditions": ""}]
        result = validate_candidate(candidate, {"kind": "single_choice", "score_x100": 200}, {})
        self.assertEqual(result["overall_status"], "FAIL")
        self.assertNotIn("SECRET-ANSWER", str(result["rule_checks"]))


if __name__ == "__main__":
    unittest.main()
