#!/usr/bin/env python3
"""
知卷 - 教材单词表全库批量智能扫描与清洗工具 (Smart Filter Vocab CLI)

功能：
1. --scan-all: 多进程/多线程并发扫描全库 367 本教材，生成 .vocab_meta.json 本地缓存。
2. --report: 生成全库单词表识别报告（包含识别率、词汇页总数、建议清理页总数）。
3. --auto-clean: 批量将所有已识别出的非单词页自动移入 .trash 回收站。
4. --dry-run: 模拟预览清理操作，不改变任何本地磁盘文件。
"""

import argparse
import concurrent.futures
import json
import os
import shutil
import sys
import time
from typing import Dict, List

# 确保能直接导入同目录下的 vocab_detector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vocab_detector import BASE_DIR, detect_vocab_in_book
from vocab_report import print_report

TRASH_DIR = os.path.join(BASE_DIR, ".trash")


def find_all_textbook_dirs() -> List[str]:
    """发现教材单词图片目录下的所有教材终端目录"""
    book_dirs = []
    for root, dirs, files in os.walk(BASE_DIR):
        if root.startswith(TRASH_DIR) or ".trash" in root:
            continue
        jpgs = [f for f in files if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if jpgs:
            rel_p = os.path.relpath(root, BASE_DIR)
            book_dirs.append(rel_p)
    book_dirs.sort()
    return book_dirs


def scan_single_book(rel_path: str, force_refresh: bool = False) -> Dict:
    """扫描单本教材并返回结果"""
    res = detect_vocab_in_book(rel_path, force_refresh=force_refresh)
    res["rel_path"] = rel_path
    return res


def run_batch_scan(book_dirs: List[str], max_workers: int = 6, force_refresh: bool = False) -> List[Dict]:
    """多线程并发全库扫描"""
    total = len(book_dirs)
    print(f"🚀 开始全库智能扫描，共 {total} 本教材，并发线程数: {max_workers}")
    t0 = time.time()
    results = []
    completed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_book = {
            executor.submit(scan_single_book, b, force_refresh): b for b in book_dirs
        }
        for future in concurrent.futures.as_completed(future_to_book):
            b_name = future_to_book[future]
            completed += 1
            try:
                data = future.result()
                results.append(data)
                status_icon = "✅" if data.get("detected") else "⚠️"
                summary = data.get("summary", "")
                if completed % 10 == 0 or completed == total:
                    pct = (completed / total) * 100
                    elapsed = time.time() - t0
                    print(f"[{completed:3d}/{total:3d} {pct:5.1f}%] (耗时 {elapsed:.1f}s) {status_icon} {b_name} -> {summary}")
            except Exception as exc:
                print(f"[{completed:3d}/{total:3d}] ❌ {b_name} 扫描失败: {exc}")

    elapsed = time.time() - t0
    print(f"\n✨ 全库扫描完成！共处理 {len(results)} 本教材，总耗时: {elapsed:.2f} 秒 (平均单本: {elapsed/max(1, total):.2f}s)")
    return results


def run_auto_clean(results: List[Dict], dry_run: bool = True, use_trash: bool = True):
    """自动清理所有检测到的非单词页"""
    action_name = "【模拟预览】" if dry_run else "【执行清洗】"
    dest_name = "移至回收站 (.trash)" if use_trash else "直接永久删除"
    print(f"\n🧹 开始批量清洗非单词页 {action_name} 目标: {dest_name}")

    total_cleaned = 0
    total_skipped = 0

    for r in results:
        if not r.get("detected"):
            continue

        non_vocab_files = r.get("non_vocab_files", [])
        if not non_vocab_files:
            continue

        for rel_f in non_vocab_files:
            full_src = os.path.abspath(os.path.join(BASE_DIR, rel_f))
            if not os.path.exists(full_src):
                total_skipped += 1
                continue

            if not dry_run:
                try:
                    if use_trash:
                        full_dst = os.path.join(TRASH_DIR, rel_f)
                        os.makedirs(os.path.dirname(full_dst), exist_ok=True)
                        shutil.move(full_src, full_dst)
                    else:
                        os.remove(full_src)
                    total_cleaned += 1
                except Exception as e:
                    print(f"❌ 清洗失败 {rel_f}: {e}")
            else:
                total_cleaned += 1

    if dry_run:
        print(f"\n💡 预览完成：共计将清洗 {total_cleaned} 张非单词页（若要实际执行，请加上 --execute 参数）")
    else:
        print(f"\n🎉 清洗完成！已成功将 {total_cleaned} 张非单词页{dest_name}！可在 Web 工作台随时撤销恢复。")


def main():
    parser = argparse.ArgumentParser(description="知卷 - 教材单词表全库智能扫描与批量清洗工具")
    parser.add_argument("--scan-all", action="store_true", help="全库并发扫描并建立缓存")
    parser.add_argument("--report", action="store_true", help="输出全库识别统计报告")
    parser.add_argument("--auto-clean", action="store_true", help="自动清洗检测出的非单词页")
    parser.add_argument("--execute", action="store_true", help="确认实际执行磁盘删除（默认仅为 dry-run 预览）")
    parser.add_argument("--no-trash", action="store_true", help="直接从磁盘永久删除（不移至回收站，谨慎使用）")
    parser.add_argument("--workers", type=int, default=6, help="并发扫描线程数 (默认: 6)")
    parser.add_argument("--force", action="store_true", help="忽略已有缓存重新扫描")
    parser.add_argument("--book", type=str, default="", help="仅针对指定单本教材操作")

    args = parser.parse_args()

    if args.book:
        target = args.book.lstrip("/\\")
        print(f"🔍 针对单本教材执行操作: {target}")
        res = scan_single_book(target, force_refresh=args.force)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return

    book_dirs = find_all_textbook_dirs()
    if not book_dirs:
        print(f"未在 {BASE_DIR} 下找到任何教材图片目录！")
        return

    if args.scan_all or args.report or args.auto_clean:
        # 加载或扫描所有教材
        results = []
        books_to_scan = []

        if not args.force:
            for b in book_dirs:
                cache_f = os.path.join(BASE_DIR, b, ".vocab_meta.json")
                if os.path.exists(cache_f):
                    try:
                        with open(cache_f, "r", encoding="utf-8") as f:
                            d = json.load(f)
                            d["rel_path"] = b
                            results.append(d)
                            continue
                    except Exception:
                        pass
                books_to_scan.append(b)
        else:
            books_to_scan = book_dirs

        if books_to_scan:
            print(f"📦 已有缓存: {len(results)} 本，需新扫描: {len(books_to_scan)} 本")
            scanned = run_batch_scan(books_to_scan, max_workers=args.workers, force_refresh=args.force)
            results.extend(scanned)
        else:
            print(f"⚡ 全库 {len(results)} 本教材已全部命中本地缓存！")

        print_report(results)

        if args.auto_clean:
            run_auto_clean(results, dry_run=not args.execute, use_trash=not args.no_trash)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
