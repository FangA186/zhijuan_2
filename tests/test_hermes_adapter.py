from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Hermes adapter offline contract checks."""
from tests.hermes_adapter_cases_1 import HermesAdapterCases1
from tests.hermes_adapter_cases_2 import HermesAdapterCases2

if __name__ == "__main__":
    unittest.main()
