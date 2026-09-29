"""Shared fetch and output paths for the SmartEdu catalog crawler."""
import json
from pathlib import Path
import time
import urllib.request

OUTPUT_DIR = str(Path(__file__).resolve().parents[2] / "smartedu_data")
MAX_WORKERS = 16
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_json(url: str, retries: int = 3):
    """带重试机制的 JSON 请求工具函数"""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                print(f"[错误] 请求失败 ({url}): {e}")
                return None
            time.sleep(1)


# ========================================================
# 阶段 1：获取维度分类树 (national_lesson_tag.json)
# ========================================================
