from __future__ import annotations
from typing import Any
from fastapi import APIRouter
from services.exam import QuestionService
from ..store import store

router = APIRouter()


@router.get("/current/validation")
@router.get("/{exam_id}/validation")
def get_validation(exam_id: str = "current"):
    return QuestionService.get_validation(exam_id)


@router.get("/current/adjudications")
@router.get("/{exam_id}/adjudications")
def get_adjudications(exam_id: str = "current"):
    return store.get_adjudications()


@router.post("/current/adjudications")
@router.post("/{exam_id}/adjudications")
def submit_adjudication(record: dict[str, Any], exam_id: str = "current"):
    store.submit_adjudication(record)
    return {"status": "SUCCESS"}


