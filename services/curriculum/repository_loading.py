"""Dataset initialization, tag indexing, and visibility rules."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from .models import TextbookMaterial


class CurriculumRepositoryLoadingMixin:
    def __init__(self, data_dir: Optional[Path] = None):
        workspace_root = Path(__file__).resolve().parents[2]
        if data_dir is None:
            # Default to <workspace_root>/smartedu_data
            data_dir = workspace_root / "smartedu_data"
        self.data_dir = data_dir
        self.tags_file = self.data_dir / "1_tags" / "national_lesson_tag.json"
        self.mats_file = self.data_dir / "2_materials_list" / "all_materials.json"
        self.details_dir = self.data_dir / "3_details"
        self.tch_details_dir = self.data_dir / "tch_material" / "details"
        self.trees_dir = self.data_dir / "4_trees"
        self.covers_dir = self.data_dir / "covers"
        self.vocab_catalog_file = Path(__file__).resolve().parent / "vocab_catalog.json"
        self.vocab_images_base = workspace_root / "教材单词图片"

        self._tags_root: dict[str, Any] = {}
        self._tag_name_map: dict[str, str] = {}
        self._materials: list[TextbookMaterial] = []
        self._material_map: dict[str, TextbookMaterial] = {}
        self._vocab_by_material_id: dict[str, dict[str, Any]] = {}
        self._vocab_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        self._loaded: bool = False


    def _build_tag_map(self, node: dict[str, Any]) -> None:
        if not node:
            return
        tag_id = node.get("tag_id")
        tag_name = node.get("tag_name")
        if tag_id and tag_name:
            self._tag_name_map[tag_id] = tag_name
        for h in node.get("hierarchies") or []:
            for c in h.get("children") or []:
                self._build_tag_map(c)


    def _compute_visibility(self, mat_dict: dict[str, Any]) -> tuple[bool, str, str]:
        tag_id_set = set(mat_dict.get("tag_ids") or [t.get("tag_id") for t in mat_dict.get("tag_list", []) if t.get("tag_id")])
        curr = self._tags_root
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
                        tag_name = self._tag_name_map.get(hid, "对应选项")
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


    def ensure_loaded(self) -> None:
        """Load datasets into memory index once."""
        if self._loaded:
            return

        if self.tags_file.is_file():
            try:
                with open(self.tags_file, "r", encoding="utf-8") as f:
                    self._tags_root = json.load(f)
                self._build_tag_map(self._tags_root)
            except Exception:
                self._tags_root = {}

        if self.vocab_catalog_file.is_file():
            try:
                with open(self.vocab_catalog_file, "r", encoding="utf-8") as f:
                    v_data = json.load(f)
                    self._vocab_by_material_id = v_data.get("materials", {})
                    for rec in self._vocab_by_material_id.values():
                        st = rec.get("stage", "")
                        ed = rec.get("edition", "")
                        gr = rec.get("grade", "")
                        tm = rec.get("term", "")
                        self._vocab_by_key[(st, ed, gr, tm)] = rec
            except Exception:
                self._vocab_by_material_id = {}
                self._vocab_by_key = {}

        if self.mats_file.is_file():
            try:
                with open(self.mats_file, "r", encoding="utf-8") as f:
                    raw_mats = json.load(f)
            except Exception:
                raw_mats = []

            mats_list = []
            mats_map = {}
            for m in raw_mats:
                mat_id = m.get("id")
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

                thumbs = (m.get("custom_properties") or {}).get("thumbnails") or []
                thumb = thumbs[0] if thumbs else ""

                temp_dict = dict(m)
                temp_dict["tag_ids"] = list(tag_ids)
                is_vis, reason, code = self._compute_visibility(temp_dict)

                stage_n = dims.get("zxxxd", {}).get("name", "")
                if "五" in stage_n and "四" in stage_n:
                    stage_n = "初中（五·四学制）" if "初中" in stage_n else "小学（五·四学制）"
                ed_n = dims.get("zxxbb", {}).get("name", "").replace("(", "（").replace(")", "）")
                if stage_n == "初中" and "外研社" in ed_n:
                    ed_n = "外研社版"
                gr_n = dims.get("zxxnj", {}).get("name", "")
                tm_n = dims.get("zxxcc", {}).get("name", "")

                vocab_rec = self._find_vocab_record(
                    mat_id, stage_n, ed_n, gr_n, tm_n, m.get("title", "")
                )
                has_vocab = bool(vocab_rec)
                vocab_count = vocab_rec.get("image_count", 0) if vocab_rec else 0

                entity = TextbookMaterial(
                    id=mat_id,
                    title=m.get("title", ""),
                    tag_ids=list(tag_ids),
                    dims=dims,
                    thumb=thumb,
                    is_visible=is_vis,
                    vis_reason=reason,
                    vis_code=code,
                    has_vocab=has_vocab,
                    vocab_count=vocab_count,
                    raw_data=m,
                )
                mats_list.append(entity)
                if mat_id:
                    mats_map[mat_id] = entity

            self._materials = mats_list
            self._material_map = mats_map

        self._loaded = True
