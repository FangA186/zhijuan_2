import json
import unittest
from unittest.mock import patch

import httpx

from services.hermes_adapter.adapter import HermesDeepSeekAdapter
from services.hermes_adapter.blind_runtime import BlindSolverRuntime, SecurityIsolationError
from services.hermes_adapter.http_adapter import HermesHttpAdapter
from services.hermes_adapter.isolation_gateway import validate_solver_run


class BlindIsolationTests(unittest.TestCase):
    def test_nested_private_field_rejected(self):
        runtime = BlindSolverRuntime(adapter=None)
        with self.assertRaises(SecurityIsolationError):
            runtime.prepare_blind_input({"prompt": [{"text": "x", "private": {"answer": "canary"}}]})

    def test_solver_gateway_refuses_author_context_and_session_reuse(self):
        question = {"local_id": "q1", "kind": "solution", "prompt": [{"type": "text", "text": "x"}],
                    "options": [], "score_x100": 100, "material_ids": [], "children": [],
                    "answer_space_lines": 1}
        seen = []
        def respond(request):
            if request.method == "POST":
                seen.append(request)
                return httpx.Response(202, json={"run_id": "run_blindtest"})
            return httpx.Response(200, json={"run_id": "run_blindtest", "status": "completed", "completed": True,
                                             "output": json.dumps({"derived_answer": "x"})})
        transport = HermesHttpAdapter("http://author.invalid", "author-key",
                                      httpx.Client(transport=httpx.MockTransport(respond)), 0)
        adapter = HermesDeepSeekAdapter(transport=transport)
        adapter._solver_transport = HermesHttpAdapter("http://solver.invalid", "solver-key",
                                                      httpx.Client(transport=httpx.MockTransport(respond)), 0)
        self.assertEqual(adapter.execute_solver_role(question)["derived_answer"], "x")
        body = json.loads(seen[0].content)
        with patch.dict("os.environ", {"HERMES_SOLVER_MODEL_ID": "deepseek-chat"}):
            self.assertEqual(validate_solver_run(body), question)
            for added in ({"session_id": "author-session"}, {"previous_response_id": "author-run"}):
                with self.assertRaises(ValueError):
                    validate_solver_run({**body, **added})
            context = json.loads(body["input"])
            context["public_question"]["prompt"][0]["answers"] = ["canary"]
            with self.assertRaises(ValueError):
                validate_solver_run({**body, "input": json.dumps(context)})
            context["public_question"]["prompt"][0].pop("answers")
            context["public_question"]["author_note"] = "canary"
            with self.assertRaises(ValueError):
                validate_solver_run({**body, "input": json.dumps(context)})


if __name__ == "__main__":
    unittest.main()
