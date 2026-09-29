from __future__ import annotations
import base64
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from services.exam.template_parser import template_service
from ..store import store

router = APIRouter()


class TemplateParsePayload(BaseModel):
    filename: str = Field(..., description="Uploaded template filename, e.g. exam.docx")
    content_base64: str = Field(..., description="Base64 encoded content of the template file")
    force_llm: bool = Field(False, description="Legacy flag; AI template parsing is not yet connected through Hermes")





@router.post("/current/publish", status_code=201)
@router.post("/{exam_id}/publish", status_code=201)
def publish_exam(exam_id: str = "current", payload: Optional[dict[str, Any]] = None):
    raise HTTPException(status_code=501, detail="正式发布尚未接入当前生成版本、独立审批与真实排版产物；候选题不能直接发布。")


@router.post("/templates/parse")
def parse_template(payload: TemplateParsePayload):
    """Parse an uploaded exam template document (.docx or .txt) and extract its structure."""
    if not payload.filename or not payload.content_base64:
        raise HTTPException(status_code=400, detail="Missing filename or content_base64")
    if payload.force_llm:
        raise HTTPException(status_code=501, detail="AI 模板识别尚未接入 Hermes；请先使用结构识别并核对结果")

    raw_b64 = payload.content_base64.strip()
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    try:
        content_bytes = base64.b64decode(raw_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base64 content")

    try:
        result = template_service.parse_template(
            filename=payload.filename,
            content_bytes=content_bytes,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模板解析失败: {str(e)}")


