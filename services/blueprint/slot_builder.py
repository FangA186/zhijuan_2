"""Assembler for individual BlueprintSlotDefinition instances."""
from __future__ import annotations
from typing import Any, Optional
from .schema import BlueprintSlotDefinition, QuestionKind
from .rules import resolve_cognitive_target, resolve_difficulty, resolve_answer_space_lines

class SlotBuilder:
    @staticmethod
    def build_slot(
        order: int,
        section_id: str,
        kind: QuestionKind,
        index_in_sec: int,
        total_in_sec: int,
        score_each_x100: int,
        target_topic: str,
        material_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
    ) -> BlueprintSlotDefinition:
        slot_id = f'slot_{order:02d}'
        cognitive = resolve_cognitive_target(kind, index_in_sec, total_in_sec)
        difficulty = resolve_difficulty(kind, index_in_sec, total_in_sec)
        lines = resolve_answer_space_lines(kind)

        return BlueprintSlotDefinition(
            slot_id=slot_id,
            order=order,
            section_id=section_id,
            kind=kind,
            target_topic=target_topic,
            cognitive_target=cognitive,
            estimated_difficulty=difficulty,
            score_x100=score_each_x100,
            answer_space_lines=lines,
            material_id=material_id,
            chapter_id=chapter_id,
            status='PENDING',
        )
