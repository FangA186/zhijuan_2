"""Shared isolated probe setup."""
from tests.runtime_readiness_shared import *

class IndividualProbeFixture:
    BUDGET_OK = {
        'run_id': 'fixture', 'calls': 0, 'max_requests': None,
        'reserved_cny': 0, 'max_reserved_cny': None,
        'remaining_requests': None, 'remaining_cny': None,
        'reserve_per_request_cny': 1, 'pending_count': 0,
        'sufficient': True, 'reason_code': 'BUDGET_OK',
        'checked_at': '2026-09-24T00:00:00+00:00',
    }

    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        health.clear_readiness_cache()


    def tearDown(self):
        self.env.stop()


    def _budget_env(self, token='token-fixture'):
        return {'ZHIJUAN_BUDGET_PROXY_TOKEN': token,
                'ZHIJUAN_BUDGET_INTERNAL_URL': 'http://budget.test/internal/budget'}



__all__ = [name for name in globals() if not name.startswith("__")]
