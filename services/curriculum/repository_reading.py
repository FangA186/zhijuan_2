"""Read operations over the loaded curriculum indexes."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from .models import TextbookMaterial


class CurriculumRepositoryReadingMixin:
    def get_tags(self) -> dict[str, Any]:
        self.ensure_loaded()
        return self._tags_root


    def get_all_materials(self) -> list[TextbookMaterial]:
        self.ensure_loaded()
        return self._materials


    def get_material_by_id(self, material_id: str) -> Optional[TextbookMaterial]:
        self.ensure_loaded()
        mat = self._material_map.get(material_id)
        if mat:
            return mat
        v = self._vocab_by_material_id.get(material_id)
        if v:
            return TextbookMaterial(
                id=material_id,
                title=v.get("title", ""),
                dims={
                    "zxxxd": {"id": "", "name": v.get("stage", "")},
                    "zxxbb": {"id": "", "name": v.get("edition", "")},
                    "zxxnj": {"id": "", "name": v.get("grade", "")},
                    "zxxcc": {"id": "", "name": v.get("term", "")},
                    "zxxxk": {"id": "", "name": "英语"},
                },
                has_vocab=True,
                vocab_count=v.get("image_count", 0),
                raw_data={"id": material_id, "title": v.get("title", "")},
            )
        return None


    def get_material_detail(self, material_id: str) -> dict[str, Any]:
        for d in (self.tch_details_dir, self.details_dir):
            p = d / f"{material_id}.json"
            if p.is_file():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
        return {}


    def get_chapter_tree(self, material_id: str) -> Optional[list[dict[str, Any]]]:
        tree_path = self.trees_dir / f"{material_id}.json"
        if not tree_path.is_file():
            return None
        try:
            with open(tree_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


    def get_cover_path(self, material_id: str) -> Optional[Path]:
        cover_file = self.covers_dir / f"{material_id}.jpg"
        if cover_file.is_file():
            return cover_file
        return None


    def _find_vocab_record(
        self,
        mat_id: str,
        stage_n: str,
        ed_n: str,
        gr_n: str,
        tm_n: str,
        title: str = "",
    ) -> Optional[dict[str, Any]]:
        """Smart adaptive matching for vocabulary record across ID, stage, edition, grade, term."""
        # 1. Exact material_id
        if mat_id and mat_id in self._vocab_by_material_id:
            return self._vocab_by_material_id[mat_id]

        # Normalize stage name (handles • vs ·)
        norm_stage = stage_n
        if "五" in stage_n and "四" in stage_n:
            norm_stage = "初中（五·四学制）" if "初中" in stage_n else "小学（五·四学制）"

        # Normalize edition name
        norm_ed = ed_n.replace("(", "（").replace(")", "）")
        if norm_stage == "初中" and "外研社" in norm_ed:
            norm_ed = "外研社版"

        # 2. Exact 4-tuple key
        key = (norm_stage, norm_ed, gr_n, tm_n)
        if key in self._vocab_by_key:
            return self._vocab_by_key[key]

        # 3. High school: match on (stage, edition, term) regardless of grade
        if norm_stage == "高中":
            for (v_st, v_ed, v_gr, v_tm), v_rec in self._vocab_by_key.items():
                if v_st == "高中" and v_tm == tm_n:
                    if v_ed == norm_ed or v_ed in norm_ed or norm_ed in v_ed:
                        return v_rec

        # 4. Five-four system (初中/小学 五·四学制): match on (norm_stage, edition, grade, term)
        if "五·四学制" in norm_stage:
            for (v_st, v_ed, v_gr, v_tm), v_rec in self._vocab_by_key.items():
                if v_st == norm_stage and v_tm == tm_n and v_gr == gr_n:
                    if v_ed == norm_ed or v_ed in norm_ed or norm_ed in v_ed:
                        return v_rec

        # 5. Fuzzy edition matching for Primary/Junior (e.g. 人教版 vs 人教版（主编：吴欣）)
        for (v_st, v_ed, v_gr, v_tm), v_rec in self._vocab_by_key.items():
            if v_st == norm_stage and v_tm == tm_n and (v_gr == gr_n or norm_stage == "高中"):
                if v_ed in norm_ed or norm_ed in v_ed:
                    return v_rec

        # 6. Title matching fallback
        if title:
            clean_t = title.replace(" ", "").replace("•", "·").replace("(", "（").replace(")", "）")
            for v_rec in self._vocab_by_material_id.values():
                vt = v_rec.get("title", "").replace(" ", "").replace("•", "·").replace("(", "（").replace(")", "）")
                if vt and (clean_t in vt or vt in clean_t):
                    return v_rec

        return None


    def get_material_vocab(self, material_id: str) -> Optional[dict[str, Any]]:
        """Get structured vocabulary metadata and image list for a textbook."""
        self.ensure_loaded()
        rec = self._vocab_by_material_id.get(material_id)
        if rec:
            return rec
        mat = self._material_map.get(material_id)
        if mat:
            return self._find_vocab_record(
                mat.id,
                mat.stage_name,
                mat.edition_name,
                mat.grade_name,
                mat.term_name,
                mat.title,
            )
        return None


    def get_vocab_image_path(self, material_id: str, filename: str) -> Optional[Path]:
        """Return the secure local path of a vocabulary page image for a textbook."""
        self.ensure_loaded()
        vocab = self.get_material_vocab(material_id)
        if not vocab:
            return None

        # Filename whitelist verification
        allowed_filenames = {img["filename"] for img in vocab.get("images", [])}
        if filename not in allowed_filenames:
            return None

        folder_path = vocab.get("folder_path", "")
        img_file = (self.vocab_images_base / folder_path / filename).resolve()

        # Path traversal guard
        if not str(img_file).startswith(str(self.vocab_images_base)):
            return None

        if img_file.is_file():
            return img_file
        return None
