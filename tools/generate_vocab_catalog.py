#!/usr/bin/env python3
"""
知卷 - 英语教材单词图片与课程元数据绑定生成器 (Vocab Catalog Generator)

功能：
1. 扫描已人工/自动清洗的 ./教材单词图片/ 目录 (共 367 本教材、2005 张词汇高清图)。
2. 与中小学智慧教育平台全量教材清单 (smartedu_data) 进行 100% 精准绑定，获取每本教材的 material_id。
3. 提取每本教材的词汇页码区间、图片列表（包含相对路径、真实书本页码、直链 API URL）及词汇摘要。
4. 生成统一结构化索引文件：
   - services/curriculum/vocab_catalog.json (知卷后端常驻加载)
   - smartedu_data/vocab_catalog.json (离线数据备份)
"""

import json
import os
import re

if __package__:
    from tools.vocab_catalog_metadata import BASE_DIR, OUT_FILE_API, OUT_FILE_DATA, load_smartedu_materials
else:
    from vocab_catalog_metadata import BASE_DIR, OUT_FILE_API, OUT_FILE_DATA, load_smartedu_materials

def scan_cleaned_books():
    """扫描 BASE_DIR 下所有清洗完毕的教材目录与图片"""
    if not os.path.exists(BASE_DIR):
        raise FileNotFoundError(f"Base dir not found: {BASE_DIR}")

    books = []
    stage_order = ["小学", "初中", "初中（五·四学制）", "小学（五·四学制）", "高中"]

    for root, dirs, files in os.walk(BASE_DIR):
        if root.endswith(".trash") or "/.trash" in root:
            continue

        jpg_files = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if not jpg_files:
            continue

        # 确保这是册次底级目录
        rel_folder = os.path.relpath(root, BASE_DIR)
        parts = rel_folder.split(os.sep)
        stage = parts[0]
        if stage not in stage_order:
            continue

        # 高中 3 层 (高中/版本/册次)，中小学 4 层 (学段/版本/年级/册次)
        if stage == "高中" and len(parts) != 3:
            continue
        if stage != "高中" and len(parts) != 4:
            continue

        jpg_files.sort()
        meta_file = os.path.join(root, ".vocab_meta.json")
        vocab_meta = {}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as mf:
                    vocab_meta = json.load(mf)
            except Exception:
                pass

        books.append({
            "rel_folder": rel_folder,
            "abs_path": root,
            "images": jpg_files,
            "vocab_meta": vocab_meta,
        })

    return books


def generate_catalog():
    print("=" * 65)
    print("知卷 - 英语教材单词图片与课程元数据绑定生成器")
    print("=" * 65)

    print("[1/3] 加载中小学智慧教育平台教材元数据...")
    folder_to_meta = load_smartedu_materials()
    print(f"✓ 课程白名单与教材映射就绪，共解析出 {len(folder_to_meta)} 本教材映射规则")

    print("\n[2/3] 扫描已清洗词汇目录资产...")
    books = scan_cleaned_books()
    print(f"✓ 扫描到 {len(books)} 本教材词汇目录")

    catalog_by_material_id = {}
    catalog_by_folder = {}
    total_images = 0
    matched_count = 0
    unmatched = []

    for b in books:
        folder = b["rel_folder"]
        img_files = b["images"]
        img_count = len(img_files)
        total_images += img_count

        meta = folder_to_meta.get(folder)
        if not meta:
            unmatched.append(folder)
            continue

        matched_count += 1
        mat_id = meta["id"]
        tags = meta["tags"]

        image_items = []
        page_numbers = []
        for idx, fn in enumerate(img_files, 1):
            m_page = re.search(r"page_(\d+)", fn)
            page_num = int(m_page.group(1)) if m_page else idx
            page_numbers.append(page_num)

            image_items.append({
                "filename": fn,
                "page_num": page_num,
                "order": idx,
                "rel_path": os.path.join(folder, fn),
                "url": f"/v1/curriculum/materials/{mat_id}/vocab/images/{fn}",
            })

        start_page = min(page_numbers) if page_numbers else None
        end_page = max(page_numbers) if page_numbers else None

        record = {
            "material_id": mat_id,
            "title": meta["title"],
            "stage": tags.get("学段", ""),
            "edition": tags.get("版本", ""),
            "grade": tags.get("年级", ""),
            "term": tags.get("册次", ""),
            "folder_path": folder,
            "image_count": img_count,
            "start_page": start_page,
            "end_page": end_page,
            "page_range": [start_page, end_page] if start_page is not None else [],
            "images": image_items,
            "summary": b["vocab_meta"].get("summary", f"收录教材原版词汇表第 {start_page} ~ {end_page} 页（共 {img_count} 页）"),
        }

        catalog_by_material_id[mat_id] = record
        catalog_by_folder[folder] = record

    print(f"✓ 匹配成功：{matched_count}/{len(books)} 本教材 (覆盖图片 {total_images} 张)")
    if unmatched:
        print(f"⚠ 未匹配目录 ({len(unmatched)} 本)：", unmatched[:5])

    output_payload = {
        "version": "1.0",
        "total_materials": len(catalog_by_material_id),
        "total_images": total_images,
        "materials": catalog_by_material_id,
        "folder_index": {f: rec["material_id"] for f, rec in catalog_by_folder.items()},
    }

    print("\n[3/3] 保存元数据索引...")
    os.makedirs(os.path.dirname(OUT_FILE_API), exist_ok=True)
    with open(OUT_FILE_API, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)
    print(f"✓ 已写入知卷后端索引：{OUT_FILE_API}")

    os.makedirs(os.path.dirname(OUT_FILE_DATA), exist_ok=True)
    with open(OUT_FILE_DATA, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2)
    print(f"✓ 已写入数据备份索引：{OUT_FILE_DATA}")

    print("\n" + "=" * 65)
    print(f" 完成！知卷已建立 {len(catalog_by_material_id)} 本教材、{total_images} 张单词图的完整对应关系。")
    print("=" * 65)


if __name__ == "__main__":
    generate_catalog()
