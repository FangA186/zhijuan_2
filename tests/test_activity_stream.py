"""Native SSE filtering, durable replay and incremental strict-provider output."""
import json
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from services.api.main import app
from services.api.job_run_events import append_activity
from services.api.routes.exam_activity_routes import activity_snapshot
from services.exam.job_service import GenerationJobService
from services.hermes_adapter.run_stream import public_event
from tools.deepseek_json_contract import prepare_strict_request, FUNCTION_NAME
from tools.live_budget_stream import output_chunks


class ActivityTests(unittest.TestCase):
    def test_provider_arguments_stream_before_finish_and_hide_reasoning(self):
        def lines():
            for delta, finish in [({'tool_calls': [{'index': 0, 'function': {'name': FUNCTION_NAME, 'arguments': '{"x":'}}]}, None),
                                  ({'reasoning_content': 'PRIVATE', 'tool_calls': [{'index': 0, 'function': {'arguments': '1}'}}]}, None),
                                  ({}, 'tool_calls')]:
                yield 'data: ' + json.dumps({'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]})
            yield 'data: [DONE]'
        stream = output_chunks(lines())
        self.assertEqual(next(stream)['choices'][0]['delta']['content'], '{"x":')
        rest = list(stream)
        self.assertNotIn('PRIVATE', str(rest))
        self.assertEqual(rest[-1]['choices'][0]['finish_reason'], 'stop')
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            list(output_chunks(['data: [DONE]']))

    def test_reviewer_has_own_strict_schema(self):
        prepared = prepare_strict_request({'messages': [{'content': 'Role: reviewer.'}]})
        props = prepared['tools'][0]['function']['parameters']['properties']
        self.assertIn('action', props)
        self.assertNotIn('derived_answer', props)

    def test_native_event_allowlist_and_no_private_progress(self):
        self.assertIsNone(public_event({'event': 'reasoning.available', 'text': 'PRIVATE'}))
        result = public_event({'event': 'tool.started', 'tool': 'validate', 'preview': 'SECRET', 'args': {'key': 'SECRET'}})
        self.assertEqual(result, {'event': 'tool.started', 'tool': 'validate'})
        job = {'job_id': 'j', 'version': 4, 'status': 'COMPLETED', 'logs': []}
        for delta in ('first ', 'second'):
            append_activity(job, 's1', 'author', 0, {'event': 'message.delta', 'delta': delta})
        self.assertEqual(len(job['activity']), 1)
        self.assertEqual(job['activity'][0]['message'], 'first second')
        with patch.object(GenerationJobService, 'get_current_job', return_value=GenerationJobService._public(job)), \
             patch.object(GenerationJobService, 'repository') as repo:
            repo.return_value.get.return_value = job
            self.assertEqual(activity_snapshot()['logs'][0]['message'], 'first second')
            response = TestClient(app).get('/v1/exams/current/generation-jobs/activity/stream')
            self.assertIn('first second', response.text)
            self.assertIn('event: completed', response.text)
        self.assertNotIn('first second', str(GenerationJobService._public(job)))

    def test_remote_activity_forbidden(self):
        response = TestClient(app, client=('203.0.113.4', 123)).get('/v1/exams/current/generation-jobs/activity')
        self.assertEqual(response.status_code, 403)

    def test_legacy_results_are_labelled_saved_not_streamed(self):
        job = {'job_id': 'j', 'version': 1, 'status': 'PARTIAL_FAILED', 'logs': []}
        with patch.object(GenerationJobService, 'get_current_job', return_value=job.copy()), \
             patch.object(GenerationJobService, 'repository') as repo:
            repo.return_value.get.return_value = job
            repo.return_value.results.return_value = [{'slot_id': 'slot_001', 'candidate': {'public': {'prompt': []}}}]
            response = activity_snapshot()
        self.assertFalse(response['activity_available'])
        self.assertEqual(response['logs'][1]['kind'], 'saved.result')
        self.assertEqual(response['logs'][1]['data']['source'], 'generation_job_results')
