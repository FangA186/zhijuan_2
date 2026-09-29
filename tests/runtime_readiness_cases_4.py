"""Runtime readiness checks."""
from tests.runtime_readiness_shared import *

class HeartbeatReadinessTests(unittest.TestCase):
    """Test the heartbeat probe against a fake C2 runtime_heartbeats module.

    The real services/api/runtime_heartbeats.py lands in a parallel task; this
    fake mirrors contract C2's fresh_components signature.
    """

    FAKE_MODULE_NAME = 'services.api.runtime_heartbeats'

    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        os.environ['DATABASE_URL'] = 'fixture-dsn'
        os.environ['ZHIJUAN_RUNTIME_ID'] = 'zhijuan-test'
        os.environ['ZHIJUAN_HEARTBEAT_TTL_SECONDS'] = '20'
        os.environ['ZHIJUAN_DEEPSEEK_MODEL_ID'] = 'deepseek-flash'
        health.clear_readiness_cache()
        self.fake_module = types.ModuleType(self.FAKE_MODULE_NAME)
        self.fake_module.fresh_components = MagicMock(return_value={})
        sys.modules[self.FAKE_MODULE_NAME] = self.fake_module
        self.conn_patch = patch.object(psycopg, 'connect', return_value=FakeConn())
        self.conn_patch.start()
        self.model_patch = patch.object(health.settings, 'deepseek_model_id', 'deepseek-flash')
        self.model_patch.start()
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.conn_patch.stop()
        self.model_patch.stop()
        sys.modules.pop(self.FAKE_MODULE_NAME, None)
        # Restore the process environment: setUp's patch.dict(clear=True) wrote
        # DATABASE_URL=fixture-dsn / ZHIJUAN_RUNTIME_ID=zhijuan-test, and leaving
        # them behind breaks later test modules (e.g. test_workflow_safety_closeout
        # hits psycopg.connect('fixture-dsn') with a bogus DSN). addCleanup does not
        # run self.env.stop() automatically, so stop it here explicitly.
        self.env.stop()

    @staticmethod
    def _fresh(component, age, model='deepseek-flash'):
        return {component: {'ok': True, 'age_seconds': age, 'metadata': {'model_id': model}}}

    def test_heartbeats_module_missing_degrades(self):
        sys.modules.pop(self.FAKE_MODULE_NAME, None)
        result = health._probe_heartbeats(1.0)
        self.assertEqual(result['worker']['reason'], 'WORKER_UNAVAILABLE')
        self.assertEqual(result['dispatcher']['reason'], 'DISPATCHER_UNAVAILABLE')
        self.assertFalse(result['worker']['ok'])

    def test_db_unconfigured_heartbeats_fail(self):
        with patch.dict(os.environ, {'DATABASE_URL': ''}, clear=False):
            result = health._probe_heartbeats(1.0)
        self.assertEqual(result['worker']['reason'], 'DATABASE_UNAVAILABLE')

    def test_calls_fresh_components_with_runtime_id_and_ttl(self):
        with patch.dict(os.environ, {'ZHIJUAN_RUNTIME_ID': 'zhijuan-other'}, clear=False):
            health._probe_heartbeats(1.0)
        args = self.fake_module.fresh_components.call_args
        conn, runtime, ttl = args[0]
        self.assertIsInstance(conn, FakeConn)
        self.assertEqual(runtime, 'zhijuan-other')
        self.assertEqual(ttl, 20.0)

    def test_worker_and_dispatcher_fresh(self):
        fresh = {}
        fresh.update(self._fresh('worker', 1.0))
        fresh.update(self._fresh('dispatcher', 0.5))
        self.fake_module.fresh_components.return_value = fresh
        result = health._probe_heartbeats(1.0)
        self.assertTrue(result['worker']['ok'])
        self.assertTrue(result['dispatcher']['ok'])
        self.assertNotIn('reason', result['worker'])

    def test_cross_runtime_heartbeats_not_accepted(self):
        # fresh_components filters by runtime_id; heartbeats from another
        # runtime simply do not appear in its result (contract C2).
        self.fake_module.fresh_components.return_value = {'worker': self._fresh('worker', 1.0)['worker']}
        result = health._probe_heartbeats(1.0)
        self.assertTrue(result['worker']['ok'])
        # Dispatcher has no heartbeat at all -> unavailable.
        self.assertEqual(result['dispatcher']['reason'], 'DISPATCHER_UNAVAILABLE')

    def test_no_heartbeat_rows(self):
        self.fake_module.fresh_components.return_value = {}
        result = health._probe_heartbeats(1.0)
        self.assertEqual(result['worker']['reason'], 'WORKER_UNAVAILABLE')
        self.assertEqual(result['dispatcher']['reason'], 'DISPATCHER_UNAVAILABLE')

    def test_heartbeat_boundary_before_expiry(self):
        self.fake_module.fresh_components.return_value = self._fresh('worker', 19.99)
        result = health._probe_heartbeats(1.0)
        self.assertTrue(result['worker']['ok'])

    def test_heartbeat_boundary_at_expiry(self):
        # Defensive guard: an entry at exactly the TTL is treated as stale
        # even if fresh_components reported ok.
        self.fake_module.fresh_components.return_value = self._fresh('worker', 20.0)
        result = health._probe_heartbeats(1.0)
        self.assertEqual(result['worker']['reason'], 'HEARTBEAT_STALE')

    def test_heartbeat_expired_by_component(self):
        self.fake_module.fresh_components.return_value = {
            'worker': {'ok': False, 'age_seconds': 25.0, 'metadata': {}},
            'dispatcher': {'ok': True, 'age_seconds': 1.0, 'metadata': {'model_id': 'deepseek-flash'}}}
        result = health._probe_heartbeats(1.0)
        self.assertEqual(result['worker']['reason'], 'WORKER_UNAVAILABLE')
        self.assertTrue(result['dispatcher']['ok'])

    def test_model_mismatch(self):
        self.fake_module.fresh_components.return_value = self._fresh('worker', 1.0, model='deepseek-chat')
        result = health._probe_heartbeats(1.0)
        self.assertEqual(result['worker']['reason'], 'MODEL_MISMATCH')
        self.assertFalse(result['worker']['ok'])

    def test_heartbeat_table_error_fails_closed(self):
        self.conn_patch.stop()
        with patch.object(psycopg, 'connect', side_effect=psycopg.OperationalError('table missing')):
            result = health._probe_heartbeats(1.0)
        self.assertEqual(result['worker']['reason'], 'WORKER_UNAVAILABLE')
        self.assertEqual(result['dispatcher']['reason'], 'DISPATCHER_UNAVAILABLE')

