"""Missing runtime configuration must neither claim readiness nor enqueue work."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from services.api.health import generation_configuration, readiness
from services.api.main import app


class GenerationConfigurationTests(unittest.TestCase):
    def test_provider_key_alone_is_not_a_ready_generation_runtime(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'unused-fixture'}, clear=True):
            self.assertFalse(generation_configuration()['configured'])
            self.assertEqual(readiness()['status'], 'NOT_CONFIGURED')
            client = TestClient(app)
            tag = client.get('/v1/exams/current/spec').headers['etag']
            with patch('services.api.routes.exams.GenerationJobService.start_job') as start:
                response = client.post('/v1/exams/current/generation-jobs', headers={'If-Match': tag})
            self.assertEqual(response.status_code, 503)
            self.assertIn('暂不能开始出题', response.json()['detail'])
            start.assert_not_called()

    def test_configuration_does_not_claim_runtime_health_or_leak_credentials(self):
        values = {'DATABASE_URL':'fixture-db','CELERY_BROKER_URL':'amqp://fixture',
                  'HERMES_API_BASE_URL':'http://author','HERMES_SOLVER_API_BASE_URL':'http://solver',
                  'HERMES_API_KEY':'private-author-fixture','HERMES_SOLVER_API_KEY':'private-solver-fixture'}
        with patch.dict(os.environ, values, clear=True):
            result = generation_configuration()
            self.assertTrue(result['configured'])
            self.assertFalse(result['runtime_verified'])
            self.assertNotIn('private-', str(result))
            os.environ['HERMES_SOLVER_API_BASE_URL']='http://author/'
            self.assertFalse(generation_configuration()['configured'])
