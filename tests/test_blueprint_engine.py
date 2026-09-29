"""Offline checks for canonical, immutable blueprint generation."""
import copy
import json
import unittest
from pathlib import Path

from services.blueprint.generator import BlueprintGenerator
from services.blueprint.rules import validate_score_balance


FIXTURE = Path(__file__).resolve().parents[1] / "acceptance/fixtures/minimum-primary.json"


class BlueprintTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.spec["taught_scope"]["scope_confirmed"] = True

    def test_five_slots_exact_score_and_scope(self):
        blueprint = BlueprintGenerator.generate(self.spec, spec_revision=7)
        self.assertEqual(blueprint["spec_revision"], 7)
        self.assertEqual([slot["slot_id"] for slot in blueprint["slots"]], [f"slot_{i:03d}" for i in range(1, 6)])
        self.assertEqual([slot["score_x100"] for slot in blueprint["slots"]], [300, 300, 200, 200, 1000])
        self.assertEqual(sum(slot["score_x100"] for slot in blueprint["slots"]), 2000)
        self.assertEqual({slot["target_topic"] for slot in blueprint["slots"]}, {"整数四则运算"})
        self.assertEqual(sum(blueprint["difficulty_distribution"].values()), 5)
        self.assertEqual(blueprint["canonical_spec"], self.spec)
        self.assertFalse(blueprint["confirmed"])
        self.assertEqual(len(blueprint["plan_hash"]), 64)

    def test_score_conflict_is_not_rounded_or_reassigned(self):
        spec = copy.deepcopy(self.spec)
        spec["total_score_x100"] = 2020
        self.assertEqual(validate_score_balance(spec["sections"], 2020), (False, 2000, 20))
        with self.assertRaisesRegex(ValueError, "sections score"):
            BlueprintGenerator.generate(spec)

    def test_section_topics_must_be_in_taught_scope(self):
        spec = copy.deepcopy(self.spec)
        spec["sections"][0]["topics"] = ["导数"]
        with self.assertRaises(ValueError):
            BlueprintGenerator.generate(spec)
        spec["sections"][0]["topics"] = ["范围外知识"]
        with self.assertRaisesRegex(ValueError, "exceeds taught_scope"):
            BlueprintGenerator.generate(spec)

    def test_hash_changes_with_spec_revision_and_content(self):
        first = BlueprintGenerator.generate(self.spec, spec_revision=1)
        second = BlueprintGenerator.generate(self.spec, spec_revision=2)
        self.assertNotEqual(first["plan_hash"], second["plan_hash"])
        changed = copy.deepcopy(self.spec)
        changed["title"] = "另一试卷"
        third = BlueprintGenerator.generate(changed, spec_revision=1)
        self.assertNotEqual(first["plan_hash"], third["plan_hash"])


if __name__ == "__main__":
    unittest.main()
