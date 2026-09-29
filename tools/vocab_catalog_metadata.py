"""SmartEdu metadata mapping for the vocabulary catalog."""
import json
import os
from collections import defaultdict

BASE_DIR = os.path.abspath("./教材单词图片")
DATA_DIR = os.path.abspath("./smartedu_data")
SUMMARY_FILE = os.path.join(DATA_DIR, "tch_material", "all_tch_materials.json")
BACKUP_SUMMARY = os.path.join(DATA_DIR, "2_materials_list", "all_materials.json")
TAG_FILE = os.path.join(DATA_DIR, "national_lesson_tag.json")
OUT_FILE_API = os.path.abspath("./services/curriculum/vocab_catalog.json")
OUT_FILE_DATA = os.path.join(DATA_DIR, "vocab_catalog.json")

DIM_MAP = {
    "zxxxd": "学段",
    "zxxxk": "学科",
    "zxxbb": "版本",
    "zxxcc": "册次",
    "zxxnj": "年级",
}


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

    stage = tags.get("学段", "未知")
    if "五" in stage and "四" in stage:
        if "初中" in stage:
            stage = "初中（五·四学制）"
        elif "小学" in stage:
            stage = "小学（五·四学制）"
    tags["学段"] = stage

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
    tags = meta["tags"]
    stage = tags.get("学段", "其他")
    edition = tags.get("版本", "未知版本")
    grade = tags.get("年级", "")
    term = tags.get("册次", "全一册")

    suffix = ""
    if is_duplicate_group:
        if meta["bknd"]:
            suffix = f"（{meta['bknd']}）"
        elif meta["create_time"]:
            suffix = f"（{meta['create_time'][:4]}版）"

    folder_term = f"{term}{suffix}"
    if stage == "高中":
        return os.path.join(stage, edition, folder_term)
    else:
        return os.path.join(stage, edition, grade, folder_term)


def load_curriculum_whitelist():
    if not os.path.exists(TAG_FILE):
        return None
    try:
        with open(TAG_FILE, "r", encoding="utf-8") as f:
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


def load_smartedu_materials():
    materials_file = SUMMARY_FILE if os.path.exists(SUMMARY_FILE) else BACKUP_SUMMARY
    if not os.path.exists(materials_file):
        raise FileNotFoundError(f"SmartEdu materials not found: {materials_file}")

    with open(materials_file, "r", encoding="utf-8") as f:
        all_raw = json.load(f)

    whitelist = load_curriculum_whitelist()
    grouped = defaultdict(list)
    for raw in all_raw:
        meta = parse_material_metadata(raw)
        tags = meta["tags"]
        if tags.get("学科") != "英语" and "英语" not in meta["title"]:
            continue
        st = tags.get("学段", "")
        gr = tags.get("年级", "")
        ed = tags.get("版本", "")
        if whitelist:
            if st not in whitelist:
                continue
            if st != "高中":
                if gr not in whitelist[st]:
                    continue
                if ed not in whitelist[st][gr]:
                    continue
        key = (st, ed, gr, tags.get("册次", "全一册"))
        grouped[key].append(meta)

    folder_to_meta = {}
    for key, group in grouped.items():
        is_dup = len(group) > 1
        for meta in group:
            folder = build_folder_path(meta, is_dup)
            folder_to_meta[folder] = meta

    return folder_to_meta


