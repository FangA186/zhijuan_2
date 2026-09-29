"""Native event forwarding happens before terminal output, with run identity fencing."""
import json
import threading
import unittest
from dataclasses import replace
import httpx
from services.hermes_adapter.http_adapter import HermesHttpAdapter
from tests.test_hermes_runs_transport import request


class StreamTransportTests(unittest.TestCase):
    def test_stream_before_completion_and_final_error_detail(self):
        emitted, first = [], threading.Event()
        class Body(httpx.SyncByteStream):
            def __iter__(self):
                for data in ({'event': 'message.delta', 'delta': '{"answer":'},
                             {'event': 'reasoning.available', 'text': 'PRIVATE'}):
                    yield b'data: ' + json.dumps(dict(data, run_id='run_test')).encode() + b'\n\n'
                first.set()
        polls = []
        def handler(req):
            if req.method == 'POST':
                return httpx.Response(202, json={'run_id': 'run_test'})
            if req.url.path.endswith('/events'):
                return httpx.Response(200, headers={'content-type': 'text/event-stream'}, stream=Body())
            polls.append(1)
            if len(polls) < 2:
                first.wait(1)
                return httpx.Response(200, json={'run_id': 'run_test', 'status': 'running'})
            return httpx.Response(200, json={'run_id': 'run_test', 'status': 'failed', 'completed': False,
                                            'error': 'provider rejected: HTTP 400'})
        adapter = HermesHttpAdapter('http://test', 'secret', httpx.Client(transport=httpx.MockTransport(handler)), .01)
        result = adapter.run_stage(replace(request(), capability_grant_ref='isolated-local-generation'), emitted.append)
        data = [e['data'] for e in emitted if e['event'] == 'activity']
        self.assertEqual(data[0]['event'], 'message.delta')
        self.assertEqual(data[-1]['event'], 'run.result')
        self.assertIn('HTTP 400', data[-1]['error'])
        self.assertNotIn('PRIVATE', str(emitted))
        self.assertEqual(result.error_code, 'HERMES_FAILED')

    def test_solver_gateway_allows_only_authenticated_events(self):
        from services.hermes_adapter.isolation_gateway import Handler, RUN_PATH
        from unittest.mock import patch
        self.assertTrue(RUN_PATH.fullmatch('/v1/runs/run_x/events'))
        self.assertFalse(RUN_PATH.fullmatch('/v1/runs/run_x/events/extra'))
        with patch.dict('os.environ', {'HERMES_SOLVER_API_KEY': 'key'}), patch.object(Handler, 'send_error') as error:
            handler = Handler.__new__(Handler)
            handler.path, handler.headers = '/v1/runs/run_x/events', {}
            handler._forward('GET')
            error.assert_called_once_with(401)

    def test_explicit_unknown_upstream_must_reconcile(self):
        from services.hermes_adapter.run_stream import terminal_failure
        result = terminal_failure({'error': 'HTTP 502: upstream_result_unknown'}, {})
        self.assertEqual(result.status, 'UNKNOWN')
        self.assertEqual(result.error_code, 'HERMES_PROVIDER_RECONCILE')

    def test_queued_deltas_batch_without_losing_text_or_event_order(self):
        from services.hermes_adapter.run_stream import RunStream
        events = []
        stream = RunStream(None, request(), events.append)
        for data in ({'event':'message.delta','delta':'a'}, {'event':'message.delta','delta':'b'},
                     {'event':'tool.started','tool':'verify'}, {'event':'message.delta','delta':'c'}):
            stream.events.put(data)
        stream.drain()
        self.assertEqual([e['data'] for e in events], [
            {'event':'message.delta','delta':'ab'}, {'event':'tool.started','tool':'verify'},
            {'event':'message.delta','delta':'c'}])
