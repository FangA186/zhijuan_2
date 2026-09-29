"""ExamSpec domain service for requirement and specification management."""
from __future__ import annotations
from typing import Any
from ..api.store import store
from .spec_validation import validate_spec
from .spec_validation import VALIDATOR

UI_FIELDS = frozenset({"material_id", "textbook_cover", "chinese_config", "english_config"})

class SpecService:
    @staticmethod
    def get_spec(exam_id: str = 'current') -> dict[str, Any]:
        return store.get_spec()

    @staticmethod
    def update_spec(spec: dict[str, Any], exam_id: str = 'current', expected_revision: int | None = None) -> dict[str, Any]:
        canonical_fields = VALIDATOR.schema["properties"]
        unexpected = set(spec) - set(canonical_fields) - UI_FIELDS
        if unexpected:
            raise ValueError(f"unknown specification fields: {', '.join(sorted(unexpected))}")
        canonical = {key: value for key, value in spec.items() if key in canonical_fields}
        canonical.setdefault("multiple_choice_partial_score_x100", 0)
        sidecar = {key: value for key, value in spec.items() if key in UI_FIELDS}
        validate_spec(canonical, require_scope_confirmation=True)
        return store.update_spec(canonical, sidecar=sidecar, expected_revision=expected_revision)
