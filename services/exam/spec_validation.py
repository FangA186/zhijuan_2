"""Validation at the ExamSpec trust boundary, before planning or model work."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts" / "exam-spec.schema.json"
VALIDATOR = Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
STAGE_YEARS = {"primary": range(1, 7), "junior": range(1, 4), "senior": range(1, 4)}


def validate_spec(spec: dict[str, Any], capabilities: dict[str, Any] | None = None, *, require_scope_confirmation: bool = False) -> None:
    """Reject invalid or unsupported requests; no implicit score correction."""
    errors = sorted(VALIDATOR.iter_errors(spec), key=lambda error: (list(map(str, error.path)), error.message))
    if errors:
        error = errors[0]
        location = ".".join(map(str, error.path)) or "spec"
        raise ValueError(f"{location}: {error.message}")

    if spec["stage_year"] not in STAGE_YEARS[spec["stage"]]:
        raise ValueError("stage_year does not belong to stage")
    if require_scope_confirmation and not spec["taught_scope"]["scope_confirmed"]:
        raise ValueError("taught_scope.scope_confirmed must be true before saving a generation-ready specification")
    if any(not material["rights_confirmed"] for material in spec.get("provided_materials", [])):
        raise ValueError("provided_materials rights must be confirmed")
    excluded = set(spec["taught_scope"]["excluded_topics"])
    if excluded.intersection(spec["taught_scope"]["topics"]):
        raise ValueError("taught_scope.topics overlaps excluded_topics")
    if sum(spec["difficulty_distribution"].values()) != 100:
        raise ValueError("difficulty_distribution must total 100")
    section_ids = [section["id"] for section in spec["sections"]]
    if len(section_ids) != len(set(section_ids)):
        raise ValueError("sections.id must be unique")
    actual = sum(section["count"] * section["score_each_x100"] for section in spec["sections"])
    if actual != spec["total_score_x100"]:
        raise ValueError(f"sections score {actual} does not equal total_score_x100 {spec['total_score_x100']}")
    partial = spec.get("multiple_choice_partial_score_x100", 0)
    for section in spec["sections"]:
        if section["question_type"] == "multiple_choice" and partial >= section["score_each_x100"]:
            raise ValueError("多选题少选得分必须小于每题满分")
        if excluded.intersection(section["topics"]):
            raise ValueError(f"sections.{section['id']}.topics includes an excluded topic")

    if capabilities is not None:
        entries = capabilities.get("entries", [])
        for section in spec["sections"]:
            matching = [entry for entry in entries if (entry.get("stage"), entry.get("subject_code"), entry.get("question_type")) == (spec["stage"], spec["subject_code"], section["question_type"])]
            if not matching or any(entry.get("generation") != "READY" for entry in matching):
                raise ValueError(f"unsupported capability: {spec['stage']}/{spec['subject_code']}/{section['question_type']}")
