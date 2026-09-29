"""Offline safety checks for repair, reviewer routing and version-bound blind inputs."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from reference_code.adapter_contract import RunResult
from services.exam.question_service import QuestionService, GenerationFailure
from services.api.job_run_events import apply_run_event
from services.exam.job_service import GenerationJobService
from tests.test_validators import ValidatorTests


class ReviewWorkflowTests(unittest.TestCase):
    def fixture(self, fail_rounds=1, broken_format=False, unknown=False):
        candidate = ValidatorTests().candidate()
        candidate['public']['kind'] = 'multiple_choice'
        a = candidate['private']['answers'][0]
        a.update(scoring_mode='exclusive', partial_score_x100=0, rubric=[])
        spec = json.loads(Path('examples/exam-spec.json').read_text())
        spec['multiple_choice_partial_score_x100'] = 0
        slot = {'slot_id': 's1', 'kind': 'multiple_choice', 'score_x100': 200,
                'question_revision_id': 'job:s1', 'status': 'AUTHORING'}
        calls, events = [], []
        job = {'job_id': 'job', 'slots': [slot], 'status': 'RUNNING'}
        class Adapter:
            def run_stage(self, request, emit, cancelled):
                calls.append(request)
                if unknown:
                    return RunResult('UNKNOWN', None, (), {}, 'HERMES_ADMISSION_UNKNOWN')
                if request.role == 'reviewer':
                    result = {'question_revision_id': request.input_payload['question_revision_id'],
                              'action': 'no_change', 'issues': [], 'summary': '模型审查意见，仍需教师复核'}
                elif request.role == 'solver':
                    result = {'derived_answer': 'AB', 'selected_option_ids': ['A', 'B'], 'steps': []}
                else:
                    result = copy.deepcopy(candidate)
                    round_no = sum(r.role == 'author' for r in calls)
                    if round_no > fail_rounds:
                        result['private']['answers'][0]['correct_option_ids'] = ['A', 'B']
                    if broken_format and round_no <= fail_rounds:
                        result['private']['answers'][0]['unknown_field'] = 'extra'
                        return RunResult('FAILED', result, (), {}, 'HERMES_OUTPUT_INVALID:additionalProperties')
                return RunResult('SUCCEEDED', result, (), {'total_tokens': 10}, None)
        def record(event):
            events.append(copy.deepcopy(event))
            apply_run_event(job, slot, event)
        return Adapter(), spec, slot, calls, events, record, job

    def run_case(self, **kwargs):
        adapter, spec, slot, calls, events, record, job = self.fixture(**kwargs)
        with patch.object(QuestionService, 'get_adapter', return_value=adapter):
            result = QuestionService.generate_slot_result('q1', spec=spec, slot=slot,
                task_refs={r: f'job:s1:{r}' for r in ('author', 'solver', 'reviewer')}, run_event=record)
        return result, calls, events, job

    def test_single_answer_repaired_revalidated_and_blind_is_public_only(self):
        result, calls, events, job = self.run_case()
        self.assertEqual([c.role for c in calls], ['author', 'reviewer', 'author', 'solver', 'reviewer'])
        self.assertEqual(result['candidate']['private']['answers'][0]['correct_option_ids'], ['A', 'B'])
        self.assertEqual(result['validation']['overall_status'], 'REVIEW')
        self.assertEqual(result['validation']['revision']['question_revision_id'], 'job:s1:repair:1')
        self.assertEqual(set(calls[3].input_payload), {'public_question'})
        self.assertNotIn('private', json.dumps(calls[3].input_payload))
        self.assertEqual(job['slots'][0]['repair_attempt'], 1)
        snapshots = [e['checkpoint'] for e in events if e['event'] == 'candidate_checkpoint']
        self.assertNotEqual(snapshots[0]['validation']['content_hash'], snapshots[-1]['validation']['content_hash'])
        self.assertNotIn('run_refs', GenerationJobService._public(job))
        self.assertNotIn('activity', GenerationJobService._public(job))

    def test_bad_format_reaches_reviewer_without_promoting_it(self):
        result, calls, _, _ = self.run_case(broken_format=True)
        self.assertTrue(calls[1].input_payload['format_error'])
        self.assertNotIn('unknown_field', result['candidate']['private']['answers'][0])
        self.assertEqual(result['validation']['overall_status'], 'REVIEW')

    def test_two_repairs_exhausted_and_review_cannot_waive_deterministic_fail(self):
        result, calls, _, job = self.run_case(fail_rounds=9)
        self.assertEqual(result['validation']['overall_status'], 'FAIL')
        self.assertEqual(job['slots'][0]['repair_attempt'], 2)
        self.assertEqual([c.role for c in calls], ['author', 'reviewer'] * 3)

    def test_unknown_never_retried(self):
        adapter, spec, slot, calls, _, record, _ = self.fixture(unknown=True)
        with patch.object(QuestionService, 'get_adapter', return_value=adapter):
            with self.assertRaises(GenerationFailure) as failure:
                QuestionService.generate_slot_result('q1', spec=spec, slot=slot, run_event=record,
                    task_refs={r: f'job:s1:{r}' for r in ('author', 'solver', 'reviewer')})
        self.assertEqual(failure.exception.status, 'UNKNOWN')
        self.assertEqual(len(calls), 1)

    def test_atomic_quota_rejects_replay_and_unreserved_call(self):
        _, _, slot, _, _, _, job = self.fixture()
        reserve = {'phase': 'author', 'attempt': 1, 'event': 'repair_reserved', 'task_ref': 'job:s1:author:repair:1'}
        with self.assertRaises(ValueError):
            apply_run_event(job, slot, {**reserve, 'event': 'phase_started'})
        apply_run_event(job, slot, reserve)
        with self.assertRaises(ValueError):
            apply_run_event(job, slot, reserve)
        with self.assertRaises(ValueError):
            apply_run_event(job, slot, {**reserve, 'attempt': 3})
