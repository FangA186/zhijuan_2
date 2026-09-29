"""Local delete-to-trash and restore operations for the vocabulary viewer."""
from __future__ import annotations

import os
import shutil

if __package__:
    from .vocab_viewer_paths import BASE_DIR, TRASH_DIR, get_safe_path, get_safe_trash_path
else:
    from vocab_viewer_paths import BASE_DIR, TRASH_DIR, get_safe_path, get_safe_trash_path


def delete_files(file_rel_paths, use_trash=True):
    """批量或单张删除本地图片（默认移至回收站，支持恢复）"""
    deleted = []
    failed = []
    affected_dirs = set()

    for rel_f in file_rel_paths:
        try:
            full_src = get_safe_path(rel_f)
            if not os.path.exists(full_src):
                continue

            affected_dirs.add(os.path.dirname(full_src))
            if use_trash:
                full_dst = get_safe_trash_path(rel_f)
                os.makedirs(os.path.dirname(full_dst), exist_ok=True)
                shutil.move(full_src, full_dst)
            else:
                os.remove(full_src)
            deleted.append(rel_f)
        except Exception as e:
            failed.append({"file": rel_f, "error": str(e)})

    # 清理受影响目录的智能识别缓存
    for d in affected_dirs:
        cache_f = os.path.join(d, ".vocab_meta.json")
        if os.path.exists(cache_f):
            try:
                os.remove(cache_f)
            except Exception:
                pass

    return {"deleted": deleted, "failed": failed, "success": len(failed) == 0}


def restore_trash_files(file_rel_paths=None):
    """恢复回收站中的文件（不指定则全部恢复）"""
    if not os.path.exists(TRASH_DIR):
        return {"restored": 0}

    restored_count = 0
    affected_dirs = set()
    failed = []
    if file_rel_paths is None:
        for root, _, files in os.walk(TRASH_DIR):
            for f in files:
                rel_p = os.path.relpath(os.path.join(root, f), TRASH_DIR)
                try:
                    trash_file = get_safe_trash_path(rel_p)
                    target_p = get_safe_path(rel_p)
                except PermissionError as exc:
                    failed.append({"file": rel_p, "error": str(exc)})
                    continue
                os.makedirs(os.path.dirname(target_p), exist_ok=True)
                shutil.move(trash_file, target_p)
                restored_count += 1
                affected_dirs.add(os.path.dirname(target_p))
    else:
        for rel_f in file_rel_paths:
            try:
                trash_file = get_safe_trash_path(rel_f)
                target_p = get_safe_path(rel_f)
            except PermissionError as exc:
                failed.append({"file": rel_f, "error": str(exc)})
                continue
            if os.path.exists(trash_file):
                os.makedirs(os.path.dirname(target_p), exist_ok=True)
                shutil.move(trash_file, target_p)
                restored_count += 1
                affected_dirs.add(os.path.dirname(target_p))

    for d in affected_dirs:
        cache_f = os.path.join(d, ".vocab_meta.json")
        if os.path.exists(cache_f):
            try:
                os.remove(cache_f)
            except Exception:
                pass

    return {"restored": restored_count, "failed": failed}
