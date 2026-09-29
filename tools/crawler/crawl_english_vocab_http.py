"""URL normalization and cached metadata downloads for the crawler."""
from __future__ import annotations

import json
import os
import time
import urllib.request

if __package__:
    from .crawl_english_vocab_config import DATA_DIR, PARTS_DIR, HEADERS
else:
    from crawl_english_vocab_config import DATA_DIR, PARTS_DIR, HEADERS


def clean_url(raw_url: str) -> str:
    parts = urllib.parse.urlsplit(raw_url)
    path = urllib.parse.quote(parts.path, safe="/")
    query = urllib.parse.quote(parts.query, safe="=&?")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def fetch_json(url: str, retries: int = 3, timeout: int = 15):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(clean_url(url), headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(1)
    return None


def fetch_all_materials():
    """获取所有教材清单，支持本地缓存"""
    os.makedirs(PARTS_DIR, exist_ok=True)
    summary_file = os.path.join(DATA_DIR, "all_tch_materials.json")
    if os.path.exists(summary_file):
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    version_url = "https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/resources/tch_material/version/data_version.json"
    v_data = fetch_json(version_url)
    if not v_data:
        raise RuntimeError("无法获取教材版本索引文件")

    raw_urls = v_data.get("urls", "")
    if isinstance(raw_urls, str):
        part_urls = [u.strip() for u in raw_urls.split(",") if u.strip()]
    else:
        part_urls = list(raw_urls)

    all_materials = []
    for p_url in part_urls:
        filename = p_url.split("/")[-1]
        p_path = os.path.join(PARTS_DIR, filename)
        p_data = None
        if os.path.exists(p_path):
            try:
                with open(p_path, "r", encoding="utf-8") as f:
                    p_data = json.load(f)
            except Exception:
                pass
        if not p_data:
            p_data = fetch_json(p_url)
            if p_data:
                with open(p_path, "w", encoding="utf-8") as f:
                    json.dump(p_data, f, ensure_ascii=False, indent=2)
        if p_data:
            all_materials.extend(p_data)

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_materials, f, ensure_ascii=False, indent=2)

    return all_materials

