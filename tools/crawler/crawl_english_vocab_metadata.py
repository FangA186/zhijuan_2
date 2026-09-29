"""Normalize textbook curriculum metadata and output folder names."""
from __future__ import annotations

from collections import defaultdict
import json
import os

if __package__:
    from .crawl_english_vocab_config import DIM_MAP
else:
    from crawl_english_vocab_config import DIM_MAP


def parse_material_metadata(mat):
    """解析教材的维度标签及标题信息"""
    tags = {}
    bknd = ""
    for t in mat.get("tag_list", []):
        dim = t.get("tag_dimension_id")
        name = t.get("tag_name", "").strip()
        if dim in DIM_MAP:
            tags[DIM_MAP[dim]] = name
        elif dim == "bknd":
            bknd = name
        elif name == "英语":
            tags["学科"] = "英语"

    # 标准化学段名称（统一中英文括号与标点）
    stage = tags.get("学段", "未知")
    if "五" in stage and "四" in stage:
        if "初中" in stage:
            stage = "初中（五·四学制）"
        elif "小学" in stage:
            stage = "小学（五·四学制）"
    tags["学段"] = stage

    # 规范化版本名称括号及课程教学别名对齐
    edition = tags.get("版本", "未知")
    edition = edition.replace("(", "（").replace(")", "）")
    if stage == "初中" and "外研社" in edition:
        edition = "外研社版"
    tags["版本"] = edition

    title = mat.get("title") or ""
    if not title and isinstance(mat.get("global_title"), dict):
        title = mat.get("global_title", {}).get("zh-CN", "")

    return {
        "id": mat.get("id"),
        "title": title,
        "tags": tags,
        "bknd": bknd,
        "create_time": mat.get("create_time", ""),
    }


def build_folder_path(meta, is_duplicate_group=False):
    """构建与用户期望结构完全一致的存储目录路径"""
    tags = meta["tags"]
    stage = tags.get("学段", "其他")
    edition = tags.get("版本", "未知版本")
    grade = tags.get("年级", "")
    term = tags.get("册次", "全一册")

    # 如果同一学段/版本/年级/册次有新老多本教材，用年度或年份标识区分目录
    suffix = ""
    if is_duplicate_group:
        if meta["bknd"]:
            suffix = f"（{meta['bknd']}）"
        elif meta["create_time"]:
            suffix = f"（{meta['create_time'][:4]}版）"

    folder_term = f"{term}{suffix}"

    if stage == "高中":
        # 高中通常直接按 高中/版本/册次
        return os.path.join(stage, edition, folder_term)
    else:
        # 小学与初中：学段/版本/年级/册次
        return os.path.join(stage, edition, grade, folder_term)


def load_curriculum_whitelist():
    """从 national_lesson_tag.json 严格提取官方课程教学认可的 (学段, 年级, 版本) 白名单"""
    tag_path = "smartedu_data/national_lesson_tag.json"
    if not os.path.exists(tag_path):
        return None
    try:
        with open(tag_path, "r", encoding="utf-8") as f:
            tag_data = json.load(f)
    except Exception:
        return None

    whitelist = defaultdict(lambda: defaultdict(set))
    def traverse(node, current_path):
        dim = node.get("tag_dimension_id", "")
        name = node.get("tag_name", "").strip()
        new_path = current_path + [(dim, name)]
        hierarchies = node.get("hierarchies") or []
        if not hierarchies:
            d = {item[0]: item[1] for item in new_path}
            if d.get("zxxxk") == "英语":
                st = d.get("zxxxd", "")
                if "五" in st and "四" in st:
                    st = "初中（五·四学制）" if "初中" in st else "小学（五·四学制）"
                gr = d.get("zxxnj", "")
                ed = d.get("zxxbb", "").replace("(", "（").replace(")", "）")
                whitelist[st][gr].add(ed)
            return
        for h in hierarchies:
            for c in (h.get("children") or []):
                traverse(c, new_path)

    for root in (tag_data.get("hierarchies") or []):
        for c in (root.get("children") or []):
            traverse(c, [])
    return whitelist

