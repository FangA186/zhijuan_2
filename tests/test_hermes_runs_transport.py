"""Offline contract checks against the pinned Hermes /v1/runs wire shape."""
import json
import unittest

import httpx

from reference_code.adapter_contract import RunRequest
from services.hermes_adapter.http_adapter import HermesHttpAdapter


def request(role="solver"):
    return RunRequest("t1", "deepseek", "deepseek-chat", role, {"public_question": {"prompt": []}},
                      "blind_solver", "h", "p", 1, "", "g")


class RunsTransportTests(unittest.TestCase):
    def adapter(self, terminal):
        seen = []

        def handler(req):
            seen.append(req)
            if req.method == "POST" and req.url.path == "/v1/runs":
                return httpx.Response(202, json={"run_id": "run_test", "status": "started"})
            if req.method == "GET":
                return httpx.Response(200, json=terminal)
            return httpx.Response(200, json={"status": "stopping"})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        return HermesHttpAdapter("http://hermes.local", "gateway-key", client, 0), seen

    def test_completed_requires_output_and_keeps_usage_unknown(self):
        adapter, seen = self.adapter({"run_id": "run_test", "status": "completed", "completed": True,
                                      "output": json.dumps({"derived_answer": "A"}), "usage": {}})
        result = adapter.run_stage(request())
        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(result.provider_request_ids, ())
        self.assertEqual(result.usage, {})
        self.assertEqual(seen[0].url.path, "/v1/runs")
        self.assertEqual(seen[1].url.path, "/v1/runs/run_test")
        self.assertTrue(seen[0].headers.get("Idempotency-Key"))

    def test_partial_cannot_pass(self):
        adapter, _ = self.adapter({"run_id": "run_test", "status": "failed", "completed": False, "partial": True,
                                   "output": "{\"derived_answer\": \"A\"}"})
        result = adapter.run_stage(request())
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.error_code, "HERMES_PARTIAL")

    def test_author_output_needs_candidate_schema(self):
        adapter, _ = self.adapter({"run_id": "run_test", "status": "completed", "completed": True, "output": "{}"})
        result = adapter.run_stage(request("author"))
        self.assertEqual(result.status, "FAILED")
        self.assertTrue(result.error_code.startswith("HERMES_OUTPUT_INVALID"))

    def test_missing_completion_flag_stays_unknown(self):
        adapter, _ = self.adapter({"run_id": "run_test", "status": "completed", "output": "{}"})
        self.assertEqual(adapter.run_stage(request()).status, "UNKNOWN")

    def test_admission_timeout_stays_unknown(self):
        def handler(req):
            raise httpx.ReadTimeout("lost response")
        client = httpx.Client(transport=httpx.MockTransport(handler))
        adapter = HermesHttpAdapter("http://hermes.local", "gateway-key", client)
        result = adapter.run_stage(request())
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.provider_request_ids, ())

    def test_admission_server_error_stays_unknown(self):
        client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(503)))
        adapter = HermesHttpAdapter("http://hermes.local", "gateway-key", client)
        self.assertEqual(adapter.run_stage(request()).status, "UNKNOWN")

    def test_cancel_calls_native_stop(self):
        adapter, seen = self.adapter({"status": "running"})
        adapter._run_ids["t1"] = "run_test"
        adapter.cancel("t1")
        self.assertEqual(seen[0].url.path, "/v1/runs/run_test/stop")
        self.assertEqual(adapter.run_stage(request()).status, "CANCELLED")

    def test_status_timeout_polls_original_run_without_another_admission(self):
        seen=[]
        def handler(req):
            seen.append(req)
            if req.method=='POST':return httpx.Response(202,json={'run_id':'run_once'})
            if len(seen)==2:raise httpx.ReadTimeout('read interrupted')
            return httpx.Response(200,json={'run_id':'run_once','status':'completed','completed':True,'output':'{"derived_answer":"A"}'})
        adapter=HermesHttpAdapter('http://hermes.local','gateway-key',httpx.Client(transport=httpx.MockTransport(handler)),0)
        self.assertEqual(adapter.run_stage(request()).status,'SUCCEEDED')
        self.assertEqual(sum(r.method=='POST' for r in seen),1)
        self.assertTrue(all(r.url.path=='/v1/runs/run_once' for r in seen[1:]))

    def test_expired_deadline_cannot_admit_a_paid_run(self):
        from dataclasses import replace
        adapter,seen=self.adapter({})
        expired=replace(request(),deadline_utc='2000-01-01T00:00:00+00:00')
        self.assertEqual(adapter.run_stage(expired).status,'TIMED_OUT')
        self.assertEqual(seen,[])

    def test_mismatched_or_missing_status_run_id_cannot_succeed(self):
        for status_run_id in ("run_other", None):
            terminal = {"status": "completed", "completed": True, "output": '{"derived_answer":"A"}'}
            if status_run_id is not None:
                terminal["run_id"] = status_run_id
            adapter, _ = self.adapter(terminal)
            self.assertEqual(adapter.run_stage(request()).status, "UNKNOWN")

    def test_admission_event_failure_stops_without_readmission(self):
        adapter, seen = self.adapter({"run_id": "run_test", "status": "running"})
        result = adapter.run_stage(
            request(),
            emit_event=lambda _: (_ for _ in ()).throw(RuntimeError("database fence rejected")),
        )
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual([(r.method, r.url.path) for r in seen],
                         [("POST", "/v1/runs"), ("POST", "/v1/runs/run_test/stop")])

    def test_cancel_during_terminal_poll_cannot_succeed(self):
        cancelled = {"value": False}
        seen = []
        def handler(req):
            seen.append(req)
            if req.url.path == "/v1/runs":
                return httpx.Response(202, json={"run_id": "run_test"})
            if req.method == "GET":
                cancelled["value"] = True
                return httpx.Response(200, json={"run_id": "run_test", "status": "completed",
                                                  "completed": True, "output": '{"derived_answer":"A"}'})
            return httpx.Response(200, json={"run_id": "run_test", "status": "stopping"})
        adapter = HermesHttpAdapter("http://hermes.local", "gateway-key",
                                    httpx.Client(transport=httpx.MockTransport(handler)), 0)
        result = adapter.run_stage(request(), cancellation_requested=lambda: cancelled["value"])
        self.assertNotEqual(result.status, "SUCCEEDED")
        self.assertTrue(any(r.url.path.endswith("/stop") for r in seen))

    def test_cancel_during_completion_event_cannot_succeed(self):
        cancelled = {"value": False}
        adapter, seen = self.adapter({"run_id": "run_test", "status": "completed",
                                      "completed": True, "output": '{"derived_answer":"A"}'})
        def emit(event):
            if event["event"] == "hermes_run_completed":
                cancelled["value"] = True
        result = adapter.run_stage(request(), emit_event=emit,
                                   cancellation_requested=lambda: cancelled["value"])
        self.assertNotEqual(result.status, "SUCCEEDED")
        self.assertTrue(any(r.url.path.endswith("/stop") for r in seen))

    def test_cancel_check_failure_before_admission_never_posts(self):
        adapter, seen = self.adapter({})
        result = adapter.run_stage(
            request(), cancellation_requested=lambda: (_ for _ in ()).throw(RuntimeError("db unavailable")))
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(seen, [])

    def test_cancel_check_failure_after_admission_stops(self):
        checked = {"count": 0}
        adapter, seen = self.adapter({"run_id": "run_test", "status": "running"})
        def check():
            checked["count"] += 1
            if checked["count"] > 1:
                raise RuntimeError("db unavailable")
            return False
        result = adapter.run_stage(request(), cancellation_requested=check)
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.error_code, "HERMES_CANCEL_CHECK_UNKNOWN")
        self.assertEqual([(r.method, r.url.path) for r in seen],
                         [("POST", "/v1/runs"), ("POST", "/v1/runs/run_test/stop")])

    def test_gateway_interruption_requires_reconciliation_not_slot_failure(self):
        adapter, seen = self.adapter({"run_id": "run_test", "status": "interrupted",
                                      "completed": False, "usage": {"total_tokens": 12}})
        result = adapter.run_stage(request())
        self.assertEqual(result.status, "UNKNOWN")
        self.assertEqual(result.error_code, "HERMES_INTERRUPTED_RECONCILE")
        self.assertEqual(result.usage["total_tokens"], 12)
        self.assertEqual(sum(r.method == "POST" for r in seen), 1)
