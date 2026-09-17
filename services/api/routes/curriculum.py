"""Curriculum and Textbook routes based on SmartEdu crawled dataset (3209 textbooks)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse

router = APIRouter(prefix="/v1/curriculum", tags=["Curriculum"])

# Locate smartedu_data
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SMARTEDU_DIR = WORKSPACE_ROOT / "smartedu_data"
TAGS_FILE = SMARTEDU_DIR / "1_tags" / "national_lesson_tag.json"
MATS_FILE = SMARTEDU_DIR / "2_materials_list" / "all_materials.json"
DETAILS_DIR = SMARTEDU_DIR / "3_details"
TREES_DIR = SMARTEDU_DIR / "4_trees"
COVERS_DIR = SMARTEDU_DIR / "covers"

# Cache
_CACHED_TAGS: dict[str, Any] = {}
_CACHED_MATERIALS: list[dict[str, Any]] = []
_MATERIAL_MAP: dict[str, dict[str, Any]] = {}
_TAG_NAME_MAP: dict[str, str] = {}


def _build_tag_map(node: dict[str, Any]) -> None:
    if not node:
        return
    tag_id = node.get("tag_id")
    tag_name = node.get("tag_name")
    if tag_id and tag_name:
        _TAG_NAME_MAP[tag_id] = tag_name
    for h in node.get("hierarchies") or []:
        for c in h.get("children") or []:
            _build_tag_map(c)


def _compute_visibility(mat: dict[str, Any], tags_root: dict[str, Any]) -> tuple[bool, str, str]:
    tag_id_set = set(mat.get("tag_ids") or [t.get("tag_id") for t in mat.get("tag_list", []) if t.get("tag_id")])
    curr = tags_root
    while curr:
        hierarchies = curr.get("hierarchies") or []
        if not hierarchies:
            return True, "官网公开开放", "OPEN"

        matched_child = None
        for h in hierarchies:
            hidden_tags = (h.get("ext") or {}).get("hidden_tags") or []
            dim_name = h.get("hierarchy_name") or "维度"
            for hid in hidden_tags:
                if hid in tag_id_set:
                    tag_name = _TAG_NAME_MAP.get(hid, "对应选项")
                    return False, f"维度【{dim_name}】中的【{tag_name}】被官网前端设为 hidden_tags 屏蔽", "HIDDEN_TAG"

            for child in (h.get("children") or []):
                if child.get("tag_id") in tag_id_set:
                    matched_child = child
                    break
            if matched_child:
                break

        if not matched_child:
            first_h = hierarchies[0] if hierarchies else {}
            exp_dim = first_h.get("hierarchy_name", "维度")
            return False, f"官网前台标签树未开放【{exp_dim}】导航节点", "NOT_IN_TREE"

        curr = matched_child

    return True, "官网公开开放", "OPEN"


def _load_data() -> None:
    global _CACHED_TAGS, _CACHED_MATERIALS, _MATERIAL_MAP
    if _CACHED_MATERIALS:
        return

    if TAGS_FILE.is_file():
        with open(TAGS_FILE, "r", encoding="utf-8") as f:
            _CACHED_TAGS = json.load(f)
        _build_tag_map(_CACHED_TAGS)

    if MATS_FILE.is_file():
        with open(MATS_FILE, "r", encoding="utf-8") as f:
            raw_mats = json.load(f)

        for m in raw_mats:
            mat_id = m.get("id")
            # Build dimension dictionary
            dims = {}
            tag_ids = set()
            for t in m.get("tag_list") or []:
                tid = t.get("tag_id")
                dim_id = t.get("tag_dimension_id")
                tname = t.get("tag_name")
                if tid:
                    tag_ids.add(tid)
                if dim_id and tid and tname:
                    dims[dim_id] = {"id": tid, "name": tname}

            m["tag_ids"] = list(tag_ids)
            m["dims"] = dims
            thumbs = (m.get("custom_properties") or {}).get("thumbnails") or []
            m["thumb"] = thumbs[0] if thumbs else ""

            is_vis, reason, code = _compute_visibility(m, _CACHED_TAGS)
            m["isVisible"] = is_vis
            m["visReason"] = reason
            m["visCode"] = code

            _CACHED_MATERIALS.append(m)
            if mat_id:
                _MATERIAL_MAP[mat_id] = m


_load_data()


@router.get("/tags")
def get_tags():
    """Get the full classification hierarchy tag tree from SmartEdu."""
    _load_data()
    return _CACHED_TAGS


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
    _load_data()
    results = _CACHED_MATERIALS

    if mode == "visible":
        results = [m for m in results if m.get("isVisible")]

    if stage:
        results = [
            m for m in results
            if m.get("dims", {}).get("zxxxd", {}).get("id") == stage
            or m.get("dims", {}).get("zxxxd", {}).get("name") == stage
        ]

    # Notice: For high school, grade is ignored so modular textbooks aren't filtered out
    if grade:
        results = [
            m for m in results
            if m.get("dims", {}).get("zxxnj", {}).get("id") == grade
            or m.get("dims", {}).get("zxxnj", {}).get("name") == grade
        ]

    if subject:
        results = [
            m for m in results
            if m.get("dims", {}).get("zxxxk", {}).get("id") == subject
            or m.get("dims", {}).get("zxxxk", {}).get("name") == subject
        ]

    if edition:
        results = [
            m for m in results
            if m.get("dims", {}).get("zxxbb", {}).get("id") == edition
            or m.get("dims", {}).get("zxxbb", {}).get("name") == edition
        ]

    if term:
        results = [
            m for m in results
            if (m.get("dims", {}).get("zxxcc", {}).get("id") == term
                or m.get("dims", {}).get("zxxcc", {}).get("name") == term
                or m.get("dims", {}).get("zxxnj", {}).get("id") == term
                or m.get("dims", {}).get("zxxnj", {}).get("name") == term)
        ]

    if q and q.strip():
        k = "".join(q.strip().lower().split())
        results = [m for m in results if k in "".join(m.get("title", "").lower().split())]

    total = len(results)
    items = results if limit is None else results[:limit]

    return {
        "total": total,
        "mode": mode,
        "count": len(items),
        "items": items,
    }


@router.get("/materials/{material_id}")
def get_material(material_id: str):
    """Get single material metadata and details."""
    _load_data()
    mat = _MATERIAL_MAP.get(material_id)
    if not mat:
        raise HTTPException(status_code=404, detail=f"Textbook {material_id} not found")

    detail_path = DETAILS_DIR / f"{material_id}.json"
    details = {}
    if detail_path.is_file():
        try:
            with open(detail_path, "r", encoding="utf-8") as f:
                details = json.load(f)
        except Exception:
            pass

    return {
        "summary": mat,
        "details": details,
    }


@router.get("/materials/{material_id}/tree")
def get_material_chapter_tree(material_id: str):
    """Get complete chapter catalog tree (trees/{id}.json) for a textbook."""
    tree_path = TREES_DIR / f"{material_id}.json"
    if not tree_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Chapter tree for textbook {material_id} not found",
        )

    with open(tree_path, "r", encoding="utf-8") as f:
        chapters = json.load(f)

    return {
        "material_id": material_id,
        "chapters": chapters,
    }


@router.get("/covers/{material_id}.jpg")
def get_material_cover(material_id: str):
    """Serve downloaded cover jpg or fallback to CDN thumbnail."""
    cover_file = COVERS_DIR / f"{material_id}.jpg"
    if cover_file.is_file():
        return FileResponse(cover_file, media_type="image/jpeg")

    _load_data()
    mat = _MATERIAL_MAP.get(material_id)
    if mat and mat.get("thumb"):
        return RedirectResponse(url=mat["thumb"])

    raise HTTPException(status_code=404, detail="Cover not found")
