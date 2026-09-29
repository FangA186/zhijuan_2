#!/usr/bin/env python3
"""国家中小学智慧教育平台英语教材单词页采集工具入口。"""
from __future__ import annotations

import argparse
from collections import defaultdict
import os
import sys
import time

if __package__:
    from .crawl_english_vocab_config import DATA_DIR, DETAILS_DIR, PARTS_DIR, DEFAULT_OUTPUT_DIR, HEADERS, DIM_MAP
    from .crawl_english_vocab_http import clean_url, fetch_json, fetch_all_materials
    from .crawl_english_vocab_metadata import (
        parse_material_metadata, build_folder_path, load_curriculum_whitelist,
    )
    from .crawl_english_vocab_detail import get_material_detail, resolve_real_last_page
    from .crawl_english_vocab_downloads import download_image, process_material
else:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from crawl_english_vocab_config import DATA_DIR, DETAILS_DIR, PARTS_DIR, DEFAULT_OUTPUT_DIR, HEADERS, DIM_MAP
    from crawl_english_vocab_http import clean_url, fetch_json, fetch_all_materials
    from crawl_english_vocab_metadata import (
        parse_material_metadata, build_folder_path, load_curriculum_whitelist,
    )
    from crawl_english_vocab_detail import get_material_detail, resolve_real_last_page
    from crawl_english_vocab_downloads import download_image, process_material


def main():
    parser = argparse.ArgumentParser(description="中小学智慧教育平台 - 英语教材末尾单词页图片爬虫")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="图片保存主目录 (默认: ./教材单词图片)")
    parser.add_argument("--stage", choices=["小学", "初中", "初中（五·四学制）", "小学（五·四学制）", "高中", "all"], default="all", help="筛选学段 (默认: all)")
    parser.add_argument("--edition", default="", help="筛选特定版本 (例如: 北京版, 人教版（主编：吴欣）)")
    parser.add_argument("--grade", default="", help="筛选特定年级 (例如: 三年级, 七年级)")
    parser.add_argument("--pages", type=int, default=30, help="每本教材倒序获取的页数 (默认: 30)")
    parser.add_argument("--limit", type=int, default=0, help="限制处理的教材数量 (0 为全部)")
    parser.add_argument("--material-workers", type=int, default=4, help="并发处理教材数 (默认: 4)")
    parser.add_argument("--image-workers", type=int, default=8, help="每本教材并发下载图片数 (默认: 8)")
    parser.add_argument("--clean-target", action="store_true", help="下载前清空目标目录内的旧图片与缓存，避免因页数范围变更导致新旧序号重叠")
    parser.add_argument("--dry-run", action="store_true", help="仅显示将要处理的教材与目录路径，不执行下载")
    args = parser.parse_args()

    print("=" * 65)
    print(" 智卷 - 国家中小学智慧教育平台英语教材单词页图片采集工具")
    print(f" 输出目录: {os.path.abspath(args.output_dir)}")
    print(f" 采集规则: 真实总页数倒序获取末尾 {args.pages} 页")
    print(f" 筛选范围: 学段={args.stage} | 版本={args.edition or '全部'} | 年级={args.grade or '全部'}")
    print("=" * 65)

    print("\n[1/3] 获取全量电子教材清单...")
    all_raw = fetch_all_materials()
    print(f"✓ 已加载全网教材数据共 {len(all_raw)} 条记录")

    # 筛选英语教材（严格对齐官方课程教学）
    curriculum_whitelist = load_curriculum_whitelist()
    if curriculum_whitelist:
        print("✓ 已启用 national_lesson_tag 课程教学官方白名单过滤机制")

    english_materials = []
    for raw in all_raw:
        meta = parse_material_metadata(raw)
        tags = meta["tags"]
        if tags.get("学科") != "英语" and "英语" not in meta["title"]:
            continue

        st = tags.get("学段", "")
        if args.stage != "all":
            if args.stage not in st:
                continue
        else:
            # 默认排除特殊教育和无学段教材
            if st not in ["小学", "初中", "初中（五·四学制）", "小学（五·四学制）", "高中"]:
                continue

        if args.edition and args.edition not in tags.get("版本", ""):
            continue

        if args.grade and args.grade not in tags.get("年级", ""):
            continue

        # 严格对齐官方课程教学体系：排除未在 national_lesson_tag 上线的教材
        if curriculum_whitelist:
            st_key = tags.get("学段", "")
            gr_key = tags.get("年级", "")
            ed_key = tags.get("版本", "")
            if st_key == "高中":
                # 高中无年级维度
                if ed_key not in curriculum_whitelist.get("高中", {}).get("", set()):
                    continue
            else:
                if ed_key not in curriculum_whitelist.get(st_key, {}).get(gr_key, set()):
                    continue

        english_materials.append(meta)

    print(f"✓ 筛选出符合条件的英语教材共 {len(english_materials)} 本")

    # 分析重名/新老教材分组
    group_map = defaultdict(list)
    for m in english_materials:
        key = (m["tags"].get("学段"), m["tags"].get("版本"), m["tags"].get("年级"), m["tags"].get("册次"))
        group_map[key].append(m)

    multi_keys = {k for k, v in group_map.items() if len(v) > 1}
    print(f"✓ 识别出共存的新老多版本教材组: {len(multi_keys)} 组（将自动以年度标识隔离目录）")

    if args.limit > 0:
        english_materials = english_materials[: args.limit]
        print(f"! 已根据 --limit 参数限制处理前 {len(english_materials)} 本")

    if args.dry_run:
        print("\n--- [DRY-RUN 规划清单] ---")
        for i, m in enumerate(english_materials, 1):
            key = (m["tags"].get("学段"), m["tags"].get("版本"), m["tags"].get("年级"), m["tags"].get("册次"))
            is_dup = key in multi_keys
            folder = build_folder_path(m, is_dup)
            print(f"[{i:03d}] {folder}  <==  {m['title'][:40]}")
        print("\nDry-run 完毕，未写入任何文件。")
        return

    print(f"\n[2/3] 开始批量采集末尾 {args.pages} 页单词图片...")
    start_time = time.time()
    success_count = 0
    total_imgs_downloaded = 0
    total_imgs_skipped = 0
    total_imgs_failed = 0

    total_mats = len(english_materials)
    for i, meta in enumerate(english_materials, 1):
        key = (meta["tags"].get("学段"), meta["tags"].get("版本"), meta["tags"].get("年级"), meta["tags"].get("册次"))
        is_dup = key in multi_keys
        rel_folder = build_folder_path(meta, is_dup)
        print(f"\n[{i}/{total_mats}] 正在处理: {rel_folder}")
        print(f"  教材名称: {meta['title']}")

        res = process_material(
            meta=meta,
            is_duplicate_group=is_dup,
            output_base_dir=args.output_dir,
            num_pages=args.pages,
            workers=args.image_workers,
            clean_target=args.clean_target,
        )

        if res["status"] in ["PASS", "PARTIAL"]:
            success_count += 1
            total_imgs_downloaded += res["downloaded"]
            total_imgs_skipped += res["skipped"]
            total_imgs_failed += res["failed"]
            print(f"  ✓ 成功完成: 总页数={res['total_pages']} | 抽取页码={res['page_range']} | 新增下载={res['downloaded']} | 已存在跳过={res['skipped']} | 失败={res['failed']}")
        else:
            print(f"  ✗ 处理失败: {res.get('message')}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 65)
    print("【采集任务执行完毕】")
    print(f" 耗时: {elapsed:.1f} 秒")
    print(f" 教材成功数: {success_count}/{total_mats}")
    print(f" 图片新增下载: {total_imgs_downloaded} 张")
    print(f" 图片已存在跳过: {total_imgs_skipped} 张")
    print(f" 图片失败数: {total_imgs_failed} 张")
    print(f" 文件保存在: {os.path.abspath(args.output_dir)}")
    print("=" * 65)



if __name__ == "__main__":
    main()
