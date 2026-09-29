"""Model validation must not invent answers, scores, or replace rendered blocks."""
import copy
import json
from pathlib import Path
import unittest
from services.hermes_adapter.schema_validator import validate_candidate, SchemaValidationError

class CandidateIntegrityTests(unittest.TestCase):
    def candidate(self):
        return json.loads((Path(__file__).resolve().parents[1]/'examples/candidate.json').read_text())

    def test_missing_rubric_and_extra_fields_fail_without_mutating(self):
        for change in [lambda c:c['private']['answers'][0].pop('rubric'),lambda c:c['public']['prompt'][0].update(unexpected='canary'),lambda c:c['public'].update(score_x100=300.9)]:
            candidate=self.candidate();change(candidate);before=copy.deepcopy(candidate)
            with self.assertRaises(SchemaValidationError):validate_candidate(candidate)
            self.assertEqual(candidate,before)

    def test_valid_empty_accepted_answers_and_asset_block_are_preserved(self):
        candidate=self.candidate();candidate['private']['answers'][0]['accepted_answers']=[]
        candidate['public']['prompt']=[{'type':'asset','asset_id':'diagram-1','alt':'question diagram'}]
        before=copy.deepcopy(candidate)
        validate_candidate(candidate)
        self.assertEqual(candidate,before)
