from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _empty_result(filename: str) -> dict[str, Any]:
    clean_title = Path(filename).stem if filename else "自定义试卷模板"
    return {"title": clean_title, "duration_minutes": 90, "total_score": 100,
            "total_score_x100": 10000, "sections": [], "engine_used": "rule_empty"}


def _parse_header(paragraphs: list[str], filename: str):
    # 1. Title detection
    title = ""
    for p in paragraphs[:5]:
        p_clean = p.strip()
        if any(kw in p_clean for kw in ["试卷", "测试", "考试", "期末", "期中", "调研", "模拟", "诊断", "监测"]):
            title = p_clean
            break
    if not title:
        title = Path(filename).stem if filename else paragraphs[0]

    # Prefer filename if filename is richer with test/academic metadata
    if filename:
        clean_fn = Path(filename).stem
        if any(kw in clean_fn for kw in ["学年", "人教", "苏教", "北师大", "期末", "期中", "测试卷", "模拟"]):
            if len(clean_fn) >= len(title):
                title = clean_fn

    # 2. Duration and total score detection
    duration = 90
    total_score = 100
    full_text = "\n".join(paragraphs[:15])

    time_match = re.search(r"(?:考试时间|时间|时量)[:：\s]*(\d+)\s*分钟", full_text)
    if time_match:
        try:
            duration = int(time_match.group(1))
        except ValueError:
            pass

    score_match = re.search(r"(?:满分|总分)[:：\s]*(\d+)\s*分", full_text)
    if score_match:
        try:
            total_score = int(score_match.group(1))
        except ValueError:
            pass
    return title, duration, total_score


def _finalize(title, duration, total_score, parsed_sections, calculated_total_score, warnings):
    # If detected total score aligns with calculated, keep detected; else use calculated
    final_total_score = total_score
    if calculated_total_score > 0:
        if calculated_total_score in (100, 120, 150):
            final_total_score = calculated_total_score
        elif abs(calculated_total_score - total_score) > 5 and total_score not in (100, 120, 150):
            final_total_score = calculated_total_score
        elif total_score == 100 and calculated_total_score in (120, 150):
            final_total_score = calculated_total_score

    # Duration heuristic if 150 points
    if final_total_score >= 150 and duration == 90:
        duration = 120

    return {
        "title": title,
        "duration_minutes": duration,
        "total_score": final_total_score,
        "total_score_x100": final_total_score * 100,
        "sections": parsed_sections,
        "engine_used": "rule_engine",
        "warnings": warnings,
    }
