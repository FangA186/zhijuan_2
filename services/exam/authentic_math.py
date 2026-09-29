"""Stable import surface for the deterministic math candidate fallback."""
from __future__ import annotations

import hashlib
import random
from typing import Any

from .authentic_math_fill_blank import _build_fill_blank
from .authentic_math_multiple import _build_multiple_choice
from .authentic_math_single import _build_single_choice
from .authentic_math_solution import _build_solution


def _hash_seed(text: str, order: int) -> int:
    h = hashlib.md5(f"{text}_{order}".encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def generate_authentic_candidate(
    local_id: str,
    order_num: int,
    kind: str,
    target_topic: str,
    score_x100: int,
    stage: str = "senior",
    subject: str = "数学",
) -> dict[str, Any]:
    """Generate an authentic, LaTeX-enabled question candidate based on topic and kind."""
    rng = random.Random(_hash_seed(target_topic, order_num))
    if kind == "single_choice":
        return _build_single_choice(local_id, order_num, target_topic, score_x100, rng)
    if kind == "multiple_choice":
        return _build_multiple_choice(local_id, order_num, target_topic, score_x100, rng)
    if kind == "fill_blank":
        return _build_fill_blank(local_id, order_num, target_topic, score_x100, rng)
    return _build_solution(local_id, order_num, target_topic, score_x100, rng)
