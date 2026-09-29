from __future__ import annotations
import logging
from typing import Any
from fastapi import APIRouter, HTTPException, Response
from services.exam import QuestionService
from services.diagram_assets import diagram_asset_matches, load_diagram
from ..store import store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/current/assets/{asset_id}")
def get_current_asset(asset_id: str):
    def reference(question: Any) -> dict | None:
        if not isinstance(question, dict):
            return None
        blocks = list(question.get("prompt", []))
        blocks.extend(block for option in question.get("options", []) if isinstance(option, dict)
                      for block in option.get("content", []))
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "asset" and block.get("asset_id") == asset_id:
                return block
        return next((found for child in question.get("children", [])
                     if (found := reference(child)) is not None), None)

    asset = next((found for candidate in QuestionService.list_candidates("current")
                  if isinstance(candidate, dict)
                  and (found := reference(candidate.get("public"))) is not None), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="Diagram asset is not part of the current paper")
    if not diagram_asset_matches(asset_id, asset.get("alt")):
        raise HTTPException(status_code=404, detail="Diagram asset is missing, corrupt, or unsupported")
    data = load_diagram(asset_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Diagram asset is missing, corrupt, or unsupported")
    return Response(content=data, media_type="image/svg+xml",
                    headers={"Content-Security-Policy": "sandbox; default-src 'none'",
                             "X-Content-Type-Options": "nosniff",
                             "Cache-Control": "private, max-age=3600"})


@router.get("/current/questions")
@router.get("/{exam_id}/questions")
def list_questions(exam_id: str = "current"):
    return QuestionService.list_candidates(exam_id)


@router.put("/current/questions/{local_id}")
@router.put("/{exam_id}/questions/{local_id}")
def update_question(local_id: str, candidate: dict[str, Any], exam_id: str = "current"):
    if candidate.get("public", {}).get("local_id") != local_id:
        raise HTTPException(status_code=422, detail="Question ID mismatch")
    try:
        return QuestionService.update_candidate(candidate, exam_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/current/questions/{local_id}/regenerate")
@router.post("/{exam_id}/questions/{local_id}/regenerate")
def regenerate_question(local_id: str, exam_id: str = "current"):
    """Trigger real Hermes question-author and blind-solver roles based on target BlueprintSlot."""
    try:
        return QuestionService.regenerate_question_slot(local_id, exam_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Hermes generation error for question %s", local_id)
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试")


@router.post("/current/slots/{slot_id}/regenerate")
@router.post("/{exam_id}/slots/{slot_id}/regenerate")
def regenerate_slot(slot_id: str, exam_id: str = "current"):
    """Regenerate candidate item for a specific blueprint slot."""
    # Find local_id from slot_id (e.g. slot_q01 -> q01)
    local_id = slot_id.replace("slot_", "")
    try:
        return QuestionService.regenerate_question_slot(local_id, exam_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Hermes slot generation error for slot %s", slot_id)
        raise HTTPException(status_code=500, detail="生成失败，请稍后重试")


