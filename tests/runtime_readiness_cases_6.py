"""Runtime readiness checks."""
from tests.runtime_readiness_shared import *

class ReadinessEndpointsTests(unittest.TestCase):
    """/readyz + /v1/readyz contract shape; /health stays plain liveness."""

    def setUp(self):
        self.env = patch.dict(os.environ, CONFIGURED_ENV, clear=True)
        self.env.start()
        self.client = TestClient(app)
        health.clear_readiness_cache()
        self._patchers = []
        self.green_patcher = patch.object(health, 'generation_configuration', return_value=CONFIGURED)
        self._patchers.append(self.green_patcher)
        self.generation_mock = self.green_patcher.start()
        self._probe_mocks = {}
        for name in ('_probe_database', '_probe_broker', '_probe_author', '_probe_solver', '_probe_budget'):
            patcher = patch.object(health, name)
            self._patchers.append(patcher)
            self._probe_mocks[name] = patcher.start()
            self._probe_mocks[name].side_effect = ok_probe(name)
        patcher = patch.object(health, '_probe_heartbeats')
        self._patchers.append(patcher)
        self._probe_mocks['_probe_heartbeats'] = patcher.start()
        self._probe_mocks['_probe_heartbeats'].side_effect = ok_heartbeats

    def tearDown(self):
        for patcher in self._patchers:
            patcher.stop()
        self.env.stop()
        health.clear_readiness_cache()

    def test_readyz_ready(self):
        response = self.client.get('/readyz')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'READY')
        generation = body['generation']
        self.assertTrue(generation['ready'])
        self.assertEqual(set(generation['reason_codes']), set())

    def test_readyz_not_ready(self):
        # Mutate the setUp probe mock (the real mock object, not the patcher).
        self._probe_mocks['_probe_database'].side_effect = fail_probe('DATABASE_UNAVAILABLE')
        response = self.client.get('/readyz')
        self.assertEqual(response.json()['status'], 'NOT_READY')
        self.assertIn('DATABASE_UNAVAILABLE', response.json()['generation']['reason_codes'])

    def test_readyz_not_configured(self):
        self.generation_mock.return_value = dict(CONFIGURED, configured=False)
        response = self.client.get('/readyz')
        body = response.json()
        self.assertEqual(body['status'], 'NOT_CONFIGURED')
        self.assertIn('NOT_CONFIGURED', body['generation']['reason_codes'])

    def test_v1_readyz_alias(self):
        response = self.client.get('/v1/readyz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'READY')

    def test_generation_contract_shape(self):
        self._probe_mocks['_probe_heartbeats'].side_effect = lambda timeout: {
            'worker': {'ok': False, 'reason': 'WORKER_UNAVAILABLE'},
            'dispatcher': {'ok': False, 'reason': 'DISPATCHER_UNAVAILABLE'}}
        response = self.client.get('/readyz')
        generation = response.json()['generation']
        for field in ('configured', 'checks', 'runtime_verified', 'ready', 'checked_at',
                      'reason_codes', 'components'):
            self.assertIn(field, generation)
        for name in ('database', 'broker', 'worker', 'dispatcher', 'author', 'solver', 'budget'):
            self.assertIn(name, generation['components'])
            self.assertIn('ok', generation['components'][name])
        self.assertEqual(response.json()['status'], 'NOT_READY')

    def test_health_remains_liveness_only(self):
        # Make every probe raise loudly, then confirm /health never probes
        # while /readyz still can (probes are mutated, not re-patched).
        health.clear_readiness_cache()
        for name, mock in self._probe_mocks.items():
            mock.side_effect = AssertionError('must not probe')
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['status'], 'HEALTHY')
        self.assertFalse(body['generation']['runtime_verified'])
        for name, mock in self._probe_mocks.items():
            mock.side_effect = ok_heartbeats if name == '_probe_heartbeats' else ok_probe(name)
        self.assertEqual(self.client.get('/readyz').json()['status'], 'READY')

