"""Offline failure attribution and no raw-output persistence."""
import unittest
from services.worker.failures import record_failure
from services.exam.question_service import GenerationFailure


class SlotFailureDiagnosticsTests(unittest.TestCase):
    def test_bound_schema_error_and_unknown_text(self):
        class Repo:
            def __init__(self):
                self.job = {'job_id': 'job', 'status': 'RUNNING', 'version': 1,
                            'slots': [{'slot_id': 'one', 'status': 'AUTHORING'}], 'logs': []}
            def get(self, exam):
                return self.job
            def replace(self, job, version):
                self.job = job
        repo = Repo()
        error = GenerationFailure('FAILED', 'HERMES_OUTPUT_INVALID:required:properties/public/required')
        error.phase = 'author'
        self.assertTrue(record_failure(repo, 'exam', 'job', 'one', error))
        self.assertEqual(repo.job['slots'][0]['failure']['phase'], 'author')
        self.assertEqual(repo.job['logs'][0]['slot_id'], 'one')
        self.assertEqual(repo.job['completed_slots'], 1)
        self.assertEqual(repo.job['slots'][0]['status'], 'FAIL')
        repo = Repo()
        short = GenerationFailure('FAILED', 'Blind output must contain only short verifiable steps')
        self.assertTrue(record_failure(repo, 'exam', 'job', 'one', short))
        self.assertEqual(repo.job['slots'][0]['failure']['code'], 'BLIND_STEPS_INVALID')
        self.assertEqual(repo.job['slots'][0]['failure']['phase'], 'solver')
        repo = Repo()
        self.assertFalse(record_failure(repo, 'exam', 'job', 'one', RuntimeError('secret private output')))
        self.assertNotIn('secret', str(repo.job))
        self.assertEqual(repo.job['status'], 'RECONCILING')
        repo.job['status'] = 'CANCELLED'
        self.assertFalse(record_failure(repo, 'exam', 'job', 'one', error))
