from __future__ import annotations
from fastapi import HTTPException
from ..store import store


def current_exam_only(exam_id: str = "current"):
    if exam_id != "current":
        raise HTTPException(status_code=404, detail="Only the current local draft is configured")


def require_revision(if_match: str | None) -> int:
    if not if_match:
        raise HTTPException(status_code=428, detail="If-Match is required; reload the specification")
    revision = store.get_spec_revision()
    if if_match != f'"{revision}"':
        raise HTTPException(status_code=412, detail="Specification changed; reload before editing")
    return revision
