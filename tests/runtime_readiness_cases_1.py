"""Runtime readiness checks."""
from tests.runtime_readiness_shared import *

class RuntimeReadinessProbeTests(unittest.TestCase):
    """Test _probe_all / runtime_readiness orchestration with mocked probes."""

    def setUp(self):
        health.clear_readiness_cache()
        self.env = patch.dict(os.environ, CONFIGURED_ENV, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        health.clear_readiness_cache()

    def _all_green(self):
        for name in ('_probe_database', '_probe_broker', '_probe_author', '_probe_solver', '_probe_budget'):
            patcher = patch.object(health, name, side_effect=ok_probe(name))
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(health, '_probe_heartbeats', side_effect=ok_heartbeats)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_all_green(self):
        self._all_green()
        result = health.runtime_readiness()
        self.assertTrue(result['ready'])
        self.assertTrue(result['configured'])
        self.assertTrue(result['runtime_verified'])
        self.assertEqual(result['reason_codes'], [])
        self.assertTrue(result['checked_at'])
        self.assertEqual(set(result['components']),
                         {'database', 'broker', 'worker', 'dispatcher', 'author', 'solver', 'budget'})
        for name, component in result['components'].items():
            self.assertEqual(component['ok'], True, name)
            self.assertNotIn('reason', component)

    def test_database_down_reason_code(self):
        self._all_green()
        p = patch.object(health, '_probe_database', side_effect=fail_probe('DATABASE_UNAVAILABLE')); p.start(); self.addCleanup(p.stop)
        result = health.runtime_readiness()
        self.assertFalse(result['ready'])
        self.assertEqual(result['reason_codes'], ['DATABASE_UNAVAILABLE'])

    def test_broker_down_reason_code(self):
        self._all_green()
        p = patch.object(health, '_probe_broker', side_effect=fail_probe('BROKER_UNAVAILABLE')); p.start(); self.addCleanup(p.stop)
        result = health.runtime_readiness()
        self.assertEqual(result['reason_codes'], ['BROKER_UNAVAILABLE'])

    def test_no_heartbeats_reason_codes(self):
        self._all_green()
        patch.object(health, '_probe_heartbeats', side_effect=lambda timeout: {
            'worker': {'ok': False, 'reason': 'WORKER_UNAVAILABLE'},
            'dispatcher': {'ok': False, 'reason': 'DISPATCHER_UNAVAILABLE'}}).start()
        result = health.runtime_readiness()
        self.assertEqual(result['reason_codes'], ['WORKER_UNAVAILABLE', 'DISPATCHER_UNAVAILABLE'])
        self.assertFalse(result['components']['worker']['ok'])
        self.assertFalse(result['components']['dispatcher']['ok'])

    def test_reason_codes_exact_order_and_deduplication(self):
        self._all_green()
        for name in ('_probe_database', '_probe_broker', '_probe_author', '_probe_budget'):
            p = patch.object(health, name, side_effect=fail_probe(name))
            p.start()
            self.addCleanup(p.stop)
        result = health.runtime_readiness()
        self.assertEqual(result['reason_codes'],
                         ['DATABASE_UNAVAILABLE', 'BROKER_UNAVAILABLE', 'AUTHOR_UNAVAILABLE', 'BUDGET_UNAVAILABLE'])

    def test_author_solver_same_base_url_isolation_misconfig(self):
        self._all_green()
        for author_url, solver_url in (('http://gateway.test', 'http://gateway.test'),
                                       ('http://gateway.test/', 'http://gateway.test')):
            with patch.dict(os.environ, {'HERMES_API_BASE_URL': author_url,
                                         'HERMES_SOLVER_API_BASE_URL': solver_url}, clear=False):
                result = health.runtime_readiness()
                self.assertFalse(result['ready'])
                self.assertIn('ISOLATION_MISCONFIG', result['reason_codes'])
                self.assertFalse(result['components']['solver']['ok'])

    def test_not_configured_prepends_code(self):
        self._all_green()
        p = patch.object(health, 'generation_configuration',
                         return_value=dict(CONFIGURED, configured=False))
        p.start()
        self.addCleanup(p.stop)
        result = health.runtime_readiness()
        self.assertFalse(result['ready'])
        self.assertIn('NOT_CONFIGURED', result['reason_codes'])

    def test_cache_serves_until_ttl(self):
        self._all_green()
        first = health.runtime_readiness()
        second = health.runtime_readiness()
        self.assertIs(first, second)  # served from cache, same object
        # Probes were only invoked once per component.
        with patch.object(health, '_probe_database') as probe:
            probe.return_value = {'ok': False}
            health.runtime_readiness()  # cache still fresh -> probe NOT called
            probe.assert_not_called()

    def test_cache_expiry_does_not_extend_old_green(self):
        self._all_green()
        first = health.runtime_readiness()
        self.assertTrue(first['ready'])
        # Flip every probe but heartbeats to failing and force cache expiry.
        for name in ('_probe_database', '_probe_broker', '_probe_author', '_probe_solver', '_probe_budget'):
            p = patch.object(health, name, side_effect=fail_probe(name))
            p.start()
            self.addCleanup(p.stop)
        with health._READINESS_CACHE_LOCK:
            health._READINESS_CACHE['checked_at'] = time.monotonic() - 1000
        # heartbeats stay green so the only failing probe is _probe_author.
        result = health.runtime_readiness()
        self.assertFalse(result['ready'])
        self.assertIn('AUTHOR_UNAVAILABLE', result['reason_codes'])

    def test_cache_invalidated_on_config_change(self):
        self._all_green()
        health.runtime_readiness()
        with patch.object(health, '_probe_author') as probe:
            probe.return_value = {'ok': True}
            with patch.dict(os.environ, {'HERMES_API_BASE_URL': 'http://other-author.test'}, clear=False):
                health.runtime_readiness()
            probe.assert_called_once_with(health.probe_timeout())

    def test_checked_at_is_iso8601(self):
        self._all_green()
        result = health.runtime_readiness()
        from datetime import datetime
        datetime.fromisoformat(result['checked_at'])  # raises on non-ISO value

