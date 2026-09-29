"""Domain models and schema definitions for ExamBlueprint and BlueprintSlot."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional

QuestionKind = Literal[
    'single_choice',
    'multiple_choice',
    'true_false',
    'fill_blank',
    'solution',
    'short_answer',
    'essay',
    'material_group',
]

DifficultyLevel = Literal['basic', 'medium', 'advanced']

SlotStatus = Literal[
    'PENDING',
    'AUTHORING',
    'SOLVING',
    'CHECKING',
    'REPAIRING',
    'READY',
    'REVIEW_REQUIRED',
    'FAIL',
]

@dataclass
class BlueprintSlotDefinition:
    slot_id: str
    order: int
    section_id: str
    kind: QuestionKind
    target_topic: str
    cognitive_target: str
    estimated_difficulty: DifficultyLevel
    score_x100: int
    answer_space_lines: int
    material_id: Optional[str] = None
    chapter_id: Optional[str] = None
    sub_topics: list[str] = field(default_factory=list)
    status: SlotStatus = 'PENDING'

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if not self.material_id:
            d.pop('material_id', None)
        if not self.chapter_id:
            d.pop('chapter_id', None)
        if not self.sub_topics:
            d.pop('sub_topics', None)
        return d


@dataclass
class BlueprintDefinition:
    exam_id: str
    plan_id: str
    revision: int
    confirmed: bool
    slots: list[BlueprintSlotDefinition]
    total_score_x100: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            'exam_id': self.exam_id,
            'plan_id': self.plan_id,
            'revision': self.revision,
            'confirmed': self.confirmed,
            'slots': [s.to_dict() for s in self.slots],
            'total_score_x100': self.total_score_x100,
            'created_at': self.created_at,
        }
