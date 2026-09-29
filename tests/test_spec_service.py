"""Offline checks for the specification boundary; no model or network access."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from services.exam.spec_validation import validate_spec
from services.exam.spec_service import SpecService


ROOT = Path(__file__).resolve().parents[1]


class SpecValidationTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((ROOT / "examples/exam-spec-primary.json").read_text(encoding="utf-8"))

    def test_approved_examples_and_minimum_fixtures_use_stage_local_years(self):
        paths = [
            ROOT / "examples/exam-spec-primary.json",
            ROOT / "examples/exam-spec.json",
            ROOT / "examples/exam-spec-senior.json",
            ROOT / "acceptance/fixtures/minimum-primary.json",
            ROOT / "acceptance/fixtures/minimum-junior.json",
            ROOT / "acceptance/fixtures/minimum-senior.json",
        ]
        for path in paths:
            with self.subTest(path=path.name):
                spec = json.loads(path.read_text(encoding="utf-8"))
                validate_spec(spec)
                self.assertIn(spec["stage_year"], range(1, 7) if spec["stage"] == "primary" else range(1, 4))

    def test_rejects_absolute_school_years_for_junior_and_senior(self):
        for stage, old_year in (("junior", 7), ("junior", 9), ("senior", 10), ("senior", 12)):
            with self.subTest(stage=stage, old_year=old_year):
                spec = copy.deepcopy(self.spec)
                spec["stage"], spec["stage_year"] = stage, old_year
                with self.assertRaisesRegex(ValueError, "stage_year"):
                    validate_spec(spec)

    def test_rejects_unconfirmed_or_mismatched_scores_before_store(self):
        for change in (
            lambda s: s["taught_scope"].update(scope_confirmed=False),
            lambda s: s.update(total_score_x100=9999),
            lambda s: s["sections"][0].update(score_each_x100=500.5),
            lambda s: s.update(stage="senior"),
        ):
            spec = copy.deepcopy(self.spec)
            change(spec)
            with self.subTest(spec=spec), patch("services.exam.spec_service.store.update_spec") as update:
                with self.assertRaises(ValueError):
                    SpecService.update_spec(spec)
                update.assert_not_called()

    def test_projects_ui_sidecar_outside_canonical(self):
        self.spec["material_id"] = "textbook-1"
        with patch("services.exam.spec_service.store.update_spec", return_value={}) as update:
            SpecService.update_spec(self.spec)
        canonical = update.call_args.args[0]
        self.assertNotIn("material_id", canonical)
        self.assertEqual(update.call_args.kwargs["sidecar"], {"material_id": "textbook-1"})

    def test_rejects_unlisted_capability(self):
        with self.assertRaisesRegex(ValueError, "unsupported capability"):
            validate_spec(self.spec, {"entries": []})


if __name__ == "__main__":
    unittest.main()
