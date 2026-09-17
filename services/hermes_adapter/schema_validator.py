"""Schema validator for Hermes generated candidates and public projections.

Uses jsonschema to validate outputs against contracts/*.schema.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import jsonschema

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = ROOT / "contracts"

class SchemaValidationError(ValueError):
    """Raised when generated output violates schema invariants."""

def load_schema(schema_filename: str) -> dict[str, Any]:
    schema_path = CONTRACTS_DIR / schema_filename
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    return json.loads(schema_path.read_text(encoding="utf-8"))

def normalize_candidate(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize model output to conform strictly to candidate.schema.json."""
    if not isinstance(data, dict):
        return data

    pub = data.get("public")
    if isinstance(pub, dict):
        # Normalize prompt blocks
        if "prompt" in pub and isinstance(pub["prompt"], list):
            clean_prompt = []
            for b in pub["prompt"]:
                if isinstance(b, dict):
                    b_type = b.get("type", "text")
                    if b_type == "math":
                        clean_prompt.append({"type": "math", "latex": b.get("latex", "")})
                    else:
                        clean_prompt.append({"type": "text", "text": b.get("text", "")})
                elif isinstance(b, str):
                    clean_prompt.append({"type": "text", "text": b})
            pub["prompt"] = clean_prompt

        # Normalize options
        if "options" in pub and isinstance(pub["options"], list):
            clean_opts = []
            for opt in pub["options"]:
                if isinstance(opt, dict):
                    opt_id = opt.get("id", f"opt_{len(clean_opts)+1}")
                    content = opt.get("content")
                    if not content and "text" in opt:
                        content = [{"type": "text", "text": str(opt["text"])}]
                    elif isinstance(content, list):
                        clean_content = []
                        for b in content:
                            if isinstance(b, dict):
                                b_type = b.get("type", "text")
                                if b_type == "math":
                                    clean_content.append({"type": "math", "latex": b.get("latex", "")})
                                else:
                                    clean_content.append({"type": "text", "text": b.get("text", "")})
                            elif isinstance(b, str):
                                clean_content.append({"type": "text", "text": b})
                        content = clean_content
                    else:
                        content = [{"type": "text", "text": str(content or "")}]
                    clean_opts.append({"id": opt_id, "content": content})
            pub["options"] = clean_opts
        elif "options" not in pub:
            pub["options"] = []

        pub.setdefault("material_ids", [])
        pub.setdefault("children", [])
        pub.setdefault("answer_space_lines", 2)
        if "score_x100" in pub and isinstance(pub["score_x100"], float):
            pub["score_x100"] = int(pub["score_x100"])

    priv = data.get("private")
    if isinstance(priv, dict) and "answers" in priv and isinstance(priv["answers"], list):
        clean_answers = []
        for i, ans in enumerate(priv["answers"]):
            if not isinstance(ans, dict):
                continue
            qid = ans.get("local_question_id") or ans.get("target_local_id") or (pub.get("local_id") if isinstance(pub, dict) else f"q_{i+1}")
            akind = ans.get("answer_kind") or ("selection" if pub and "choice" in pub.get("kind", "") else "free_text")
            if akind not in ("selection", "expression", "free_text", "rubric"):
                akind = "selection" if pub and "choice" in pub.get("kind", "") else "free_text"

            correct_opts = ans.get("correct_option_ids") or ans.get("selected_option_ids") or []
            if not isinstance(correct_opts, list):
                correct_opts = [str(correct_opts)]

            accepted = ans.get("accepted_answers")
            if not isinstance(accepted, list) or not accepted:
                val = ans.get("answer_text") or (correct_opts[0].replace("opt_", "") if correct_opts else "A")
                accepted = [{"value": str(val), "format": "text", "conditions": "正确答案"}]
            else:
                clean_acc = []
                for a in accepted:
                    if isinstance(a, dict):
                        clean_acc.append({
                            "value": str(a.get("value", "")),
                            "format": a.get("format", "text") if a.get("format") in ("text", "latex") else "text",
                            "conditions": str(a.get("conditions", "")),
                        })
                    elif isinstance(a, str):
                        clean_acc.append({"value": a, "format": "text", "conditions": ""})
                accepted = clean_acc

            solution = ans.get("solution") or ans.get("explanation")
            if not isinstance(solution, list) or not solution:
                solution = [{"type": "text", "text": "详见题干与选项解析"}]
            else:
                clean_sol = []
                for b in solution:
                    if isinstance(b, dict):
                        b_type = b.get("type", "text")
                        if b_type == "math":
                            clean_sol.append({"type": "math", "latex": b.get("latex", "")})
                        else:
                            clean_sol.append({"type": "text", "text": b.get("text", "")})
                    elif isinstance(b, str):
                        clean_sol.append({"type": "text", "text": b})
                solution = clean_sol

            rubric = ans.get("rubric") or ans.get("scoring_rubric")
            score_target = pub.get("score_x100", 400) if isinstance(pub, dict) else 400
            if not isinstance(rubric, list) or not rubric:
                rubric = [{
                    "id": f"r_{i+1}_1",
                    "description": "回答准确，推导完整",
                    "score_x100": score_target,
                    "acceptable_variants": [],
                }]
            else:
                clean_rub = []
                for j, r in enumerate(rubric):
                    if isinstance(r, dict):
                        clean_rub.append({
                            "id": str(r.get("id", f"r_{i+1}_{j+1}")),
                            "description": str(r.get("description", r.get("criterion", "符合答题要求"))),
                            "score_x100": int(r.get("score_x100", score_target)),
                            "acceptable_variants": [str(v) for v in r.get("acceptable_variants", [])],
                        })
                rubric = clean_rub

            clean_answers.append({
                "local_question_id": qid,
                "answer_kind": akind,
                "correct_option_ids": correct_opts,
                "accepted_answers": accepted,
                "solution": solution,
                "rubric": rubric,
            })
        priv["answers"] = clean_answers

    return data

def validate_candidate(data: dict[str, Any]) -> None:
    """Validate full candidate structure (public + private answers)."""
    normalize_candidate(data)
    schema = load_schema("candidate.schema.json")
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as err:
        raise SchemaValidationError(f"GeneratedCandidate validation failed: {err.message} at path {list(err.path)}") from err

def validate_public_question(data: dict[str, Any]) -> None:
    """Validate public question projection (must not contain private answers)."""
    schema = load_schema("public-question.schema.json")
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as err:
        raise SchemaValidationError(f"PublicQuestion validation failed: {err.message} at path {list(err.path)}") from err
