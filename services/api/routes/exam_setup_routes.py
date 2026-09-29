from __future__ import annotations
import logging
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Header, Response
from services.exam import SpecService, BlueprintService
from ..store import store
from .exam_route_helpers import require_revision

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/current/spec")
@router.get("/{exam_id}/spec")
def get_spec(response: Response, exam_id: str = "current"):
    result = SpecService.get_spec(exam_id)
    response.headers["ETag"] = f'"{store.get_spec_revision()}"'
    return result


@router.put("/current/spec")
@router.put("/{exam_id}/spec")
def update_spec(spec: dict[str, Any], response: Response, exam_id: str = "current", if_match: str | None = Header(None)):
    revision = require_revision(if_match)
    try:
        result = SpecService.update_spec(spec, exam_id, expected_revision=revision)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.headers["ETag"] = f'"{store.get_spec_revision()}"'
    return result


@router.get("/current/plans/current")
@router.get("/{exam_id}/plans/current")
def get_blueprint(exam_id: str = "current"):
    return BlueprintService.get_blueprint(exam_id)


@router.post("/current/plans/generate")
@router.post("/{exam_id}/plans/generate")
def generate_blueprint(exam_id: str = "current", spec: Optional[dict[str, Any]] = None, if_match: str | None = Header(None)):
    revision = require_revision(if_match)
    """Deprecated rule-only entry; paid planning uses durable planning-jobs."""
    try:
        return BlueprintService.generate_blueprint(exam_id=exam_id, spec_override=spec, expected_revision=revision)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Blueprint generation failed")
        raise HTTPException(status_code=500, detail="生成蓝图失败，请稍后重试")


@router.post("/current/plans/{plan_id}/confirm")
@router.post("/{exam_id}/plans/{plan_id}/confirm")
def confirm_blueprint(plan_id: str, exam_id: str = "current", if_match: str | None = Header(None)):
    revision = require_revision(if_match)
    try:
        return BlueprintService.confirm_blueprint(plan_id, exam_id, expected_revision=revision)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


