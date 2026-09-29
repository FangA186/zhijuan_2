"""Offline checks for trusted counting-rod SVG assets."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator
import services.diagram_assets as diagrams


class DiagramAssetTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.asset_dir = Path(self.tempdir.name)
        self.patch_assets = patch.object(diagrams, "ASSET_DIR", self.asset_dir)
        self.patch_assets.start()
        self.addCleanup(self.patch_assets.stop)
        self.addCleanup(self.tempdir.cleanup)

    @staticmethod
    def candidate():
        return json.loads((Path(__file__).resolve().parents[1] / "examples/candidate.json").read_text())

    def test_valid_counting_rods_render_to_repeatable_hash_asset(self):
        spec = {"kind": "counting_rods", "values": [1, 3, 5]}
        svg, alt = diagrams.render_counting_rods(spec)
        self.assertEqual(svg.count(b"<line "), 9)
        self.assertIn("1 对应 1 根竖棒；3 对应 3 根竖棒；5 对应 5 根竖棒", alt)

        first = diagrams.save_diagram(spec)
        second = diagrams.save_diagram(spec)
        self.assertEqual(first, second)
        self.assertEqual(first["asset_id"], hashlib.sha256(svg).hexdigest())
        self.assertEqual(diagrams.load_diagram(first["asset_id"]), svg)
        self.assertEqual([p.suffix for p in self.asset_dir.iterdir()], [".svg"])

    def test_invalid_diagram_specs_are_rejected(self):
        invalid = [
            None,
            {"kind": "freeform", "values": [1]},
            {"kind": "counting_rods", "values": []},
            {"kind": "counting_rods", "values": [0]},
            {"kind": "counting_rods", "values": [6]},
            {"kind": "counting_rods", "values": [True]},
            {"kind": "counting_rods", "values": [1.5]},
            {"kind": "counting_rods", "values": ["2"]},
            {"kind": "counting_rods", "values": [1] * 10},
            {"kind": "counting_rods", "values": [1], "color": "red"},
        ]
        for spec in invalid:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                diagrams.render_counting_rods(spec)

    def test_candidate_contract_accepts_only_counting_rod_spec(self):
        schema = json.loads((Path(__file__).resolve().parents[1] / "contracts/candidate.schema.json").read_text())
        validator = Draft202012Validator(schema)
        candidate = self.candidate()
        candidate["public"]["prompt"] = [{
            "type": "diagram", "spec": {"kind": "counting_rods", "values": [1, 5]}
        }]
        self.assertTrue(validator.is_valid(candidate))
        for invalid_spec in (
            {"kind": "counting_rods", "values": [0]},
            {"kind": "counting_rods", "values": [6]},
            {"kind": "counting_rods", "values": [1], "color": "red"},
            {"kind": "other", "values": [1]},
        ):
            with self.subTest(spec=invalid_spec):
                candidate["public"]["prompt"][0]["spec"] = invalid_spec
                self.assertFalse(validator.is_valid(candidate))

    def test_new_candidate_diagrams_are_normalized_and_author_assets_rejected(self):
        candidate = self.candidate()
        candidate["public"]["prompt"] = [{
            "type": "diagram", "spec": {"kind": "counting_rods", "values": [2, 4]}
        }]
        original = copy.deepcopy(candidate)
        normalized = diagrams.materialize_candidate(candidate)
        block = normalized["public"]["prompt"][0]
        self.assertEqual(block["type"], "asset")
        self.assertEqual(diagrams.load_diagram(block["asset_id"])[:4], b"<svg")
        self.assertTrue(diagrams.diagram_asset_matches(block["asset_id"], block["alt"]))
        self.assertFalse(diagrams.diagram_asset_matches(block["asset_id"], "模型改写的说明"))
        self.assertEqual(candidate, original)

        candidate["public"]["prompt"] = [{"type": "asset", "asset_id": "0" * 64, "alt": "伪造"}]
        with self.assertRaisesRegex(ValueError, "unresolved asset"):
            diagrams.materialize_candidate(candidate)

    def test_question_service_normalizes_before_blind_solver(self):
        from reference_code.adapter_contract import RunResult
        from services.exam.question_service import QuestionService

        candidate = self.candidate()
        candidate["public"]["prompt"] = [{
            "type": "diagram", "spec": {"kind": "counting_rods", "values": [2, 4]}
        }]
        spec = json.loads((Path(__file__).resolve().parents[1] / "examples/exam-spec.json").read_text())
        slot = {"slot_id": "s1", "kind": candidate["public"]["kind"],
                "score_x100": candidate["public"]["score_x100"], "spec_revision": 1,
                "plan_revision": 1, "question_revision_id": "qrev-1"}
        adapter = Mock()
        adapter.run_stage.side_effect = [
            RunResult("SUCCEEDED", candidate, (), {}, None),
            RunResult("SUCCEEDED", {"derived_answer": "x=4", "selected_option_ids": ["opt-2"],
                                    "steps": []}, (), {}, None),
            RunResult("SUCCEEDED", {"question_revision_id": "qrev-1", "action": "no_change", "issues": [], "summary": "需教师复核"}, (), {}, None),
        ]
        with patch.object(QuestionService, "get_adapter", return_value=adapter):
            result = QuestionService.generate_slot_result(candidate["public"]["local_id"], spec=spec, slot=slot)

        solver_request = adapter.run_stage.call_args_list[1].args[0]
        self.assertEqual(solver_request.input_payload["public_question"]["prompt"][0]["type"], "asset")
        self.assertEqual(result["candidate"]["public"]["prompt"][0]["type"], "asset")

    def test_private_solution_diagrams_are_rejected(self):
        candidate = self.candidate()
        candidate["private"]["answers"][0]["solution"] = [{
            "type": "diagram", "spec": {"kind": "counting_rods", "values": [1]}
        }]
        with self.assertRaisesRegex(ValueError, "Private solution diagrams"):
            diagrams.materialize_candidate(candidate)

    def test_bad_or_unissued_asset_ids_and_corrupt_files_are_not_loaded(self):
        self.assertIsNone(diagrams.load_diagram("../" + "0" * 64))
        self.assertIsNone(diagrams.load_diagram(None))
        self.assertIsNone(diagrams.load_diagram("f" * 64))

        issued = diagrams.save_diagram({"kind": "counting_rods", "values": [5]})
        path = self.asset_dir / f"{issued['asset_id']}.svg"
        path.write_bytes(b"<svg>tampered</svg>")
        self.assertIsNone(diagrams.load_diagram(issued["asset_id"]))
        with self.assertRaisesRegex(ValueError, "corruption"):
            diagrams.save_diagram({"kind": "counting_rods", "values": [5]})

    def test_unreadable_asset_fails_closed(self):
        with patch.object(Path, "read_bytes", side_effect=PermissionError):
            self.assertIsNone(diagrams.load_diagram("a" * 64))


if __name__ == "__main__":
    unittest.main()
