"""Curriculum and Textbook routes delegating to Curriculum domain service."""
from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

from ...curriculum import curriculum_service, CurriculumFilter
from .vocab_image_routes import (
    router as _vocab_image_router, CUSTOM_VOCAB_DIR, VocabUploadPayload, _detect_image_type,
    get_material_vocab_image, upload_vocab_image, get_custom_vocab_image,
)

router = APIRouter(prefix="/v1/curriculum", tags=["Curriculum"])







@router.get("/tags")
def get_tags():
    """Get the full classification hierarchy tag tree from SmartEdu."""
    return curriculum_service.get_tags()


@router.get("/materials")
def list_materials(
    mode: str = Query("visible", description="Filter mode: 'visible' (official ~1727) or 'all' (full 3209)"),
    stage: Optional[str] = Query(None, description="Stage tag name or ID, e.g. '高中'"),
    grade: Optional[str] = Query(None, description="Grade tag name or ID, e.g. '高一', '九年级'"),
    subject: Optional[str] = Query(None, description="Subject tag name or ID, e.g. '数学'"),
    edition: Optional[str] = Query(None, description="Edition tag name or ID, e.g. '人教A版'"),
    term: Optional[str] = Query(None, description="Term tag name or ID, e.g. '必修 第一册'"),
    q: Optional[str] = Query(None, description="Keyword search in title"),
    limit: Optional[int] = Query(None, description="Limit returned items (default all matching)"),
):
    """List or search teaching materials with multi-dimensional cascading filters."""
    filter_params = CurriculumFilter(
        mode=mode,
        stage=stage,
        grade=grade,
        subject=subject,
        edition=edition,
        term=term,
        q=q,
        limit=limit,
    )
    result = curriculum_service.search_materials(filter_params)
    return result.to_dict()


@router.get("/materials/{material_id}")
def get_material(material_id: str):
    """Get single material metadata and details."""
    mat_info = curriculum_service.get_material(material_id)
    if not mat_info:
        raise HTTPException(status_code=404, detail=f"Textbook {material_id} not found")
    return mat_info


@router.get("/materials/{material_id}/tree")
def get_material_chapter_tree(material_id: str):
    """Get complete chapter catalog tree for a textbook."""
    chapters = curriculum_service.get_chapter_tree(material_id)
    if chapters is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chapter tree for textbook {material_id} not found",
        )
    return {
        "material_id": material_id,
        "chapters": chapters,
    }


@router.get("/covers/{material_id}.jpg")
def get_material_cover(material_id: str):
    """Serve downloaded cover jpg or fallback to CDN thumbnail."""
    cover_file = curriculum_service.get_cover_file(material_id)
    if cover_file and cover_file.is_file():
        return FileResponse(cover_file, media_type="image/jpeg")

    thumb_url = curriculum_service.get_cover_fallback_url(material_id)
    if thumb_url:
        return RedirectResponse(url=thumb_url)

    raise HTTPException(status_code=404, detail="Cover not found")


@router.get("/materials/{material_id}/vocab")
def get_material_vocab(material_id: str):
    """Get textbook vocabulary metadata, page range, and clean image URLs."""
    vocab_info = curriculum_service.get_material_vocab(material_id)
    if not vocab_info:
        raise HTTPException(
            status_code=404,
            detail=f"Vocabulary data for textbook {material_id} not found or not an English textbook.",
        )
    return vocab_info

router.include_router(_vocab_image_router)
