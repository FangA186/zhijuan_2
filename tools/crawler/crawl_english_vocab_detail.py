"""Read cached textbook details and determine the final available image page."""
from __future__ import annotations

import json
import os
import re
import urllib.request

if __package__:
    from .crawl_english_vocab_config import DETAILS_DIR, HEADERS
    from .crawl_english_vocab_http import fetch_json
else:
    from crawl_english_vocab_config import DETAILS_DIR, HEADERS
    from crawl_english_vocab_http import fetch_json


def get_material_detail(mat_id: str):
    """获取教材详情（提取 pagesize 及预览图片 URL 前缀）"""
    os.makedirs(DETAILS_DIR, exist_ok=True)
    detail_file = os.path.join(DETAILS_DIR, f"{mat_id}.json")
    detail_data = None
    if os.path.exists(detail_file):
        try:
            with open(detail_file, "r", encoding="utf-8") as f:
                detail_data = json.load(f)
        except Exception:
            pass

    if not detail_data:
        url = f"https://s-file-1.ykt.cbern.com.cn/zxx/ndrv2/resources/tch_material/details/{mat_id}.json"
        detail_data = fetch_json(url)
        if detail_data:
            with open(detail_file, "w", encoding="utf-8") as f:
                json.dump(detail_data, f, ensure_ascii=False, indent=2)

    if not detail_data:
        return None

    # 提取真实总页数 pagesize
    pagesize = None
    for ti in detail_data.get("ti_items", []):
        for req_item in ti.get("custom_properties", {}).get("requirements", []):
            if req_item.get("name") == "pagesize":
                try:
                    pagesize = int(req_item.get("value"))
                except Exception:
                    pass
                break
        if pagesize:
            break

    base_url = None
    for ti in detail_data.get("ti_items", []):
        if ti.get("ti_file_flag") == "image" or ti.get("lc_ti_format") == "image/jpg":
            storages = ti.get("ti_storages", [])
            for s in storages:
                u = s.replace("-private", "")
                if not u.endswith("/"):
                    u += "/"
                base_url = u
                break
            if base_url:
                break

    preview = detail_data.get("custom_properties", {}).get("preview", {})
    if not base_url:
        if not preview:
            return None
        sample_url = list(preview.values())[0]
        base_url = re.sub(r"/\d+\.jpg$", "/", sample_url)

    if not pagesize:
        pagesize = len(preview) if preview else 100
    else:
        # 校验真实末页是否存在（部分教材元数据包含末尾1~3页空白页未转码）
        pagesize = resolve_real_last_page(base_url, pagesize)

    return {
        "pagesize": pagesize,
        "base_url": base_url,
        "preview_count": len(preview),
    }


def resolve_real_last_page(base_url: str, nominal_pagesize: int) -> int:
    """探测 CDN 真实存在的最后一页页码"""
    curr = nominal_pagesize
    while curr > 1:
        req = urllib.request.Request(f"{base_url}{curr}.jpg", headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    return curr
        except Exception:
            curr -= 1
            if nominal_pagesize - curr > 25:
                # 保护：若连续25页都不存在，则回退
                break
    return nominal_pagesize

