from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from services.exam import GenerationJobService

router = APIRouter()


@router.get("/current/generation-jobs/current")
@router.get("/{exam_id}/generation-jobs/current")
def get_current_generation_job(exam_id: str = "current"):
    """Get active generation job status and event logs."""
    try:
        job = GenerationJobService.get_current_job(exam_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Generation infrastructure is not configured") from exc
    if not job:
        raise HTTPException(status_code=404, detail="No generation job found")
    return job


@router.get("/current/generation-jobs/stream")
@router.get("/{exam_id}/generation-jobs/stream")
async def stream_generation_job(exam_id: str = "current"):
    """Public progress SSE; answer-bearing output is restricted to the local activity route."""
    return StreamingResponse(
        GenerationJobService.stream_job_events(exam_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/current/generation-jobs/current/step")
@router.post("/{exam_id}/generation-jobs/current/step")
def step_generation_job(exam_id: str = "current", slot_id: Optional[str] = None):
    """Step the pipeline state machine forward by one slot phase."""
    try:
        return GenerationJobService.step_job(exam_id=exam_id, slot_id=slot_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/current/generation-jobs/current/pause")
@router.post("/{exam_id}/generation-jobs/current/pause")
def pause_generation_job(exam_id: str = "current"):
    try:
        return GenerationJobService.pause_job(exam_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/current/generation-jobs/current/resume")
@router.post("/{exam_id}/generation-jobs/current/resume")
def resume_generation_job(exam_id: str = "current"):
    try:
        return GenerationJobService.resume_job(exam_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/current/generation-jobs/current/cancel")
@router.post("/{exam_id}/generation-jobs/current/cancel")
def cancel_generation_job(exam_id: str = "current"):
    try:
        return GenerationJobService.cancel_job(exam_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


