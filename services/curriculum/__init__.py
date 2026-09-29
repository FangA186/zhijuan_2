"""Curriculum domain module."""
from __future__ import annotations
from .models import (
    TextbookMaterial,
    ChapterNode,
    CurriculumFilter,
    CurriculumQueryResult,
)
from .repository import CurriculumRepository
from .service import CurriculumService

# Global shared singleton instance
curriculum_service = CurriculumService()

__all__ = [
    "TextbookMaterial",
    "ChapterNode",
    "CurriculumFilter",
    "CurriculumQueryResult",
    "CurriculumRepository",
    "CurriculumService",
    "curriculum_service",
]
