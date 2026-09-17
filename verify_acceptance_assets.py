"""Offline checks of acceptance MATERIALS, not application/MVP acceptance.

This script performs no network calls, model calls, container startup or E2E tests.
It must never change any case status from NOT_RUN to PASS.
"""
from pathlib import Path
from typing import Any
import json
import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
STAGES = {"primary", "junior", "senior"}

def load(relative: str) -> Any:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text) if path.suffix in (".yaml", ".yml") else json.loads(text)

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def validate_assets() -> dict[str, Any]:
    minimum = load("acceptance/minimum-cases.yaml")["cases"]
    full = load("acceptance/full-cases.yaml")["cases"]
    expected_min = {f"MIN-{i:02d}" for i in range(1, 13)} | {f"MIN-N{i:02d}" for i in range(1, 8)}
    expected_full = {f"FULL-{i:02d}" for i in range(1, 29)}
    require({c["id"] for c in minimum} == expected_min and len(minimum) == 19, "Invalid minimum case inventory")
    require({c["id"] for c in full} == expected_full and len(full) == 28, "Invalid full case inventory")
    all_cases = minimum + full
    for case in all_cases:
        require(case["status"] == "NOT_RUN", f"Template falsely claims execution: {case['id']}")
        require(case["automation_implemented"] is False, "Specification must not claim E2E implementation")
        require(set(case["school_stages"]) == STAGES, "Missing school stage")
        require(case["actual_result"] is None and case["executed_at"] is None and not case["evidence_refs"], "Execution evidence must remain blank")
        for key in ("preconditions", "steps", "expected_results", "evidence_required", "owners"):
            require(bool(case[key]), f"Incomplete case {case['id']}: {key}")
    schema = load("contracts/exam-spec.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for stage in sorted(STAGES):
        spec = load(f"acceptance/fixtures/minimum-{stage}.json")
        validator.validate(spec)
        require(spec["stage"] == stage, "Stage mismatch")
        require(spec["taught_scope"]["scope_confirmed"] is False, "Fixture must await teacher scope confirmation")
        require(sum(s["count"] for s in spec["sections"]) == 5, "Fixture must have 5 questions")
        require(sum(s["count"] * s["score_each_x100"] for s in spec["sections"]) == spec["total_score_x100"] == 2000, "Fixture must total 20 points")
        require(not spec["provided_materials"], "Smoke fixture must not embed preset reference questions")
    status = load("acceptance/current-delivery-status.json")
    for field in ("application_runnable", "hermes_source_included", "hermes_installed", "live_deepseek_called", "real_exam_export_pipeline_implemented"):
        require(status[field] is False, f"Unsubstantiated implementation claim: {field}")
    require(status["minimum_acceptance_status"] == status["full_acceptance_status"] == "NOT_RUN", "Do not conflate local checks with acceptance")
    evidence = load("acceptance/evidence-manifest.template.json")
    require(evidence["template_only"] and evidence["overall_status"] == "NOT_RUN", "Evidence template status is invalid")
    require(evidence["run_id"] is None and not evidence["artifacts"] and not evidence["signoffs"], "Do not create fake evidence")
    plan = load("acceptance/mvp-plan.yaml")
    require([x["id"] for x in plan["phases"]] == ["M0", "M1", "M2", "M3"], "Phase order invalid")
    require(plan["scope"]["provider"] == "deepseek" and plan["scope"]["agent_framework"] == "hermes", "Technology scope drift")
    require(all(plan["scope"][x] is False for x in ("question_bank", "langchain", "langgraph", "history_retrieval")), "Scope drift")
    master = (ROOT / "deliverables/zhijuan_product_development_v1_3.md").read_text(encoding="utf-8")
    section = (ROOT / "docs/07_MVP阶段_验收链路_交付效果.md").read_text(encoding="utf-8")
    require(section in master, "Themed acceptance document must match master source")
    for case in all_cases:
        require(case["id"] in master, f"Missing case in master: {case['id']}")
    return {"result": "PASS", "scope": "offline_acceptance_material_consistency_only", "case_definitions": 47, "minimum_cases": 19, "full_cases": 28, "input_fixtures": 3, "live_model_executed": False, "g_min": "NOT_RUN", "g_full": "NOT_RUN"}

if __name__ == "__main__":
    result = validate_assets()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("NOT RUN: application startup, live Hermes/DeepSeek, generated-exam quality, G-MIN, G-FULL.")
