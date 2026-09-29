from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Runtime readiness offline and local endpoint checks."""
from tests.runtime_readiness_cases_1 import RuntimeReadinessProbeTests
from tests.runtime_readiness_cases_2 import IndividualProbeCases1
from tests.runtime_readiness_cases_3 import IndividualProbeCases2
from tests.runtime_readiness_cases_4 import HeartbeatReadinessTests
from tests.runtime_readiness_cases_5 import IsolationGatewayReadinessTests
from tests.runtime_readiness_cases_6 import ReadinessEndpointsTests

if __name__ == "__main__":
    unittest.main()
