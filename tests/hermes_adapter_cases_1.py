"""Hermes adapter contract checks, part 1."""
from tests.hermes_adapter_fixture import *

class HermesAdapterCases1(HermesAdapterFixture, unittest.TestCase):
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
        from unittest.mock import patch
        with patch.dict("os.environ", {"HERMES_API_KEY": "", "HERMES_API_BASE_URL": ""}):
            adapter = HermesDeepSeekAdapter(api_key="test_key")
            health = adapter.health()
        self.assertEqual(health["provider"], "deepseek")
        self.assertFalse(health["api_configured"])

        caps = adapter.capabilities()
        self.assertTrue(caps["native_runs"])
        self.assertFalse(caps["tested_tool_isolation"])


    def test_solver_requires_distinct_gateway(self):
        from reference_code.adapter_contract import RunRequest
        from unittest.mock import patch
        with patch.dict("os.environ", {"HERMES_API_BASE_URL": "http://same", "HERMES_API_KEY": "test",
                                    "HERMES_SOLVER_API_BASE_URL": "http://same", "HERMES_SOLVER_API_KEY": "test"}):
            adapter = HermesDeepSeekAdapter()
        req = RunRequest("solver-task", "deepseek", "deepseek-chat", "solver",
                         {"public_question": self.sample_valid_candidate["public"]},
                         "blind_solver", "h", "p", 1, "", "g")
        self.assertEqual(adapter.run_stage(req).error_code, "HERMES_SOLVER_ISOLATION_NOT_CONFIGURED")


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


    def test_solver_gateway_rejects_other_providers_models_and_widgets(self):
        from unittest.mock import patch
        from services.hermes_adapter.isolation_gateway import validate_solver_run
        for extra in ({"provider": "anthropic"}, {"model": "gpt-4o"}, {"tools": [{"name": "bash"}]},
                      {"session_id": "foreign-session"}, {"conversation_history": []},
                      {"idempotency_key": "leaked-author-run"}):
            with self.subTest(extra=extra), patch.dict("os.environ", {"HERMES_SOLVER_MODEL_ID": "deepseek-chat"}):
                with self.assertRaises(ValueError):
                    validate_solver_run(self._solver_body(**extra))


    def test_solver_gateway_rejects_unlisted_paths(self):
        from unittest.mock import patch
        from services.hermes_adapter.isolation_gateway import Handler
        paths = ["/v1/runs/run_x/tools", "/v1/runs/run_x/events/extra", "/sessions", "/", "/health",
                 "/internal/budget", "/v1/models"]
        with patch.object(Handler, "send_error") as send_error, \
             patch.dict("os.environ", {"HERMES_SOLVER_API_KEY": "k", "HERMES_SOLVER_UPSTREAM_KEY": "u",
                                       "HERMES_SOLVER_MODEL_ID": "deepseek-chat"}, clear=True):
            for path in paths:
                handler = Handler.__new__(Handler)
                handler.path = path
                handler.headers = {"Authorization": "Bearer k"}
                handler.send_error = send_error
                handler._forward("GET")
            self.assertEqual(send_error.call_count, len(paths))

