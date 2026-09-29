"""Hermes adapter contract checks, part 2."""
from tests.hermes_adapter_fixture import *

class HermesAdapterCases2(HermesAdapterFixture, unittest.TestCase):
    def test_solver_gateway_internal_readiness_requires_auth(self):
        # The narrow internal readiness route must not weaken the gateway boundary:
        # unauthenticated GET /internal/readiness is refused and nothing is forwarded.
        from unittest.mock import patch
        from services.hermes_adapter.isolation_gateway import Handler
        with patch.object(Handler, "send_error") as send_error, \
             patch.dict("os.environ", {"HERMES_SOLVER_API_KEY": "k", "HERMES_SOLVER_UPSTREAM_KEY": "u"},
                        clear=False):
            handler = Handler.__new__(Handler)
            handler.path = "/internal/readiness"
            handler.headers = {"Authorization": "Bearer wrong"}
            handler.send_error = send_error
            handler._forward("GET")
            send_error.assert_called_once_with(401)


    def test_gateway_runs_reject_private_fields_recursively(self):
        from unittest.mock import patch
        from services.hermes_adapter.isolation_gateway import validate_solver_run
        body = self._solver_body()
        content = json.loads(body["input"])
        content["public_question"]["children"] = [{
            "local_id": "c1", "kind": "short_answer", "prompt": [{"type": "text", "text": "y"}],
            "options": [], "score_x100": 50, "material_ids": [], "children": [], "answer_space_lines": 1}]
        content["public_question"]["children"][0]["rubric"] = [{"id": "r1"}]
        with patch.dict("os.environ", {"HERMES_SOLVER_MODEL_ID": "deepseek-chat"}):
            with self.assertRaises(ValueError):
                validate_solver_run({**body, "input": json.dumps(content)})


    def test_author_output_must_be_contract_json_and_fail_without_patch(self):
        from services.exam.question_service import GenerationFailure, QuestionService
        from unittest.mock import Mock, patch
        from reference_code.adapter_contract import RunResult
        import copy, json as _json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        candidate = _json.loads((root / "examples/candidate.json").read_text())
        spec = _json.loads((root / "examples/exam-spec.json").read_text())
        bad = copy.deepcopy(candidate)
        bad["private"]["answers"][0]["rubric"] = []
        adapter = Mock()
        adapter.run_stage.side_effect = lambda req, *args: RunResult("SUCCEEDED", bad if req.role == 'author' else {
            'question_revision_id': req.input_payload['question_revision_id'], 'action': 'repair',
            'issues': ['评分不完整'], 'summary': '修订评分'}, (), {}, None)
        slot = {"slot_id": "s1", "kind": candidate["public"]["kind"],
                "score_x100": candidate["public"]["score_x100"],
                "spec_revision": 1, "plan_revision": 1, "question_revision_id": "qrev-1"}
        with patch.object(QuestionService, "get_adapter", return_value=adapter):
            with self.assertRaisesRegex(GenerationFailure, 'REPAIR_EXHAUSTED'):
                QuestionService.generate_slot_result(candidate["public"]["local_id"], spec=spec, slot=slot)
        self.assertEqual(adapter.run_stage.call_count, 6)
        self.assertNotIn('solver', [call.args[0].role for call in adapter.run_stage.call_args_list])


    def test_author_missing_payload_failed_output_cannot_succeed(self):
        # A completed status without a contract payload, or output the schema
        # rejects, must surface as FAILED, never as a synthetic success.
        from services.hermes_adapter.http_adapter import HermesHttpAdapter
        from reference_code.adapter_contract import RunRequest
        import httpx as _httpx
        cases = [("{}", "HERMES_OUTPUT_INVALID"),
                 (json.dumps({"random": True}), "HERMES_OUTPUT_INVALID")]
        # "random" is an empty candidate object missing required fields -> invalid.
        for output, expected_prefix in cases:
            def handler(req, _output=output):
                if req.url.path == "/v1/runs":
                    return _httpx.Response(202, json={"run_id": "run_x"})
                return _httpx.Response(200, json={"run_id": "run_x", "status": "completed",
                                                  "completed": True, "output": _output})
            adapter = HermesHttpAdapter("http://hermes.local", "key",
                                        _httpx.Client(transport=_httpx.MockTransport(handler)), 0)
            req = RunRequest("t-author", "deepseek", "deepseek-chat", "author",
                             {}, "candidate", "h", "p", 1, "", "g")
            result = adapter.run_stage(req)
            self.assertEqual(result.status, "FAILED")
            self.assertTrue(result.error_code.startswith(expected_prefix),
                            f"unexpected error_code {result.error_code} for {output}")


    def test_material_slots_rejected_before_model_admission(self):
        from services.exam.question_service import GenerationFailure, QuestionService
        from unittest.mock import Mock, patch
        import json as _json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        spec = _json.loads((root / "examples/exam-spec.json").read_text())
        for slot in ({"kind": "material_group", "score_x100": 0},
                     {"kind": "solution", "score_x100": 100, "material_id": "mat-1"}):
            with self.subTest(slot=slot), patch.object(QuestionService, "get_adapter") as adapter:
                with self.assertRaises(GenerationFailure):
                    QuestionService.generate_slot_result("q1", spec=spec, slot=slot)
                adapter.assert_not_called()


    def test_spec_provided_materials_rejected_before_model_admission(self):
        from services.exam.question_service import GenerationFailure, QuestionService
        from unittest.mock import Mock, patch
        import json as _json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        spec = _json.loads((root / "examples/exam-spec.json").read_text())
        spec["provided_materials"] = [{"id": "m1", "title": "材料", "text": "正文",
                                       "source_note": "", "rights_confirmed": True}]
        with patch.object(QuestionService, "get_adapter") as adapter:
            with self.assertRaises(GenerationFailure):
                QuestionService.generate_slot_result("q1", spec=spec,
                                                     slot={"kind": "solution", "score_x100": 100})
            adapter.assert_not_called()


    def test_math_truth_stays_review_without_trusted_proof(self):
        # A matching blind answer must never promote MATH_TRUTH past REVIEW.
        import json as _json
        from pathlib import Path
        from services.exam.question_service import QuestionService
        from unittest.mock import Mock, patch
        from reference_code.adapter_contract import RunResult
        root = Path(__file__).resolve().parents[1]
        candidate = _json.loads((root / "examples/candidate.json").read_text())
        spec = _json.loads((root / "examples/exam-spec.json").read_text())
        adapter = Mock()
        adapter.run_stage.side_effect = [
            RunResult("SUCCEEDED", candidate, (), {}, None),
            RunResult("SUCCEEDED", {"derived_answer": "2", "selected_option_ids": [],
                                    "steps": [{"text": "verified"}]}, (), {}, None),
            RunResult("SUCCEEDED", {"question_revision_id": "qrev-1", "action": "no_change", "issues": [], "summary": "需教师复核"}, (), {}, None),
        ]
        slot = {"slot_id": "s1", "kind": candidate["public"]["kind"],
                "score_x100": candidate["public"]["score_x100"],
                "spec_revision": 1, "plan_revision": 1, "question_revision_id": "qrev-1"}
        with patch.object(QuestionService, "get_adapter", return_value=adapter):
            result = QuestionService.generate_slot_result(candidate["public"]["local_id"], spec=spec, slot=slot)
        self.assertEqual(result["validation"]["overall_status"], "REVIEW")
        math_truth = next(c for c in result["validation"]["rule_checks"] if c["check_code"] == "MATH_TRUTH")
        self.assertEqual(math_truth["status"], "REVIEW")


