"""Educational measurement and validation rules for blueprint generation."""
from __future__ import annotations
from typing import Any
from .schema import DifficultyLevel, QuestionKind

def validate_score_balance(
    sections: list[dict[str, Any]], total_score_x100: int, tolerance_x100: int = 0
) -> tuple[bool, int, int]:
    """Return exact integer score balance; tolerance is retained for old callers only."""
    actual = sum(section["count"] * section["score_each_x100"] for section in sections)
    difference = total_score_x100 - actual
    return difference == 0, actual, difference


def resolve_cognitive_target(kind: QuestionKind, index_in_sec: int, total_in_sec: int) -> str:
    """Determine educational cognitive target based on question kind and progression order."""
    if kind in ('single_choice', 'multiple_choice', 'true_false'):
        if total_in_sec <= 1:
            return '基础理解'
        ratio = index_in_sec / max(1, total_in_sec - 1)
        if ratio <= 0.35:
            return '基础理解与概念识记'
        elif ratio <= 0.75:
            return '运算求解与概念应用'
        else:
            return '综合分析与逻辑推演'

    elif kind == 'fill_blank':
        if total_in_sec <= 1:
            return '运算求解'
        ratio = index_in_sec / max(1, total_in_sec - 1)
        if ratio <= 0.4:
            return '概念辨析与直接运算'
        elif ratio <= 0.8:
            return '结构转化与综合运算'
        else:
            return '多步推导与深层求解'

    elif kind == 'solution':
        if total_in_sec <= 1:
            return '综合论证与深度求解'
        if index_in_sec == 0:
            return '基础定理与标准运算'
        elif index_in_sec == total_in_sec - 1:
            return '压轴综合推演与创新突破'
        elif index_in_sec == 1:
            return '推理论证与转化化归'
        else:
            return '数学建模与多知识点综合应用'

    elif kind == 'short_answer':
        return '要点提炼与逻辑表达'

    elif kind == 'essay':
        return '材料思辨与深度论述'

    return '核心概念综合应用'


def resolve_difficulty(kind: QuestionKind, index_in_sec: int, total_in_sec: int) -> DifficultyLevel:
    """Determine question difficulty level following educational measurement ladders."""
    if total_in_sec <= 1:
        return 'advanced' if kind in ('solution', 'essay') else 'medium'

    ratio = index_in_sec / max(1, total_in_sec - 1)

    if kind in ('single_choice', 'multiple_choice', 'true_false', 'fill_blank'):
        if ratio < 0.45:
            return 'basic'
        elif ratio < 0.85:
            return 'medium'
        else:
            return 'advanced'

    elif kind in ('solution', 'material_group'):
        if index_in_sec == 0:
            return 'medium' if total_in_sec > 2 else 'basic'
        elif index_in_sec == total_in_sec - 1:
            return 'advanced'
        else:
            return 'medium'

    return 'medium'


def resolve_answer_space_lines(kind: QuestionKind) -> int:
    """Determine line height for physical paper rendering."""
    mapping = {
        'single_choice': 2,
        'multiple_choice': 2,
        'true_false': 2,
        'fill_blank': 2,
        'short_answer': 6,
        'solution': 10,
        'essay': 16,
        'material_group': 12,
    }
    return mapping.get(kind, 4)
