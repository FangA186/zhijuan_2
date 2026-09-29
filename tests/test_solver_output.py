"""Bounded solver summaries allow five or more steps without weakening shape checks."""
import unittest
from services.hermes_adapter.solver_output import valid_solver_steps, SOLVER_OUTPUT_INSTRUCTIONS


class SolverOutputTests(unittest.TestCase):
    def test_five_steps_are_valid(self):
        self.assertTrue(valid_solver_steps([{'text': f'可审核结论 {i}'} for i in range(5)]))
        self.assertTrue(valid_solver_steps([{'text': 'x'*500} for _ in range(12)]))
        self.assertNotIn('At most 4', SOLVER_OUTPUT_INSTRUCTIONS)

    def test_reject_bad_fields_private_reasoning_and_oversized_summaries(self):
        for value in [None, 'steps', [{'text': 1}], [{'text': ''}], [{'text': ' '}],
                      [{'text': 'summary', 'reasoning': 'private'}], [{'text': 'x'*501}],
                      [{'text': 'x'*500} for _ in range(13)]]:
            with self.subTest(value_type=type(value).__name__):
                self.assertFalse(valid_solver_steps(value))
