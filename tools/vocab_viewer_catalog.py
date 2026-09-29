"""Filesystem catalog tree and counts for the vocabulary viewer."""
from __future__ import annotations

from collections import defaultdict
import os

if __package__:
    from .vocab_viewer_paths import BASE_DIR, TRASH_DIR
else:
    from vocab_viewer_paths import BASE_DIR, TRASH_DIR


def build_catalog_tree():
    """扫描 BASE_DIR 生成完整的层级目录树与统计数据（支持按版本与按年级双重视角）"""
    if not os.path.exists(BASE_DIR):
        return {"stages": [], "by_grade": [], "total_images": 0, "total_books": 0}

    stages_data = []
    by_grade_stages = []
    total_images = 0
    total_books = 0

    grade_order = ["一年级", "二年级", "三年级", "四年级", "五年级", "六年级", "七年级", "八年级", "九年级"]
    stage_order = ["小学", "初中", "初中（五·四学制）", "小学（五·四学制）", "高中"]
    found_stages = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d)) and not d.startswith(".") and not d.endswith("备份")]
    found_stages.sort(key=lambda x: stage_order.index(x) if x in stage_order else 99)

    for st in found_stages:
        st_path = os.path.join(BASE_DIR, st)
        editions_data = []
        st_img_count = 0
        st_book_count = 0

        grades_map = defaultdict(lambda: defaultdict(list))

        for ed in sorted(os.listdir(st_path)):
            ed_path = os.path.join(st_path, ed)
            if not os.path.isdir(ed_path) or ed.startswith("."):
                continue

            if st == "高中":
                terms_data = []
                for tm in sorted(os.listdir(ed_path)):
                    tm_path = os.path.join(ed_path, tm)
                    if not os.path.isdir(tm_path) or tm.startswith("."):
                        continue
                    imgs = [f for f in os.listdir(tm_path) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
                    c = len(imgs)
                    total_images += c
                    st_img_count += c
                    total_books += 1
                    st_book_count += 1
                    terms_data.append({
                        "name": tm,
                        "rel_path": os.path.relpath(tm_path, BASE_DIR),
                        "count": c
                    })
                editions_data.append({
                    "name": ed,
                    "is_high_school": True,
                    "terms": terms_data,
                    "book_count": len(terms_data),
                    "img_count": sum(t["count"] for t in terms_data)
                })
            else:
                grades_data = []
                for gr in sorted(os.listdir(ed_path)):
                    gr_path = os.path.join(ed_path, gr)
                    if not os.path.isdir(gr_path) or gr.startswith("."):
                        continue
                    terms_data = []
                    for tm in sorted(os.listdir(gr_path)):
                        tm_path = os.path.join(gr_path, tm)
                        if not os.path.isdir(tm_path) or tm.startswith("."):
                            continue
                        imgs = [f for f in os.listdir(tm_path) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
                        c = len(imgs)
                        total_images += c
                        st_img_count += c
                        total_books += 1
                        st_book_count += 1
                        term_obj = {
                            "name": tm,
                            "rel_path": os.path.relpath(tm_path, BASE_DIR),
                            "count": c
                        }
                        terms_data.append(term_obj)
                        grades_map[gr][ed].append(term_obj)
                    grades_data.append({
                        "name": gr,
                        "terms": terms_data,
                        "count": sum(t["count"] for t in terms_data)
                    })
                editions_data.append({
                    "name": ed,
                    "is_high_school": False,
                    "grades": grades_data,
                    "book_count": sum(len(g["terms"]) for g in grades_data),
                    "img_count": sum(g["count"] for g in grades_data)
                })

        stages_data.append({
            "name": st,
            "editions": editions_data,
            "book_count": st_book_count,
            "img_count": st_img_count
        })

        if st == "高中":
            by_grade_stages.append({
                "name": st,
                "is_high_school": True,
                "editions": editions_data,
                "book_count": st_book_count,
                "img_count": st_img_count
            })
        else:
            grades_list = []
            sorted_grades = sorted(grades_map.keys(), key=lambda x: grade_order.index(x) if x in grade_order else 99)
            for gr in sorted_grades:
                ed_map = grades_map[gr]
                ed_list = []
                for ed_k in sorted(ed_map.keys()):
                    tms = ed_map[ed_k]
                    ed_list.append({
                        "name": ed_k,
                        "terms": tms,
                        "count": sum(t["count"] for t in tms)
                    })
                grades_list.append({
                    "name": gr,
                    "editions": ed_list,
                    "count": sum(e["count"] for e in ed_list)
                })
            by_grade_stages.append({
                "name": st,
                "is_high_school": False,
                "grades": grades_list,
                "book_count": st_book_count,
                "img_count": st_img_count
            })

    trash_count = 0
    if os.path.exists(TRASH_DIR):
        for _, _, fns in os.walk(TRASH_DIR):
            trash_count += len([f for f in fns if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))])

    return {
        "stages": stages_data,
        "by_grade": by_grade_stages,
        "total_images": total_images,
        "total_books": total_books,
        "trash_count": trash_count
    }

