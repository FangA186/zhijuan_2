"""Defaults and official metadata dimensions for the SmartEdu vocabulary crawler."""
import os

DATA_DIR = "./smartedu_data/tch_material"
DETAILS_DIR = os.path.join(DATA_DIR, "details")
PARTS_DIR = os.path.join(DATA_DIR, "parts")
DEFAULT_OUTPUT_DIR = "./教材单词图片"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "",
}

DIM_MAP = {
    "zxxxd": "学段",
    "zxxxk": "学科",
    "zxxbb": "版本",
    "zxxcc": "册次",
    "zxxnj": "年级",
}
