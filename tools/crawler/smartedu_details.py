"""Fetch individual SmartEdu textbook details and chapter trees."""
import csv
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from tools.crawler.smartedu_client import MAX_WORKERS, OUTPUT_DIR, fetch_json

def download_single_material(mat):
    """单个教材的任务单元：负责下载 details 和 trees"""
    mat_id = mat["id"]
    title = mat.get("title", "未知教材")

    details_path = os.path.join(OUTPUT_DIR, "3_details", f"{mat_id}.json")
    trees_path = os.path.join(OUTPUT_DIR, "4_trees", f"{mat_id}.json")

    # 1. 抓取 details (若已存在则跳过断点续传)
    details_data = None
    if not os.path.exists(details_path):
        d_url = f"https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/national_lesson/teachingmaterials/details/{mat_id}.json"
        details_data = fetch_json(d_url)
        if details_data:
            with open(details_path, "w", encoding="utf-8") as f:
                json.dump(details_data, f, ensure_ascii=False, indent=2)
    else:
        # 已存在直接读取
        try:
            with open(details_path, "r", encoding="utf-8") as f:
                details_data = json.load(f)
        except Exception:
            pass

    # 2. 抓取 trees
    trees_count = 0
    if not os.path.exists(trees_path):
        t_url = f"https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/national_lesson/trees/{mat_id}.json"
        trees_data = fetch_json(t_url)
        if trees_data is not None:
            with open(trees_path, "w", encoding="utf-8") as f:
                json.dump(trees_data, f, ensure_ascii=False, indent=2)
            trees_count = len(trees_data) if isinstance(trees_data, list) else 0
    else:
        try:
            with open(trees_path, "r", encoding="utf-8") as f:
                trees_data = json.load(f)
                trees_count = (
                    len(trees_data) if isinstance(trees_data, list) else 0
                )
        except Exception:
            pass

    # 提取标签维度
    dim_map = {
        "zxxxd": "学段",
        "zxxxk": "学科",
        "zxxbb": "版本",
        "zxxcc": "册次",
        "zxxnj": "年级",
    }
    tags_info = {}
    for t in mat.get("tag_list", []):
        dim = t.get("tag_dimension_id")
        if dim in dim_map:
            tags_info[dim_map[dim]] = t.get("tag_name")

    return {
        "id": mat_id,
        "title": title,
        "学段": tags_info.get("学段", ""),
        "学科": tags_info.get("学科", ""),
        "版本": tags_info.get("版本", ""),
        "年级": tags_info.get("年级", ""),
        "册次": tags_info.get("册次", ""),
        "章节数": trees_count,
    }


def step3_and_4_fetch_details_and_trees(materials: list):
    print("\n" + "=" * 50)
    print(
        f"【阶段 3 & 4】开始多线程爬取 {len(materials)} 本教材的 Details 和 Trees..."
    )
    os.makedirs(os.path.join(OUTPUT_DIR, "3_details"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "4_trees"), exist_ok=True)

    catalog_rows = []
    total = len(materials)
    completed = 0

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(download_single_material, m): m for m in materials
        }
        for future in as_completed(futures):
            res = future.result()
            if res:
                catalog_rows.append(res)
            completed += 1
            if completed % 100 == 0 or completed == total:
                elapsed = time.time() - t0
                speed = completed / elapsed if elapsed > 0 else 0
                print(
                    f"  进度: [{completed}/{total}] ({completed/total*100:.1f}%) - 速度: {speed:.1f} 本/秒"
                )

    # 导出汇总目录 catalog.csv
    csv_path = os.path.join(OUTPUT_DIR, "catalog.csv")
    if catalog_rows:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(catalog_rows[0].keys()))
            writer.writeheader()
            writer.writerows(catalog_rows)
        print(f"\n✓ 阶段 3 & 4 完成：已生成总索引清单 {csv_path}")


# ========================================================
# 辅助功能：根据页面 URL 的 defaultTag 只爬单本教材
# ========================================================
