from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Offline project record tests split by independent behavior cases."""
from tests.project_memory_cases_1 import MemoryCases1Tests
from tests.project_memory_cases_2 import MemoryCases2Tests
from tests.project_memory_cases_3 import MemoryCases3Tests

if __name__ == "__main__":
    unittest.main()
