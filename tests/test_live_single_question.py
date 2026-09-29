from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Single-question workflow offline checks."""
from tests.live_single_question_cases_1 import DotenvSafetyTests, TestDatabaseFenceTests
from tests.live_single_question_cases_2 import BudgetFenceTests
from tests.live_single_question_cases_3 import RunFailureRedactionTests, AuthorSolverProbeTests
from tests.live_single_question_cases_4 import SeedSpecTests, EvidenceReportTests, TeardownOrderTests
from tests.live_single_question_cases_5 import TerminalNoRetryTests

if __name__ == "__main__":
    unittest.main()
