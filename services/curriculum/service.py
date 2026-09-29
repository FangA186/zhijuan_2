"""Curriculum domain service coordinating textbook search, chapter trees, and key topic extraction."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Optional
from .models import CurriculumFilter, CurriculumQueryResult, TextbookMaterial, ChapterNode
from .repository import CurriculumRepository


class CurriculumService:
    """Domain service for educational curriculum and SmartEdu textbooks."""

    def __init__(self, repository: Optional[CurriculumRepository] = None):
        self.repo = repository or CurriculumRepository()

    def get_tags(self) -> dict[str, Any]:
        """Get the full classification hierarchy tag tree from SmartEdu."""
        return self.repo.get_tags()

    def search_materials(self, qf: CurriculumFilter) -> CurriculumQueryResult:
        """Query textbooks with cascading filters and search keywords."""
        all_mats = self.repo.get_all_materials()
        results = all_mats

        if qf.mode == "visible":
            results = [m for m in results if m.is_visible]

        if qf.stage:
            results = [
                m for m in results
                if m.stage_id == qf.stage or m.stage_name == qf.stage
            ]

        if qf.grade:
            results = [
                m for m in results
                if m.grade_id == qf.grade or m.grade_name == qf.grade
            ]

        if qf.subject:
            results = [
                m for m in results
                if m.subject_id == qf.subject or m.subject_name == qf.subject
            ]

        if qf.edition:
            results = [
                m for m in results
                if m.edition_id == qf.edition or m.edition_name == qf.edition
            ]

        if qf.term:
            results = [
                m for m in results
                if (m.term_id == qf.term
                    or m.term_name == qf.term
                    or m.grade_id == qf.term
                    or m.grade_name == qf.term)
            ]

        if qf.q and qf.q.strip():
            k = "".join(qf.q.strip().lower().split())
            results = [m for m in results if k in "".join(m.title.lower().split())]

        total = len(results)
        items = results if qf.limit is None else results[:qf.limit]

        return CurriculumQueryResult(
            total=total,
            mode=qf.mode,
            count=len(items),
            items=[m.to_dict() for m in items],
        )

    def get_material(self, material_id: str) -> dict[str, Any] | None:
        """Get textbook summary and extra details."""
        mat = self.repo.get_material_by_id(material_id)
        if not mat:
            return None
        details = self.repo.get_material_detail(material_id)
        return {
            "summary": mat.to_dict(),
            "details": details,
        }

    def get_chapter_tree(self, material_id: str) -> list[dict[str, Any]] | None:
        """Get complete chapter catalog tree for a textbook."""
        return self.repo.get_chapter_tree(material_id)

    def extract_key_topics(self, material_id: str) -> list[str]:
        """Extract a flattened list of topic/chapter titles from the chapter tree."""
        tree = self.get_chapter_tree(material_id)
        if not tree:
            return []

        topics: list[str] = []

        def _traverse(node: dict[str, Any]) -> None:
            title = node.get("title") or node.get("name") or ""
            title = title.strip()
            if title and title not in topics:
                # Filter out pure container names like "教材目录", "正文"
                if not any(ignore in title for ignore in ["目录", "正文", "本书说明", "致谢", "后记"]):
                    topics.append(title)
            for c in node.get("children", []) or []:
                _traverse(c)

        for root_item in tree:
            _traverse(root_item)

        return topics

    def get_cover_file(self, material_id: str) -> Optional[Path]:
        """Return local cover file path if exists."""
        return self.repo.get_cover_path(material_id)

    def get_cover_fallback_url(self, material_id: str) -> Optional[str]:
        """Return CDN thumbnail url if local cover is missing."""
        mat = self.repo.get_material_by_id(material_id)
        if mat and mat.thumb:
            return mat.thumb
        return None

    def get_material_vocab(self, material_id: str) -> Optional[dict[str, Any]]:
        """Get textbook vocabulary metadata and image list."""
        return self.repo.get_material_vocab(material_id)

    def get_vocab_image_file(self, material_id: str, filename: str) -> Optional[Path]:
        """Get secure local file path for a vocabulary page image."""
        return self.repo.get_vocab_image_path(material_id, filename)
