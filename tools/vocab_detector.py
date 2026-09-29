#!/usr/bin/env python3
"""Find vocabulary page ranges in locally cached textbook images."""

import json
import os
import re
from typing import Dict

BASE_DIR = os.path.abspath("./教材单词图片")

if __package__:
    from tools.vocab_page_features import analyze_page_features
    from tools.vocab_range_solver import solve_vocab_range
    from tools.vocab_ocr import run_ocr
else:
    from vocab_page_features import analyze_page_features
    from vocab_range_solver import solve_vocab_range
    from vocab_ocr import run_ocr

def detect_vocab_in_book(book_rel_path: str, force_refresh: bool = False) -> Dict:
    """
    智能检测单本教材中的单词表区间与页面分类。
    支持读取与写入本地缓存 .vocab_meta.json。
    """
    book_rel_path = book_rel_path.lstrip("/\\")
    full_book_dir = os.path.abspath(os.path.join(BASE_DIR, book_rel_path))

    if not full_book_dir.startswith(BASE_DIR) or not os.path.isdir(full_book_dir):
        return {"success": False, "error": "Book directory not found"}

    cache_file = os.path.join(full_book_dir, ".vocab_meta.json")

    # 获取目录下的图片列表
    img_files = [f for f in os.listdir(full_book_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    img_files.sort()

    if not img_files:
        return {
            "success": True,
            "detected": False,
            "total_pages": 0,
            "summary": "该目录下无图片",
            "vocab_files": [],
            "non_vocab_files": [],
            "pages": [],
        }

    # 检查缓存是否有效
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                cached_files = [p["filename"] for p in cached.get("pages", [])]
                if cached_files == img_files:
                    return cached
        except Exception:
            pass

    # 逐页执行 OCR 与特征提取
    pages_features = []
    for f in img_files:
        f_path = os.path.join(full_book_dir, f)
        text = run_ocr(f_path)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        feat = analyze_page_features(lines)
        feat["filename"] = f
        feat["rel_file_path"] = os.path.relpath(f_path, BASE_DIR)

        # 提取页码
        m_page = re.search(r"page_(\d+)", f)
        feat["page_num"] = int(m_page.group(1)) if m_page else None
        pages_features.append(feat)

    # 求解区间
    vocab_range = solve_vocab_range(pages_features)

    pages_result = []
    vocab_files = []
    non_vocab_files = []

    if vocab_range is not None:
        start_idx, end_idx = vocab_range
        for i, p in enumerate(pages_features):
            is_in_range = (start_idx <= i <= end_idx)
            is_start = (i == start_idx)

            if is_start:
                final_type = "vocab_start"
                final_label = "⭐ 单词表首页"
            elif is_in_range:
                final_type = "vocab"
                final_label = "📖 单词表"
            elif i < start_idx:
                final_type = "prefix_text"
                final_label = "📄 课文/语法"
            else:
                final_type = p["page_type"] if p["page_type"] in ["copyright", "appendix", "grammar"] else "suffix_other"
                final_label = p["type_label"] if p["page_type"] in ["copyright", "appendix", "grammar"] else "📄 附录/封底"

            page_dict = {
                "filename": p["filename"],
                "rel_file_path": p["rel_file_path"],
                "page_num": p["page_num"],
                "idx": i,
                "is_vocab": is_in_range,
                "is_start": is_start,
                "type": final_type,
                "label": final_label,
                "score": p["score"],
                "preview_line": p["preview_line"],
            }
            pages_result.append(page_dict)

            if is_in_range:
                vocab_files.append(p["rel_file_path"])
            else:
                non_vocab_files.append(p["rel_file_path"])

        start_page_num = pages_features[start_idx]["page_num"] or (start_idx + 1)
        end_page_num = pages_features[end_idx]["page_num"] or (end_idx + 1)
        vocab_count = end_idx - start_idx + 1
        prefix_count = start_idx
        suffix_count = len(img_files) - 1 - end_idx

        summary_parts = [f"检测到单词表位于第 {start_page_num} 页 ~ 第 {end_page_num} 页（共 {vocab_count} 页）"]
        if prefix_count > 0:
            summary_parts.append(f"前 {prefix_count} 页为课文/语法")
        if suffix_count > 0:
            summary_parts.append(f"后 {suffix_count} 页为附录/封底")

        summary = " · ".join(summary_parts)
        result = {
            "success": True,
            "detected": True,
            "total_pages": len(img_files),
            "start_idx": start_idx,
            "end_idx": end_idx,
            "start_file": img_files[start_idx],
            "end_file": img_files[end_idx],
            "start_page": start_page_num,
            "end_page": end_page_num,
            "vocab_count": vocab_count,
            "non_vocab_count": len(non_vocab_files),
            "vocab_files": vocab_files,
            "non_vocab_files": non_vocab_files,
            "pages": pages_result,
            "summary": summary,
        }
    else:
        # 未能找到明确的词汇表
        for i, p in enumerate(pages_features):
            pages_result.append({
                "filename": p["filename"],
                "rel_file_path": p["rel_file_path"],
                "page_num": p["page_num"],
                "idx": i,
                "is_vocab": False,
                "is_start": False,
                "type": p["page_type"],
                "label": p["type_label"],
                "score": p["score"],
                "preview_line": p["preview_line"],
            })
            non_vocab_files.append(p["rel_file_path"])

        result = {
            "success": True,
            "detected": False,
            "total_pages": len(img_files),
            "start_idx": None,
            "end_idx": None,
            "start_file": None,
            "end_file": None,
            "start_page": None,
            "end_page": None,
            "vocab_count": 0,
            "non_vocab_count": len(img_files),
            "vocab_files": [],
            "non_vocab_files": non_vocab_files,
            "pages": pages_result,
            "summary": "未在该册末尾 30 页中检测到显著的单词表，请手动确认",
        }

    # 写入本地缓存
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Cache Write Error] {cache_file}: {e}")

    return result


if __name__ == "__main__":
    if __package__:
        from tools.vocab_detector_cli import main
    else:
        from vocab_detector_cli import main
    main()
