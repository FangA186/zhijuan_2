from __future__ import annotations

import hashlib
import copy
import json
from typing import Any

import jsonschema

from services.hermes_adapter.schema_validator import load_schema
from services.diagram_assets import diagram_asset_matches
from .scoring import scoring_errors, answer_text_conflicts
from .diversity import same_paper_check

CHECKER_ID = "candidate-deterministic"
CHECKER_VERSION = "7"


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k not in {"created_at", "updated_at", "checked_at"}}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def validate_candidate(candidate: dict, slot: dict, spec: dict, blind_report: Any = None, *, materials: Any = None, previous_questions=()) -> dict:
    """Check a candidate against its frozen slot. REVIEW means semantic proof is absent."""
    bound = {"candidate": candidate, "slot": slot, "spec": spec, "materials": materials,
             "checker_id": CHECKER_ID, "checker_version": CHECKER_VERSION, "previous_public_questions": previous_questions}
    raw = json.dumps(_stable(bound), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    content_hash = hashlib.sha256(raw.encode()).hexdigest()
    item_id = slot.get("slot_id") or candidate.get("public", {}).get("local_id", "unknown")
    revision = {key: slot.get(key, spec.get(key)) for key in
                ("spec_revision", "plan_revision", "question_revision_id")}
    checks = []

    def check(code: str, status: str, detail: str, *, manual: bool = False) -> None:
        checks.append({"rule_id": code, "check_code": code, "category": "deterministic" if code != "MATH_TRUTH" else "math_truth",
                       "name": code, "status": status, "severity": "major" if status == "FAIL" else "info",
                       "manual_allowed": manual, "evidence_summary": detail, "checker_id": CHECKER_ID,
                       "checker_version": CHECKER_VERSION, "evidence_type": "deterministic", "content_hash": content_hash})

    try:
        jsonschema.validate(candidate, load_schema("candidate.schema.json"))
    except jsonschema.ValidationError as exc:
        path = "/".join(str(p) for p in exc.absolute_path)
        check("STRUCTURE", "FAIL", f"Candidate schema invalid at {path or '<root>'}: {exc.validator}")
    except (TypeError, ValueError):
        check("STRUCTURE", "FAIL", "Candidate schema invalid: unsupported input type")
    else:
        check("STRUCTURE", "PASS", "Candidate matches approved schema")
        questions = []
        def collect(q: dict) -> None:
            questions.append(q)
            for child in q["children"]:
                collect(child)
        collect(candidate["public"])
        leaves = [q for q in questions if q["kind"] != "material_group"]
        answers = candidate["private"]["answers"]
        qids = [q["local_id"] for q in questions]
        aids = [a["local_question_id"] for a in answers]
        valid = len(qids) == len(set(qids)) and sorted(aids) == sorted(q["local_id"] for q in leaves)
        scoring_details, conflicts = [], []
        for q in leaves:
            a = next((a for a in answers if a["local_question_id"] == q["local_id"]), None)
            if a is None:
                continue
            opts = [o["id"] for o in q["options"]]
            selected = a["correct_option_ids"]
            valid &= len(opts) == len(set(opts)) and len(selected) == len(set(selected))
            valid &= set(selected) <= set(opts)
            if q["kind"] in ("single_choice", "true_false"):
                valid &= a["answer_kind"] == "selection" and len(selected) == 1
            elif q["kind"] == "multiple_choice":
                valid &= a["answer_kind"] == "selection" and len(selected) >= 2
            else:
                valid &= not selected and a["answer_kind"] != "selection"
            scoring_details.extend(scoring_errors(q, a, spec))
            conflicts.extend(answer_text_conflicts(q, a))
            valid &= len({r["id"] for r in a["rubric"]}) == len(a["rubric"])
        check("ANSWER_AND_RUBRIC", "PASS" if valid and not scoring_details else "FAIL",
              "；".join(scoring_details) or "Answer references, option IDs, cardinality and rubric totals checked")
        check("ANSWER_TEXT_CONSISTENCY", "FAIL" if conflicts else "PASS",
              "；".join(conflicts) or "No conflicting explicit option declaration detected; not a semantic proof")
        total = sum(q["score_x100"] for q in leaves)
        slot_score = slot.get("score_x100")
        slot_ok = candidate["public"]["kind"] == slot.get("kind") and total == slot_score
        material = slot.get("material_id")
        if material:
            slot_ok &= material in candidate["public"]["material_ids"]
        check("SLOT", "PASS" if slot_ok else "FAIL", f"Leaf score {total}; slot score {slot_score}; kind/material checked")
        blocks = [block for q in questions for block in q["prompt"]]
        blocks.extend(block for q in questions for option in q["options"] for block in option["content"])
        blocks.extend(block for answer in answers for block in answer["solution"])
        unresolved = [block.get("asset_id", "unmaterialized") for block in blocks
                      if block["type"] == "diagram" or
                      (block["type"] == "asset" and
                       not diagram_asset_matches(block["asset_id"], block["alt"]))]
        check("ASSET_INTEGRITY", "FAIL" if unresolved else "PASS",
              f"{len(unresolved)} missing, corrupt, or untrusted diagram assets; local assets checked")
    if previous_questions:
        diversity_status, detail = same_paper_check(candidate.get("public", {}), previous_questions)
        check("IN_PAPER_DIVERSITY", diversity_status, detail, manual=diversity_status == "REVIEW")
    check("MATH_TRUTH", "REVIEW", "No trusted mathematical proof or supported AST verification supplied", manual=True)
    if hasattr(blind_report, "to_dict"):
        blind_report = blind_report.to_dict()
    if isinstance(blind_report, dict):
        same = blind_report.get("is_same_model")
        match = blind_report.get("match_reference")
        model = blind_report.get("model_id")
        detail = f"Blind comparison reported {'agreement' if match is True else 'disagreement' if match is False else 'unknown'}; " \
                 f"{'SAME_MODEL' if same is True else 'model relationship unknown'}; model={str(model)[:80] if model else 'unknown'}; not proof"
    else:
        detail = "Blind comparison missing or unsupported; requires review"
    check("BLIND_COMPARISON", "REVIEW", detail, manual=True)
    checks[-1]["evidence_type"] = "model"
    checks[-1]["category"] = "model_comparison"
    overall = "FAIL" if any(c["status"] == "FAIL" for c in checks) else "REVIEW"
    record = {"item_id": item_id, "overall_status": overall, "rule_checks": checks,
              "content_hash": content_hash, "revision": revision, "checker_id": CHECKER_ID,
              "checker_version": CHECKER_VERSION, "evidence_type": "deterministic",
              "blind_evidence": copy.deepcopy(blind_report)}
    # Content identity remains stable; evidence integrity additionally binds the blind result.
    record["evidence_hash"] = hashlib.sha256(json.dumps(_stable(record), ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return record
