"""Path guards and image-list operations for the local vocabulary viewer."""
from __future__ import annotations

import os
import re
from pathlib import Path

BASE_DIR = os.path.abspath("./教材单词图片")
TRASH_DIR = os.path.join(BASE_DIR, ".trash")


def get_safe_path(rel_path: str) -> str:
    """防止目录穿越漏洞，严格限制在 BASE_DIR 之内"""
    rel_path = rel_path.lstrip("/\\")
    base = Path(BASE_DIR).resolve()
    full_path = (base / rel_path).resolve()
    if not full_path.is_relative_to(base):
        raise PermissionError("Access denied: path traversal detected")
    return str(full_path)


def get_safe_trash_path(rel_path: str) -> str:
    """防止目录穿越漏洞，严格限制在 TRASH_DIR 之内"""
    rel_path = rel_path.lstrip("/\\")
    base = Path(TRASH_DIR).resolve()
    full_path = (base / rel_path).resolve()
    if not full_path.is_relative_to(base):
        raise PermissionError("Access denied: path traversal detected")
    return str(full_path)


def list_trash_images(rel_path: str = ""):
    """列出回收站中的图片列表（可按册次过滤）"""
    if not os.path.exists(TRASH_DIR):
        return []

    if rel_path:
        target_dir = get_safe_trash_path(rel_path)
        if not os.path.isdir(target_dir):
            return []
        files = [f for f in os.listdir(target_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        files.sort()
        items = []
        for f in files:
            f_path = os.path.join(target_dir, f)
            try:
                get_safe_trash_path(os.path.relpath(f_path, TRASH_DIR))
            except PermissionError:
                continue
            stat = os.stat(f_path)
            m_page = re.search(r"page_(\d+)", f)
            page_num = int(m_page.group(1)) if m_page else None
            m_idx = re.search(r"^(\d+)", f)
            idx_num = int(m_idx.group(1)) if m_idx else None
            items.append({
                "filename": f,
                "rel_file_path": os.path.relpath(f_path, TRASH_DIR),
                "size_kb": round(stat.st_size / 1024, 1),
                "page_num": page_num,
                "idx_num": idx_num,
            })
        return items
    else:
        items = []
        for root, _, fns in os.walk(TRASH_DIR):
            for f in sorted(fns):
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    f_path = os.path.join(root, f)
                    try:
                        get_safe_trash_path(os.path.relpath(f_path, TRASH_DIR))
                    except PermissionError:
                        continue
                    stat = os.stat(f_path)
                    m_page = re.search(r"page_(\d+)", f)
                    page_num = int(m_page.group(1)) if m_page else None
                    m_idx = re.search(r"^(\d+)", f)
                    idx_num = int(m_idx.group(1)) if m_idx else None
                    items.append({
                        "filename": f,
                        "rel_file_path": os.path.relpath(f_path, TRASH_DIR),
                        "size_kb": round(stat.st_size / 1024, 1),
                        "page_num": page_num,
                        "idx_num": idx_num,
                    })
        return items


def list_book_images(rel_path: str):
    """列出某一册次目录下的全部图片详情"""
    full_path = get_safe_path(rel_path)
    if not os.path.isdir(full_path):
        return []

    files = [f for f in os.listdir(full_path) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    files.sort()

    items = []
    for f in files:
        f_path = os.path.join(full_path, f)
        try:
            get_safe_path(os.path.relpath(f_path, BASE_DIR))
        except PermissionError:
            continue
        stat = os.stat(f_path)
        m_page = re.search(r"page_(\d+)", f)
        page_num = int(m_page.group(1)) if m_page else None
        m_idx = re.search(r"^(\d+)", f)
        idx_num = int(m_idx.group(1)) if m_idx else None

        items.append({
            "filename": f,
            "rel_file_path": os.path.relpath(f_path, BASE_DIR),
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 1),
            "page_num": page_num,
            "idx_num": idx_num,
        })
    return items
