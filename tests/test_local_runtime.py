from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Offline local runtime tests."""
from tests.local_runtime_cases_1 import DotenvParsingTests, PidOwnershipTests, DoctorOutputStructureTests
from tests.local_runtime_cases_2 import BudgetCheckDirectTests, StartGenerationSafetyTests, StopGenerationSafetyTests
from tests.local_runtime_cases_3 import ActiveJobQueryTests, SpawnCommandShapeTests

if __name__ == "__main__":
    unittest.main()
