"""Blueprint service binding plans to the current canonical specification."""
from __future__ import annotations
from typing import Any

from ..api.store import store


class BlueprintService:
    @staticmethod
    def get_blueprint(exam_id: str = "current") -> dict[str, Any]:
        return store.get_blueprint()

    @staticmethod
    def generate_blueprint(exam_id: str = "current", spec_override: dict[str, Any] | None = None, expected_revision: int | None = None) -> dict[str, Any]:
        raise ValueError('规则预览已停用，请通过 planning-jobs 调用规划 Agent')

    @staticmethod
    def confirm_blueprint(plan_id: str, exam_id: str = "current", expected_revision: int | None = None) -> dict[str, Any]:
        return store.confirm_blueprint(plan_id, expected_revision)

    @staticmethod
    def update_slot(slot_id: str, slot_data: dict[str, Any], exam_id: str = "current") -> dict[str, Any]:
        raise ValueError("Plan slots are immutable; update the specification and regenerate the plan")
