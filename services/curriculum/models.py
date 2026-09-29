"""Curriculum domain data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChapterNode:
    """Represents a node in a textbook chapter hierarchy."""
    id: str
    title: str
    order: int = 0
    children: list[ChapterNode] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "order": self.order,
            "children": [c.to_dict() for c in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChapterNode:
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", data.get("name", ""))),
            order=int(data.get("order", 0) or 0),
            children=[cls.from_dict(c) for c in data.get("children", []) or []],
        )


@dataclass
class TextbookMaterial:
    """Represents a textbook / educational material."""
    id: str
    title: str
    tag_ids: list[str] = field(default_factory=list)
    dims: dict[str, dict[str, str]] = field(default_factory=dict)
    thumb: str = ""
    is_visible: bool = True
    vis_reason: str = "官网公开开放"
    vis_code: str = "OPEN"
    has_vocab: bool = False
    vocab_count: int = 0
    raw_data: dict[str, Any] = field(default_factory=dict)

    @property
    def stage_name(self) -> str:
        return self.dims.get("zxxxd", {}).get("name", "")

    @property
    def stage_id(self) -> str:
        return self.dims.get("zxxxd", {}).get("id", "")

    @property
    def grade_name(self) -> str:
        return self.dims.get("zxxnj", {}).get("name", "")

    @property
    def grade_id(self) -> str:
        return self.dims.get("zxxnj", {}).get("id", "")

    @property
    def subject_name(self) -> str:
        return self.dims.get("zxxxk", {}).get("name", "")

    @property
    def subject_id(self) -> str:
        return self.dims.get("zxxxk", {}).get("id", "")

    @property
    def edition_name(self) -> str:
        return self.dims.get("zxxbb", {}).get("name", "")

    @property
    def edition_id(self) -> str:
        return self.dims.get("zxxbb", {}).get("id", "")

    @property
    def term_name(self) -> str:
        return self.dims.get("zxxcc", {}).get("name", "")

    @property
    def term_id(self) -> str:
        return self.dims.get("zxxcc", {}).get("id", "")

    def to_dict(self) -> dict[str, Any]:
        """Convert back to dictionary representation for API serialization."""
        d = dict(self.raw_data)
        d["id"] = self.id
        d["title"] = self.title
        d["tag_ids"] = self.tag_ids
        d["dims"] = self.dims
        d["thumb"] = self.thumb
        d["isVisible"] = self.is_visible
        d["visReason"] = self.vis_reason
        d["visCode"] = self.vis_code
        d["hasVocab"] = self.has_vocab
        d["vocabCount"] = self.vocab_count
        return d


@dataclass
class TextbookVocabInfo:
    """Represents the vocabulary package and images for a textbook."""
    material_id: str
    title: str
    stage: str
    edition: str
    grade: str
    term: str
    folder_path: str
    image_count: int
    start_page: Optional[int]
    end_page: Optional[int]
    page_range: list[int]
    images: list[dict[str, Any]]
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "material_id": self.material_id,
            "title": self.title,
            "stage": self.stage,
            "edition": self.edition,
            "grade": self.grade,
            "term": self.term,
            "folder_path": self.folder_path,
            "image_count": self.image_count,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "page_range": self.page_range,
            "images": self.images,
            "summary": self.summary,
        }


@dataclass
class CurriculumFilter:
    """Filter parameters for querying educational materials."""
    mode: str = "visible"
    stage: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    edition: Optional[str] = None
    term: Optional[str] = None
    q: Optional[str] = None
    limit: Optional[int] = None


@dataclass
class CurriculumQueryResult:
    """Result of querying curriculum materials."""
    total: int
    mode: str
    count: int
    items: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "mode": self.mode,
            "count": self.count,
            "items": self.items,
        }
