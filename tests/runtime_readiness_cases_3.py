"""Isolated health probes, part 2."""
from tests.runtime_readiness_fixture import *

class IndividualProbeCases2(IndividualProbeFixture, unittest.TestCase):
    def test_solver_ok_body_bad_json(self):
        with patch.dict(os.environ, {'HERMES_SOLVER_API_BASE_URL': 'http://solver.test',
                                     'HERMES_SOLVER_API_KEY': 'solver-key'}, clear=False):
            with patch.object(health.httpx, 'Client',
                              return_value=FakeHttpxClient(FakeResponse(200, json_raises=ValueError('bad')))):
                result = health._probe_solver(1.0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['reason'], 'SOLVER_UNAVAILABLE')


    def test_budget_no_token_fail_closed(self):
        self.assertEqual(health._probe_budget(1.0)['reason'], 'BUDGET_UNAVAILABLE')


    def test_budget_401_fail_closed(self):
        with patch.dict(os.environ, self._budget_env(), clear=False):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(FakeResponse(401))):
                result = health._probe_budget(1.0)
        self.assertEqual(result['reason'], 'BUDGET_UNAVAILABLE')


    def test_budget_timeout_fail_closed(self):
        with patch.dict(os.environ, self._budget_env(), clear=False):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(TimeoutError('slow'))):
                result = health._probe_budget(1.0)
        self.assertEqual(result['reason'], 'BUDGET_UNAVAILABLE')


    def test_budget_bad_json_fail_closed(self):
        with patch.dict(os.environ, self._budget_env(), clear=False):
            with patch.object(health.httpx, 'Client',
                              return_value=FakeHttpxClient(FakeResponse(200, json_raises=ValueError('bad')))):
                result = health._probe_budget(1.0)
        self.assertEqual(result['reason'], 'BUDGET_UNAVAILABLE')


    def test_budget_missing_fields_fail_closed(self):
        partial = {k: v for k, v in self.BUDGET_OK.items() if k != 'pending_count'}
        with patch.dict(os.environ, self._budget_env(), clear=False):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(FakeResponse(200, json_data=partial))):
                result = health._probe_budget(1.0)
        self.assertEqual(result['reason'], 'BUDGET_UNAVAILABLE')


    def test_budget_ok(self):
        with patch.dict(os.environ, self._budget_env(), clear=False):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(FakeResponse(200, json_data=self.BUDGET_OK))):
                result = health._probe_budget(1.0)
        self.assertTrue(result['ok'])
        self.assertNotIn('reason', result)


    def test_budget_insufficient_is_distinct(self):
        data = dict(self.BUDGET_OK, sufficient=False, reason_code='BUDGET_INSUFFICIENT')
        with patch.dict(os.environ, self._budget_env(), clear=False):
            with patch.object(health.httpx, 'Client', return_value=FakeHttpxClient(FakeResponse(200, json_data=data))):
                result = health._probe_budget(1.0)
        self.assertFalse(result['ok'])  # not usable for generation...
        self.assertEqual(result['reason'], 'BUDGET_INSUFFICIENT')  # ...with a distinct code


