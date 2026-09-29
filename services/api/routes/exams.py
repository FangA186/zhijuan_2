"""Exam API router; endpoint implementations are grouped by workflow."""
from __future__ import annotations
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from services.exam import GenerationJobService, QuestionService
from services.exam.job_service import AcceptError
from ..health import generation_configuration
from ..store import store
from .exam_route_helpers import current_exam_only, require_revision
from .exam_setup_routes import (
    router as _setup_router, get_spec, update_spec, get_blueprint, generate_blueprint, confirm_blueprint,
)
from .exam_question_routes import (
    router as _question_router, get_current_asset, list_questions, update_question,
    regenerate_question, regenerate_slot,
)
from .exam_job_routes import (
    router as _job_router, get_current_generation_job, stream_generation_job, step_generation_job,
    pause_generation_job, resume_generation_job, cancel_generation_job,
)
from .exam_review_routes import (
    router as _review_router, get_validation, get_adjudications, submit_adjudication,
)
from .exam_history_routes import (
    router as _history_router, TemplateParsePayload, publish_exam, parse_template,
    template_service,
)

router = APIRouter(prefix="/v1/exams", tags=["Exams"], dependencies=[Depends(current_exam_only)])
router.include_router(_setup_router)
router.include_router(_question_router)


@router.post("/current/generation-jobs", status_code=202)
@router.post("/{exam_id}/generation-jobs", status_code=202)
def start_generation_job(exam_id: str = "current", if_match: str | None = Header(None)):
    """Admit a confirmed job without running model work on the HTTP thread."""
    require_revision(if_match)
    if not generation_configuration()["configured"]:
        raise HTTPException(status_code=503, detail="生成服务尚未配置完整，可先编辑配置和预览计划，暂不能开始出题")
    try:
        return GenerationJobService.accept_job(exam_id)
    except AcceptError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.body)
    except Exception:
        raise HTTPException(status_code=500, detail="开始命题时发生内部错误，请稍后重试")


from .exam_activity_routes import router as _activity_router
router.include_router(_activity_router)
router.include_router(_job_router)
router.include_router(_review_router)


@router.get("")
@router.get("/")
def list_exams(limit: int = 20, cursor: Optional[str] = None):
    """List published records and drafts for the organization."""
    items = store.list_exams()
    return {"items": items[:limit], "total": len(items), "cursor": None}


router.include_router(_history_router)

from .planning_routes import router as _planning_router
router.include_router(_planning_router)
