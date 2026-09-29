"""Deterministic, validated expansion of one canonical ExamSpec into leaf slots."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


from .allocator import TopicAllocator
from .topic_scope import GENERIC_TOPICS, choose_topic
from .rules import resolve_answer_space_lines, resolve_cognitive_target


class BlueprintGenerator:
    @staticmethod
    def generate(
        spec: dict[str, Any],
        exam_id: str = "current",
        plan_id: str | None = None,
        revision: int = 1,
        spec_revision: int = 1,
        material_id: str | None = None,
    ) -> dict[str, Any]:
        from services.exam.spec_validation import validate_spec
        validate_spec(spec, require_scope_confirmation=True)
        scope = spec["taught_scope"]
        excluded = scope["excluded_topics"]
        taught = set(scope["topics"])
        slots: list[dict[str, Any]] = []
        topic_counts, chapter_counts = {}, {}
        for section in spec["sections"]:
            topics = TopicAllocator.clean_topics(section["topics"], excluded)
            if not topics or set(topics) - taught:
                raise ValueError(f"sections.{section['id']}.topics exceeds taught_scope.topics")
            if GENERIC_TOPICS.intersection(topics):
                raise ValueError("题型仍使用模板通用标签，请选择具体教材考点并重新确认范围")
            for index in range(section["count"]):
                order = len(slots) + 1
                topic = choose_topic(topics, topic_counts, chapter_counts)
                kind = section["question_type"]
                slot = {
                    "slot_id": f"slot_{order:03d}",
                    "order": order,
                    "section_id": section["id"],
                    "kind": kind,
                    "target_topic": topic,
                    "knowledge_ids": [topic],
                    "objective": resolve_cognitive_target(kind, index, section["count"]),
                    "cognitive_target": resolve_cognitive_target(kind, index, section["count"]),
                    "constraints": [*scope["permitted_methods"], *[f"排除：{item}" for item in excluded]],
                    "score_x100": section["score_each_x100"],
                    "answer_space_lines": resolve_answer_space_lines(kind),
                    "material_group_id": None,
                    "parent_slot_id": None,
                    "status": "PENDING",
                }
                slot['constraints'].append('围绕指定target_topic命题，不得改用教材中的其他考点。')
                if topic_counts[topic] > 1:
                    slot['constraints'].append(f'本考点在本卷第{topic_counts[topic]}次出现，须改变条件与解题任务，不能仅换数字。')
                if material_id:
                    slot["material_id"] = material_id
                slots.append(slot)

        if sum(slot["score_x100"] for slot in slots) != spec["total_score_x100"]:
            raise ValueError("blueprint slot scores do not equal total_score_x100")
        # Largest remainder gives the nearest possible integer slot counts; ties are stable.
        count = len(slots)
        distribution = spec["difficulty_distribution"]
        levels = ("basic", "medium", "advanced")
        targets = {level: count * distribution[level] / 100 for level in levels}
        quotas = {level: int(targets[level]) for level in levels}
        for level in sorted(levels, key=lambda item: (-(targets[item] - quotas[item]), levels.index(item)))[: count - sum(quotas.values())]:
            quotas[level] += 1
        difficulty_order = [level for level in levels for _ in range(quotas[level])]
        for slot, level in zip(slots, difficulty_order, strict=True):
            slot["estimated_difficulty"] = level

        frozen_spec = json.loads(json.dumps(spec, ensure_ascii=False, sort_keys=True))
        fingerprint = {
            "exam_id": exam_id,
            "spec_revision": spec_revision,
            "plan_revision": revision,
            "spec": frozen_spec,
            "slots": slots,
        }
        plan_hash = hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return {
            "exam_id": exam_id,
            "plan_id": plan_id or f"plan_{uuid4().hex}",
            "spec_revision": spec_revision,
            "plan_revision": revision,
            "plan_hash": plan_hash,
            "revision": revision,
            "confirmed": False,
            "confirmed_by": None,
            "confirmed_at": None,
            "slots": slots,
            "total_score_x100": spec["total_score_x100"],
            "difficulty_distribution": quotas,
            "canonical_spec": frozen_spec,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
