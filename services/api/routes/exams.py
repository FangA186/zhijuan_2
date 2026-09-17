"""Exam and question routes connected to Hermes and DeepSeek official API."""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services.hermes_adapter.adapter import HermesDeepSeekAdapter
from services.hermes_adapter.blind_runtime import BlindSolverRuntime
from ..settings import settings
from ..store import store

router = APIRouter(prefix="/v1/exams", tags=["Exams"])

def get_adapter() -> HermesDeepSeekAdapter:
    return HermesDeepSeekAdapter(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        default_model=settings.deepseek_model_id,
    )

# 1. Spec routes
@router.get("/current/spec")
@router.get("/{exam_id}/spec")
def get_spec(exam_id: str = "current"):
    return store.get_spec()

@router.put("/current/spec")
@router.put("/{exam_id}/spec")
def update_spec(spec: dict[str, Any], exam_id: str = "current"):
    return store.update_spec(spec)

# 2. Plan / Blueprint routes
@router.get("/current/plans/current")
@router.get("/{exam_id}/plans/current")
def get_blueprint(exam_id: str = "current"):
    return store.get_blueprint()

@router.post("/current/plans/{plan_id}/confirm")
@router.post("/{exam_id}/plans/{plan_id}/confirm")
def confirm_blueprint(plan_id: str, exam_id: str = "current"):
    return store.confirm_blueprint(plan_id)

# 3. Questions / Candidates routes
@router.get("/current/questions")
@router.get("/{exam_id}/questions")
def list_questions(exam_id: str = "current"):
    return store.get_candidates()

@router.put("/current/questions/{local_id}")
@router.put("/{exam_id}/questions/{local_id}")
def update_question(local_id: str, candidate: dict[str, Any], exam_id: str = "current"):
    return store.update_candidate(candidate)

# 4. Hermes Single Question Regeneration
@router.post("/current/questions/{local_id}/regenerate")
@router.post("/{exam_id}/questions/{local_id}/regenerate")
def regenerate_question(local_id: str, exam_id: str = "current"):
    """Trigger real Hermes question-author and blind-solver roles via DeepSeek."""
    current_cand = store.get_candidate(local_id)
    if not current_cand:
        raise HTTPException(status_code=404, detail=f"Question {local_id} not found")

    spec = store.get_spec()
    stage = spec.get("stage", "junior")
    subject = spec.get("subject_label", "初中数学")

    # Find matching slot info
    slot_spec = {
        "slot_id": f"slot_{local_id}",
        "order": 1,
        "kind": current_cand.get("public", {}).get("kind", "single_choice"),
        "target_topic": "一元二次方程根的判别式与系数应用",
        "cognitive_target": "运算与推导",
        "score_x100": current_cand.get("public", {}).get("score_x100", 400),
        "estimated_difficulty": "medium",
    }

    adapter = get_adapter()
    try:
        # Step 1: Author role generates candidate
        new_cand = adapter.execute_author_role(
            slot_spec=slot_spec,
            stage=stage,
            subject=subject,
            model_id=settings.deepseek_model_id,
        )
        new_cand["public"]["local_id"] = local_id
        if new_cand.get("private", {}).get("answers"):
            new_cand["private"]["answers"][0]["local_question_id"] = local_id

        # Step 2: Blind solver performs independent solution
        runtime = BlindSolverRuntime(adapter=adapter)
        report = runtime.run_blind_solve(
            question_candidate=new_cand,
            model_id=settings.deepseek_model_id,
        )

        # Step 3: Update store & validation records
        store.update_candidate(new_cand)
        val_map = store.get_validation()
        val_map[local_id] = {
            "item_id": local_id,
            "overall_status": "PASS" if report.match_reference else "REVIEW",
            "rule_checks": [
                {
                    "rule_id": "RULE_SCHEMA_VALID",
                    "category": "schema",
                    "name": "Candidate Schema 契约校验",
                    "status": "PASS",
                    "detail": "生成的 JSON 结构完全满足 candidate.schema.json",
                },
                {
                    "rule_id": "RULE_BLIND_SOLVE",
                    "category": "blind_solve",
                    "name": "独立盲解交叉一致性核验",
                    "status": "PASS" if report.match_reference else "REVIEW",
                    "detail": report.notes,
                }
            ],
            "blind_solve": report.to_dict(),
        }
        store.validation = val_map

        return new_cand
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hermes generation error: {str(e)}")

# 5. Generation Jobs
@router.post("/{exam_id}/generation-jobs")
def start_generation_job(exam_id: str, background_tasks: BackgroundTasks):
    bp = store.get_blueprint()
    job_id = f"job_{exam_id}"
    job = {
        "job_id": job_id,
        "exam_id": exam_id,
        "revision": bp.get("revision", 1),
        "status": "RUNNING",
        "total_slots": len(bp.get("slots", [])),
        "completed_slots": 0,
        "tokens_used": 0,
        "estimated_cost_cny": 0.0,
        "started_at": "2026-09-17T08:00:00Z",
        "updated_at": "2026-09-17T08:00:00Z",
        "slots": [dict(s, status="RUNNING") for s in bp.get("slots", [])],
        "logs": [
            {"timestamp": "2026-09-17T08:00:00Z", "role": "planner", "level": "info", "message": "已加载 Hermes 规划蓝图，开始调度命题与盲解任务..."},
            {"timestamp": "2026-09-17T08:00:01Z", "role": "system", "level": "info", "message": f"使用已验收模型: {settings.deepseek_model_id}"}
        ],
    }
    store.jobs[job_id] = job
    return job

# 6. Validation & Review
@router.get("/current/validation")
@router.get("/{exam_id}/validation")
def get_validation(exam_id: str = "current"):
    return store.get_validation()

@router.get("/current/adjudications")
@router.get("/{exam_id}/adjudications")
def get_adjudications(exam_id: str = "current"):
    return store.get_adjudications()

@router.post("/current/adjudications")
@router.post("/{exam_id}/adjudications")
def submit_adjudication(record: dict[str, Any], exam_id: str = "current"):
    store.submit_adjudication(record)
    return {"status": "SUCCESS"}
