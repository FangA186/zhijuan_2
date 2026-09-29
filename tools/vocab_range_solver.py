"""Select the contiguous textbook vocabulary section."""
from typing import Dict, List, Optional, Tuple

def solve_vocab_range(pages_features: List[Dict]) -> Optional[Tuple[int, int]]:
    """
    基于全书页面特征，求解单词表的连续区间 [start_idx, end_idx]。
    """
    n = len(pages_features)
    if n == 0:
        return None

    # 1. 寻找候选起始位置
    start_idx = None

    # 策略 A: 寻找首个明确的 is_start_header
    for i in range(n):
        p = pages_features[i]
        if p["is_start_header"] and not p["is_copyright"] and not p["is_non_vocab_header"]:
            start_idx = i
            break

    # 策略 B: 检查起始位置之前是否本来就已经是单词表（例如下载的 30 页截断在词汇表中间）
    # 若首个候选本来就是明确的 is_start_header，则无需向前越界回退到发音规则/正文页
    has_explicit_start_header = pages_features[start_idx]["is_start_header"] if start_idx is not None else False
    if not has_explicit_start_header and start_idx is not None and start_idx > 0:
        cur = start_idx - 1
        while cur >= 0:
            p = pages_features[cur]
            if p["is_copyright"] or p["is_non_vocab_header"] or p["score"] < 5.0:
                break
            start_idx = cur
            cur -= 1
    elif start_idx is None:
        # 策略 C: 没有明确标题时，寻找第一个词汇特征强劲且无干扰的页面
        for i in range(n):
            p = pages_features[i]
            if not p["is_copyright"] and not p["is_non_vocab_header"]:
                if p["score"] >= 12.0 or p["pos_count"] >= 6 or p["vocab_pairs"] >= 6:
                    start_idx = i
                    break

    if start_idx is None:
        return None

    # 2. 寻找候选结束位置
    end_idx = start_idx
    for i in range(start_idx, n):
        p = pages_features[i]
        if p["is_copyright"]:
            break
        if p["is_non_vocab_header"] and p["score"] < 0:
            break

        if p["score"] <= 0 and p["pos_count"] == 0 and p["vocab_pairs"] == 0:
            has_subsequent_vocab = False
            for j in range(i + 1, min(i + 3, n)):
                if pages_features[j]["score"] >= 8.0 or pages_features[j]["is_vocab_header"]:
                    has_subsequent_vocab = True
                    break
            if not has_subsequent_vocab:
                break

        end_idx = i

    return start_idx, end_idx


