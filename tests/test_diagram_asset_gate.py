import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from services import diagram_assets
from services.api.routes import exams
from services.validators import validate_candidate


class DiagramAssetGateTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.asset_dir = Path(self.tempdir.name)
        self.asset_patch = patch.object(diagram_assets, "ASSET_DIR", self.asset_dir)
        self.asset_patch.start()
        self.addCleanup(self.asset_patch.stop)
        self.addCleanup(self.tempdir.cleanup)

    @staticmethod
    def candidate(block):
        return {
            "public": {"local_id": "q1", "kind": "single_choice", "prompt": [block],
                       "options": [{"id": x, "content": [{"type": "text", "text": x}]} for x in ("A", "B")],
                       "score_x100": 200, "material_ids": [], "children": [], "answer_space_lines": 0},
            "private": {"answers": [{"local_question_id": "q1", "answer_kind": "selection",
                                      "correct_option_ids": ["B"], "accepted_answers": [],
                                      "solution": [{"type": "text", "text": "2"}],
                                      "rubric": [{"id": "r1", "description": "correct", "score_x100": 200,
                                                  "acceptable_variants": []}]}]},
        }

    def validate(self, block):
        return validate_candidate(self.candidate(block), {"kind": "single_choice", "score_x100": 200}, {})

    def test_only_hash_checked_local_assets_pass_and_diagrams_fail(self):
        asset = diagram_assets.save_diagram({"kind": "counting_rods", "values": [2]})
        valid = self.validate(asset)
        self.assertEqual(next(c for c in valid["rule_checks"] if c["rule_id"] == "ASSET_INTEGRITY")["status"], "PASS")

        raw_diagram = {"type": "diagram", "spec": {"kind": "counting_rods", "values": [2]}}
        self.assertEqual(next(c for c in self.validate(raw_diagram)["rule_checks"]
                              if c["rule_id"] == "ASSET_INTEGRITY")["status"], "FAIL")

        bogus_id = self.validate({"type": "asset", "asset_id": "diagram-1", "alt": asset["alt"]})
        self.assertEqual(next(c for c in bogus_id["rule_checks"] if c["rule_id"] == "ASSET_INTEGRITY")["status"], "FAIL")

        (self.asset_dir / f"{asset['asset_id']}.svg").write_bytes(b"<svg>corrupt</svg>")
        corrupt = self.validate(asset)
        self.assertEqual(next(c for c in corrupt["rule_checks"] if c["rule_id"] == "ASSET_INTEGRITY")["status"], "FAIL")

    def test_asset_api_serves_only_current_public_references(self):
        asset = diagram_assets.save_diagram({"kind": "counting_rods", "values": [1]})
        public_candidate = {"public": {"prompt": [asset], "options": [], "children": []}}
        with patch.object(exams.QuestionService, "list_candidates", return_value=[public_candidate]):
            response = exams.get_current_asset(asset["asset_id"])
        self.assertEqual(response.body, diagram_assets.load_diagram(asset["asset_id"]))
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("default-src 'none'", response.headers["content-security-policy"])

        private_candidate = {"public": {"prompt": [], "options": [], "children": []},
                             "private": {"answers": [{"solution": [asset] }]}}
        with patch.object(exams.QuestionService, "list_candidates", return_value=[private_candidate]):
            with self.assertRaises(HTTPException) as missing_reference:
                exams.get_current_asset(asset["asset_id"])
        self.assertEqual(missing_reference.exception.status_code, 404)

    def test_hash_consistent_arbitrary_svg_and_traversal_are_not_served(self):
        svg = ('<svg xmlns="http://www.w3.org/2000/svg"><title>'
               '算筹纵式记数：1 对应 1 根竖棒'
               '</title><script>alert(1)</script></svg>').encode()
        asset_id = hashlib.sha256(svg).hexdigest()
        (self.asset_dir / f"{asset_id}.svg").write_bytes(svg)
        candidate = {"public": {"prompt": [{"type": "asset", "asset_id": asset_id,
                                            "alt": "算筹纵式记数：1 对应 1 根竖棒"}],
                               "options": [], "children": []}}
        with patch.object(exams.QuestionService, "list_candidates", return_value=[candidate]):
            with self.assertRaises(HTTPException) as untrusted:
                exams.get_current_asset(asset_id)
            with self.assertRaises(HTTPException) as traversal:
                exams.get_current_asset("../../etc/passwd")
        self.assertEqual(untrusted.exception.status_code, 404)
        self.assertEqual(traversal.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
