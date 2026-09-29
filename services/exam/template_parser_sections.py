from __future__ import annotations

import re
from typing import Any


def _collect_sections(paragraphs: list[str], parser) -> list[dict[str, Any]]:
    raw_sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None

    for line in paragraphs:
        line_str = line.strip()
        header_match = parser.SECTION_HEADER_REGEX.match(line_str)
        alt_match = None
        if not header_match:
            alt_match = parser.ALT_SECTION_HEADER_REGEX.match(line_str)

        if header_match:
            content = header_match.group(2).strip()
            kind = parser._detect_kind(content)
            if kind or any(kw in line_str for kw in ["题", "部分", "选择", "填空", "解答"]):
                if current_section:
                    raw_sections.append(current_section)
                current_section = {
                    "header_line": line_str,
                    "content": content,
                    "kind": kind or "solution",
                    "questions": [],
                }
                continue
        elif alt_match and not any(line_str.startswith(f"{i}.") for i in range(1, 100)):
            kw_type = alt_match.group(1)
            kind = parser._detect_kind(kw_type) or "solution"
            if current_section:
                raw_sections.append(current_section)
            current_section = {
                "header_line": line_str,
                "content": line_str,
                "kind": kind,
                "questions": [],
            }
            continue

        # Check if line is a numbered question under current section
        if current_section:
            q_match = parser.QUESTION_NUM_REGEX.match(line)
            if q_match:
                current_section["questions"].append({
                    "num": int(q_match.group(1)),
                    "line": line,
                })

    if current_section:
        raw_sections.append(current_section)
    return raw_sections


def _score_sections(raw_sections: list[dict[str, Any]]):
    parsed_sections = []
    calculated_total_score = 0
    warnings: list[str] = []
    for idx, sec in enumerate(raw_sections, 1):
        header = sec["header_line"]
        kind = sec["kind"]
        question_items = sec["questions"]

        # Parse count: from header or from found question items
        count = 0
        count_match = re.search(r"(?:本(?:大题|题)*[共\s]*)(\d+)\s*小?题", header) or re.search(r"共\s*(\d+)\s*小?题", header)
        if count_match:
            count = int(count_match.group(1))
        elif question_items:
            count = len(question_items)
        else:
            count = 4  # sensible fallback

        # Parse score: each or total
        each_score = 0.0
        sec_total = 0.0

        each_match = re.search(r"每(?:小题|题)\s*(\d+(?:\.\d+)?)\s*分", header)
        if each_match:
            each_score = float(each_match.group(1))

        total_matches = re.findall(r"共\s*(\d+(?:\.\d+)?)\s*分", header)
        if total_matches:
            sec_total = float(total_matches[-1])
        declared_total = sec_total

        # Check question items for individual scores, e.g. 18.（本小题满分12分）
        item_scores: list[float] = []
        for q in question_items:
            m_score = re.search(r"(?:满分|分值)[:：\s]*(\d+(?:\.\d+)?)\s*分", q.get("line", ""))
            if m_score:
                item_scores.append(float(m_score.group(1)))
        if item_scores and len(item_scores) == count:
            sec_total = sum(item_scores)
            each_score = round(sec_total / count, 1)

        expected_total = sum(item_scores) if len(item_scores) == count else each_score * count
        if declared_total > 0 and expected_total > 0 and abs(expected_total - declared_total) > 0.01:
            warnings.append(f"第{idx}大题原文写共{declared_total:g}分，但按识别的逐题分值合计为{expected_total:g}分；请核对原卷。")

        # Derive missing or conflicting scores
        if each_score > 0 and count > 0:
            if sec_total == 0 or (not item_scores and abs(each_score * count - sec_total) > count * 0.5):
                sec_total = round(each_score * count, 1)
        elif sec_total > 0 and count > 0 and each_score == 0:
            each_score = round(sec_total / count, 1)
        elif each_score == 0 and sec_total == 0:
            # Default heuristics based on kind
            if kind in ("single_choice", "multiple_choice"):
                each_score = 4.0 or 5.0
                sec_total = each_score * count
            elif kind == "fill_blank":
                each_score = 4.0 or 5.0
                sec_total = each_score * count
            elif kind == "solution":
                each_score = 14.0
                sec_total = each_score * count
            else:
                each_score = 10.0
                sec_total = each_score * count

        calculated_total_score += int(sec_total)

        # Structure import cannot infer curriculum targets from question kind.
        default_topics = []

        sec_total_x100 = int(round(sec_total * 100))
        if item_scores and len(item_scores) == count:
            item_scores_x100 = [int(round(s * 100)) for s in item_scores]
        elif sec_total_x100 > 0 and count > 0:
            if sec_total_x100 % 100 == 0:
                pts = sec_total_x100 // 100
                base_pt = pts // count
                rem_pt = pts % count
                item_scores_x100 = [base_pt * 100] * (count - rem_pt) + [(base_pt + 1) * 100] * rem_pt
            else:
                base = sec_total_x100 // count
                rem = sec_total_x100 % count
                item_scores_x100 = [base] * (count - rem) + [base + 1] * rem
        else:
            each_x100 = int(round(each_score * 100))
            item_scores_x100 = [each_x100] * count
            sec_total_x100 = sum(item_scores_x100)

        score_each_x100 = item_scores_x100[0] if item_scores_x100 else int(round(each_score * 100))

        parsed_sections.append({
            "id": f"sec_{idx}",
            "title": header,
            "question_type": kind,
            "count": count,
            "score_each_x100": score_each_x100,
            "total_score_x100": sec_total_x100,
            "item_scores_x100": item_scores_x100,
            "topics": default_topics,
        })
    return parsed_sections, calculated_total_score, warnings
