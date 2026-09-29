"""Vocabulary image upload and serving routes."""
from __future__ import annotations
import base64
import re
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from ...curriculum import curriculum_service

router = APIRouter()
CUSTOM_VOCAB_DIR = Path(__file__).resolve().parents[3] / "uploads" / "custom_vocab"
CUSTOM_VOCAB_DIR.mkdir(parents=True, exist_ok=True)


class VocabUploadPayload(BaseModel):
    filename: str = Field(..., description="Original image filename, e.g. page1.jpg")
    content_base64: str = Field(..., description="Base64 encoded image content (may contain data:image/...;base64, prefix)")



def _detect_image_type(data: bytes) -> tuple[str, str]:
    """Detect image type from magic bytes. Returns (media_type, ext)."""
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return ("image/jpeg", ".jpg")
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return ("image/png", ".png")
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ("image/webp", ".webp")
    raise HTTPException(
        status_code=400,
        detail="Unsupported or invalid image format. Supported formats: JPEG, PNG, WEBP.",
    )



@router.get("/materials/{material_id}/vocab/images/{filename}")
def get_material_vocab_image(material_id: str, filename: str):
    """Serve a cleaned high-definition vocabulary page image."""
    img_file = curriculum_service.get_vocab_image_file(material_id, filename)
    if not img_file or not img_file.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Vocabulary image '{filename}' for textbook {material_id} not found.",
        )
    return FileResponse(
        img_file,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/vocab/upload")
def upload_vocab_image(payload: VocabUploadPayload):
    """Upload a custom vocabulary page image (Base64 JSON)."""
    if not payload.filename or not payload.content_base64:
        raise HTTPException(status_code=400, detail="Missing filename or content_base64")

    raw_b64 = payload.content_base64.strip()
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Base64 encoding in content_base64")

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Image content cannot be empty")

    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size exceeds 15MB limit")

    media_type, ext = _detect_image_type(image_bytes)

    # Clean filename and generate safe unique target
    clean_stem = re.sub(r"[^\w\.-]", "_", Path(payload.filename).stem)
    if not clean_stem:
        clean_stem = "custom_page"
    safe_name = f"custom_{int(time.time())}_{uuid.uuid4().hex[:8]}_{clean_stem}{ext}"
    target_path = CUSTOM_VOCAB_DIR / safe_name
    target_path.write_bytes(image_bytes)

    return {
        "filename": safe_name,
        "original_filename": payload.filename,
        "page_num": 1,
        "order": 1,
        "rel_path": f"custom/{safe_name}",
        "url": f"/v1/curriculum/vocab/custom-images/{safe_name}",
        "size_bytes": len(image_bytes),
        "mime_type": media_type,
    }


@router.get("/vocab/custom-images/{filename}")
def get_custom_vocab_image(filename: str):
    """Serve an uploaded custom vocabulary page image."""
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = (CUSTOM_VOCAB_DIR / filename).resolve()
    if not file_path.is_file() or file_path.parent != CUSTOM_VOCAB_DIR.resolve():
        raise HTTPException(status_code=404, detail="Custom image not found")

    ext = file_path.suffix.lower()
    media_type = "image/jpeg"
    if ext == ".png":
        media_type = "image/png"
    elif ext == ".webp":
        media_type = "image/webp"

    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )


