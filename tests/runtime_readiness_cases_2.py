"""Isolated health probes, part 1."""
from tests.runtime_readiness_fixture import *

class IndividualProbeCases1(IndividualProbeFixture, unittest.TestCase):
    def test_database_unconfigured(self):
        result = health._probe_database(1.0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'DATABASE_UNAVAILABLE')


    def test_database_connection_error(self):
        with patch.object(psycopg, 'connect', side_effect=OSError('refused')):
            result = health._probe_database(1.0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'DATABASE_UNAVAILABLE')


    def test_database_missing_generation_table(self):
        rows = [('generation_jobs',), ('generation_exam_state',)]  # only 2 of 6 tables
        conn = FakeConn()
        conn.execute = MagicMock(side_effect=[FakeCursor([(1,)]), FakeCursor(rows)])
        with patch.dict(os.environ, {'DATABASE_URL': 'fixture-dsn'}, clear=False):
            with patch.object(psycopg, 'connect', return_value=conn):
                result = health._probe_database(1.0)
        self.assertFalse(result['ok'])
        self.assertIn('generation_exam_revisions', result['detail'])
        self.assertEqual(result['reason'], 'DATABASE_UNAVAILABLE')


    def test_database_all_tables_present(self):
        tables = [f'{name},'.rstrip(',') for name in
                  ('generation_jobs', 'generation_exam_state', 'generation_exam_revisions',
                   'generation_job_outbox', 'generation_job_results', 'generation_job_history')]
        conn = FakeConn()
        conn.execute = MagicMock(side_effect=[FakeCursor([(1,)]), FakeCursor([(t,) for t in tables])])
        with patch.dict(os.environ, {'DATABASE_URL': 'fixture-dsn'}, clear=False):
            with patch.object(psycopg, 'connect', return_value=conn):
                result = health._probe_database(1.0)
        self.assertTrue(result['ok'])


    def test_broker_not_amqp(self):
        self.assertEqual(health._probe_broker(1.0)['reason'], 'BROKER_UNAVAILABLE')


    def test_broker_connection_error(self):
        import kombu
        fake = MagicMock()
        fake.ensure_connection.side_effect = OSError('refused')
        with patch.object(os.environ, 'get', return_value='amqp://127.0.0.1:9'):
            with patch.object(kombu, 'Connection', return_value=fake) as conn_cls:
                result = health._probe_broker(1.0)
            conn_cls.assert_called_once_with('amqp://127.0.0.1:9',
                                             transport_options={'connect_timeout': 1.0})
        self.assertEqual(result['reason'], 'BROKER_UNAVAILABLE')


    def test_broker_reachable(self):
        import kombu
        fake = MagicMock()
        with patch.object(os.environ, 'get', return_value='amqp://127.0.0.1:9'):
            with patch.object(kombu, 'Connection', return_value=fake):
                result = health._probe_broker(1.0)
        self.assertTrue(result['ok'])
        fake.release.assert_called_once()


    def test_author_unconfigured(self):
        self.assertEqual(health._probe_author(1.0)['reason'], 'AUTHOR_UNAVAILABLE')


    def test_author_ok(self):
        with patch.object(os.environ, 'get', return_value='http://author.test'):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(FakeResponse(200))):
                result = health._probe_author(1.0)
        self.assertTrue(result['ok'])


    def test_author_non_200(self):
        with patch.object(os.environ, 'get', return_value='http://author.test'):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(FakeResponse(503))):
                result = health._probe_author(1.0)
        self.assertEqual(result['reason'], 'AUTHOR_UNAVAILABLE')


    def test_author_timeout(self):
        with patch.object(os.environ, 'get', return_value='http://author.test'):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(TimeoutError('slow'))):
                result = health._probe_author(1.0)
        self.assertEqual(result['reason'], 'AUTHOR_UNAVAILABLE')


    def test_solver_unconfigured(self):
        self.assertEqual(health._probe_solver(1.0)['reason'], 'SOLVER_UNAVAILABLE')


    def test_solver_ok_with_bearer_auth(self):
        body = {"status": "OK", "role": "solver", "model": "deepseek-flash",
                "upstream_configured": True, "config_version": 1}
        with patch.dict(os.environ, {'HERMES_SOLVER_API_BASE_URL': 'http://solver.test',
                                     'HERMES_SOLVER_API_KEY': 'solver-key'}, clear=False):
            client = FakeHttpxClient(FakeResponse(200, json_data=body))
            with patch.object(health.httpx, 'Client', return_value=client):
                result = health._probe_solver(1.0)
        self.assertTrue(result['ok'])
        url, kwargs = client.last_request
        self.assertEqual(url, 'http://solver.test/internal/readiness')
        self.assertEqual(kwargs['headers']['Authorization'], 'Bearer solver-key')


    def test_solver_401(self):
        with patch.dict(os.environ, {'HERMES_SOLVER_API_BASE_URL': 'http://solver.test',
                                     'HERMES_SOLVER_API_KEY': 'solver-key'}, clear=False):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(FakeResponse(401))):
                result = health._probe_solver(1.0)
        self.assertEqual(result['reason'], 'SOLVER_UNAVAILABLE')


    def test_solver_ok_body_missing_upstream_configured(self):
        # 200 responses are still read body-first: a gateway that reports no
        # upstream_configured must not open the admission gate.
        body = {"status": "OK", "role": "solver", "model": "deepseek-flash"}
        with patch.dict(os.environ, {'HERMES_SOLVER_API_BASE_URL': 'http://solver.test',
                                     'HERMES_SOLVER_API_KEY': 'solver-key'}, clear=False):
            with patch.object(health.httpx, 'Client',
                              return_value=FakeHttpxClient(FakeResponse(200, json_data=body))):
                result = health._probe_solver(1.0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'SOLVER_UNAVAILABLE')


    def test_solver_ok_body_upstream_not_configured(self):
        body = {"status": "OK", "role": "solver", "model": "deepseek-flash",
                "upstream_configured": False}
        with patch.dict(os.environ, {'HERMES_SOLVER_API_BASE_URL': 'http://solver.test',
                                     'HERMES_SOLVER_API_KEY': 'solver-key'}, clear=False):
            with patch.object(health.httpx, 'Client',
                              return_value=FakeHttpxClient(FakeResponse(200, json_data=body))):
                result = health._probe_solver(1.0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'SOLVER_UNAVAILABLE')


