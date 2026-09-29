from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Local budget proxy offline checks."""
from tests.live_budget_proxy_cases import BudgetProxyTests, LegacyLimitEnvironmentTests
from tests.live_budget_status_cases import BudgetStatusInternalTests

if __name__ == "__main__":
    unittest.main()
