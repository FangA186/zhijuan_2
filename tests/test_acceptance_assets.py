"""Tests for the written acceptance assets; NOT live acceptance or E2E tests."""
import unittest
from verify_acceptance_assets import ROOT, load, validate_assets

class AcceptanceAssetsTests(unittest.TestCase):
    def test_inventory_and_cross_references(self):
        self.assertEqual(validate_assets()["case_definitions"], 47)
    def test_minimum_gate_case_count(self):
        x=load("acceptance/minimum-cases.yaml")
        self.assertEqual(x["gate"],"G-MIN")
        self.assertEqual(len(x["cases"]),19)
    def test_full_gate_case_count(self):
        x=load("acceptance/full-cases.yaml")
        self.assertEqual(x["gate"],"G-FULL")
        self.assertEqual(len(x["cases"]),28)
    def test_execution_results_are_blank(self):
        for name in ("minimum","full"):
            for c in load(f"acceptance/{name}-cases.yaml")["cases"]:
                self.assertIsNone(c["executed_at"])
                self.assertIsNone(c["actual_result"])
                self.assertEqual(c["status"],"NOT_RUN")
    def test_phases_have_explicit_dependencies(self):
        phases=load("acceptance/mvp-plan.yaml")["phases"]
        self.assertEqual([p["depends_on"] for p in phases],[[],["M0"],["M1"],["M2"]])
    def test_fixture_scope_requires_teacher_confirmation(self):
        for s in ("primary","junior","senior"):
            self.assertFalse(load(f"acceptance/fixtures/minimum-{s}.json")["taught_scope"]["scope_confirmed"])
    def test_fixtures_are_twenty_points_and_five_items(self):
        for s in ("primary","junior","senior"):
            x=load(f"acceptance/fixtures/minimum-{s}.json")
            self.assertEqual(sum(t["count"] for t in x["sections"]),5)
            self.assertEqual(sum(t["count"]*t["score_each_x100"] for t in x["sections"]),2000)
    def test_no_application_or_hermes_delivery_claim(self):
        x=load("acceptance/current-delivery-status.json")
        for k in ("application_runnable","hermes_source_included","hermes_installed","live_deepseek_called"):
            self.assertFalse(x[k])
    def test_capability_template_has_no_ready_claims(self):
        x=load("acceptance/capability-matrix.template.yaml")
        self.assertFalse(x["approved_before_run"])
        for c in x["capabilities"]:
            self.assertEqual(c["acceptance_status"],"NOT_RUN")
            for k in ("generation","verification","rendering"):
                self.assertNotEqual(c[k],"READY")
    def test_evidence_template_is_not_a_run(self):
        x=load("acceptance/evidence-manifest.template.json")
        self.assertTrue(x["template_only"])
        self.assertIsNone(x["run_id"])
        self.assertFalse(x["artifacts"])
        self.assertFalse(x["signoffs"])
    def test_minimum_positive_and_sensitive_cases_repeat_all_stages(self):
        for c in load("acceptance/minimum-cases.yaml")["cases"]:
            if not c["id"].startswith("MIN-N") or c["id"] in ("MIN-N05","MIN-N07"):
                self.assertEqual(c["repeat_rule"],"each_stage")
    def test_hermes_deepseek_no_question_bank_scope(self):
        x=load("acceptance/mvp-plan.yaml")["scope"]
        self.assertEqual(x["provider"],"deepseek")
        self.assertEqual(x["agent_framework"],"hermes")
        for k in ("question_bank","langchain","langgraph","history_retrieval"):
            self.assertFalse(x[k])

if __name__=="__main__":
    unittest.main()
