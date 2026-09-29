"""Runtime readiness checks."""
from tests.runtime_readiness_shared import *

class IsolationGatewayReadinessTests(unittest.TestCase):
    """Narrow /internal/readiness route on the solver gateway (real server on
    127.0.0.1, closed right after the test)."""

    @classmethod
    def setUpClass(cls):
        cls.env = patch.dict(os.environ, {
            'HERMES_SOLVER_API_KEY': 'test-solver-key',
            'HERMES_SOLVER_MODEL_ID': 'deepseek-flash',
            'HERMES_SOLVER_UPSTREAM_URL': 'http://127.0.0.1:9',  # unreachable: proves no forwarding
            'HERMES_SOLVER_API_BASE_URL': '',
        }, clear=True)
        cls.env.start()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), GatewayHandler)
        cls.base = f'http://127.0.0.1:{cls.server.server_address[1]}'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.env.stop()

    def _get(self, path, token=None):
        headers = {'Authorization': f'Bearer {token}'} if token else {}
        request = Request(self.base + path, headers=headers)
        return urlopen(request, timeout=2)

    def test_readiness_requires_auth(self):
        with self.assertRaises(HTTPError) as exc:
            self._get('/internal/readiness')
        self.assertEqual(exc.exception.code, 401)
        exc.exception.close()

    def test_readiness_ok_returns_non_secret_config(self):
        response = self._get('/internal/readiness', token='test-solver-key')
        self.assertEqual(response.status, 200)
        body = json.loads(response.read().decode())
        response.close()
        self.assertEqual(body['status'], 'OK')
        self.assertEqual(body['config_version'], GatewayHandler._CONFIG_VERSION)
        self.assertEqual(body['role'], 'solver')
        self.assertEqual(body['model'], 'deepseek-flash')
        self.assertTrue(body['upstream_configured'])
        body_text = json.dumps(body)
        self.assertNotIn('test-solver-key', body_text)  # no secret echo
        self.assertNotIn('run_id', body_text)

    def test_readiness_does_not_forward_to_upstream(self):
        # Upstream is on an unreachable port; a 200 local body proves no proxy.
        response = self._get('/internal/readiness', token='test-solver-key')
        self.assertEqual(response.status, 200)
        body = json.loads(response.read().decode())
        response.close()
        self.assertEqual(body['status'], 'OK')

    def test_unknown_path_still_404_with_auth(self):
        with self.assertRaises(HTTPError) as exc:
            self._get('/v1/anything-else', token='test-solver-key')
        self.assertEqual(exc.exception.code, 404)
        exc.exception.close()

    def test_runs_still_requires_auth(self):
        with self.assertRaises(HTTPError) as exc:
            self._get('/v1/runs/run_abc', token=None)
        self.assertEqual(exc.exception.code, 401)
        exc.exception.close()

