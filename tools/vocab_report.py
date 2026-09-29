"""Human-readable summaries for vocabulary scan results."""
from typing import Dict, List

def print_report(results: List[Dict]):
    """打印全库单词表识别统计报告"""
    total_books = len(results)
    detected_books = sum(1 for r in results if r.get("detected"))
    total_images = sum(r.get("total_pages", 0) for r in results)
    vocab_images = sum(r.get("vocab_count", 0) for r in results)
    non_vocab_images = sum(r.get("non_vocab_count", 0) for r in results)

    print("\n" + "=" * 75)
    print(" 📊 知卷 - 全国英语教材单词表智能识别统计报告")
    print("=" * 75)
    print(f" 教材总册数:        {total_books:6d} 册")
    print(f" 成功定位单词表:    {detected_books:6d} 册 (定位率: {detected_books/max(1, total_books)*100:.1f}%)")
    print(f" 未能自动定位:      {total_books - detected_books:6d} 册")
    print("-" * 75)
    print(f" 现有图片总数:      {total_images:6d} 张")
    print(f" 核心单词表图片:    {vocab_images:6d} 张 (占 {vocab_images/max(1, total_images)*100:.1f}%)")
    print(f" 可清理非单词图片:  {non_vocab_images:6d} 张 (占 {non_vocab_images/max(1, total_images)*100:.1f}%)")
    print("=" * 75)

    # 打印部分未能定位的教材以便人工关注
    undetected = [r for r in results if not r.get("detected") and r.get("total_pages", 0) > 0]
    if undetected:
        print(f"\n⚠️ 共有 {len(undetected)} 册教材未检测到常规单词表，建议在 Web 端人工审查：")
        for u in undetected[:15]:
            print(f"   - {u.get('rel_path')} ({u.get('total_pages')} 页)")
        if len(undetected) > 15:
            print(f"   ... 及另外 {len(undetected) - 15} 册")


