#!/usr/bin/env python3
"""
批量下载中小学智慧教育平台教材封面脚本
读取 smartedu_data/2_materials_list/all_materials.json，多线程下载封面到 smartedu_data/covers/
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = "./smartedu_data"
MATERIALS_FILE = os.path.join(DATA_DIR, "2_materials_list", "all_materials.json")
COVERS_DIR = os.path.join(DATA_DIR, "covers")
MAX_WORKERS = 16

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # 关键：空 Referer 避开 CDN 防盗链 403
    "Referer": ""
}

def clean_url(raw_url: str) -> str:
    """自动转义 URL 中的中文字符、特殊符号及空格，避免 urllib InvalidURL / UnicodeEncodeError"""
    parts = urllib.parse.urlsplit(raw_url)
    path = urllib.parse.quote(parts.path, safe='/')
    query = urllib.parse.quote(parts.query, safe='=&?')
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))

def extract_thumb(mat):
    if mat.get("thumb"):
        return mat["thumb"]
    custom_props = mat.get("custom_properties") or {}
    thumbs = custom_props.get("thumbnails") or []
    if thumbs:
        return thumbs[0]
    return ""

def download_one(mat):
    os.makedirs(COVERS_DIR, exist_ok=True)
    mat_id = mat.get("id")
    raw_thumb = extract_thumb(mat)
    if not raw_thumb or not mat_id:
        return False, "官方未提供封面"
    
    out_path = os.path.join(COVERS_DIR, f"{mat_id}.jpg")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
        return True, "已存在"

    encoded_url = clean_url(raw_thumb)

    for attempt in range(3):
        try:
            req = urllib.request.Request(encoded_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                if len(data) > 500:
                    with open(out_path, "wb") as f:
                        f.write(data)
                    return True, "下载成功"
        except Exception as e:
            if attempt == 2:
                return False, str(e)
            time.sleep(0.5)
    return False, "重试耗尽"

def main():
    if not os.path.exists(MATERIALS_FILE):
        print(f"[错误] 找不到材料列表: {MATERIALS_FILE}")
        sys.exit(1)

    with open(MATERIALS_FILE, "r", encoding="utf-8") as f:
        materials = json.load(f)

    os.makedirs(COVERS_DIR, exist_ok=True)
    total = len(materials)
    print(f"==================================================")
    print(f"开始批量下载教材封面 (共 {total} 本教材)")
    print(f"存储目录: {os.path.abspath(COVERS_DIR)}")
    print(f"并发线程: {MAX_WORKERS}")
    print(f"==================================================")

    success_cnt = 0
    skip_cnt = 0
    no_thumb_cnt = 0
    fail_cnt = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_one, mat): mat for mat in materials}
        for i, fut in enumerate(as_completed(futures), 1):
            ok, msg = fut.result()
            if ok:
                if msg == "已存在":
                    skip_cnt += 1
                else:
                    success_cnt += 1
            else:
                if msg == "官方未提供封面":
                    no_thumb_cnt += 1
                else:
                    fail_cnt += 1

            if i % 100 == 0 or i == total:
                print(f"进度: [{i}/{total}] 新增下载: {success_cnt}, 已存在跳过: {skip_cnt}, 平台无封面: {no_thumb_cnt}, 异常失败: {fail_cnt}")

    print(f"\n✓ 下载流程结束！")
    print(f"  - 新增下载成功: {success_cnt}")
    print(f"  - 原已存在跳过: {skip_cnt}")
    print(f"  - 官方平台原本无封面: {no_thumb_cnt}")
    print(f"  - 真实网络异常失败: {fail_cnt}")

if __name__ == "__main__":
    main()
