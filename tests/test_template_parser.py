from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

"""Template parser offline checks."""
from tests.template_parser_cases_1 import TemplateParserCases1
from tests.template_parser_cases_2 import TemplateParserCases2

if __name__ == "__main__":
    unittest.main()
