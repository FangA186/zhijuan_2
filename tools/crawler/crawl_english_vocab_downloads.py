"""Image download and per-material crawl orchestration."""
from __future__ import annotations

import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

if __package__:
    from .crawl_english_vocab_config import HEADERS
    from .crawl_english_vocab_http import clean_url
    from .crawl_english_vocab_detail import get_material_detail
    from .crawl_english_vocab_metadata import build_folder_path
else:
    from crawl_english_vocab_config import HEADERS
    from crawl_english_vocab_http import clean_url
    from crawl_english_vocab_detail import get_material_detail
    from crawl_english_vocab_metadata import build_folder_path


def download_image(url: str, out_path: str, retries: int = 3):
    """下载单张图片并落盘（已存在且有效则跳过）"""
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
        return True, "已存在"

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    temp_path = out_path + ".tmp"

    for attempt in range(retries):
        try:
            req = urllib.request.Request(clean_url(url), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                if len(data) > 500:
                    with open(temp_path, "wb") as f:
                        f.write(data)
                    os.replace(temp_path, out_path)
                    return True, "下载成功"
        except Exception as e:
            if attempt == retries - 1:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
                return False, str(e)
            time.sleep(0.5)
    return False, "重试耗尽"


def process_material(meta, is_duplicate_group, output_base_dir, num_pages=30, workers=4, clean_target=False):
    """处理单个教材：解析详情并下载倒数指定页数（默认 30 页）"""
    mat_id = meta["id"]
    detail = get_material_detail(mat_id)
    if not detail or not detail["base_url"]:
        return {
            "id": mat_id,
            "title": meta["title"],
            "status": "FAIL",
            "message": "无法获取图片预览或页数信息",
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
        }

    total_pages = detail["pagesize"]
    base_url = detail["base_url"]
    count_to_take = min(num_pages, total_pages)
    start_page = max(1, total_pages - count_to_take + 1)
    end_page = total_pages

    # 目标目录
    rel_folder = build_folder_path(meta, is_duplicate_group)
    target_dir = os.path.join(output_base_dir, rel_folder)
    os.makedirs(target_dir, exist_ok=True)

    if clean_target:
        for f in os.listdir(target_dir):
            if f.endswith(".jpg") or f.endswith(".tmp") or f == ".vocab_meta.json":
                try:
                    os.remove(os.path.join(target_dir, f))
                except Exception:
                    pass

    # 准备下载任务列表（按真实页码顺序排布）
    # 序号格式：01_page_069.jpg ~ 30_page_098.jpg
    # 保证严格字典序与真实书本页码一致，绝不混乱
    tasks = []
    page_numbers = list(range(start_page, end_page + 1))
    for idx, page in enumerate(page_numbers, 1):
        img_url = f"{base_url}{page}.jpg"
        filename = f"{idx:02d}_page_{page:03d}.jpg"
        out_path = os.path.join(target_dir, filename)
        tasks.append((img_url, out_path))

    downloaded = 0
    skipped = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(download_image, url, path) for url, path in tasks]
        for fut in as_completed(futures):
            ok, msg = fut.result()
            if ok:
                if msg == "已存在":
                    skipped += 1
                else:
                    downloaded += 1
            else:
                failed += 1

    return {
        "id": mat_id,
        "title": meta["title"],
        "folder": rel_folder,
        "total_pages": total_pages,
        "page_range": f"{start_page}..{end_page}",
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "status": "PASS" if failed == 0 else "PARTIAL",
    }

