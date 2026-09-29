"""OCR page feature scoring for vocabulary detection."""
import re
from typing import Dict, List

def analyze_page_features(lines: List[str]) -> Dict:
    """分析单页 OCR 文本特征并评分"""
    if not lines:
        return {
            "score": -15.0,
            "is_start_header": False,
            "is_vocab_header": False,
            "is_non_vocab_header": False,
            "is_copyright": False,
            "pos_count": 0,
            "phonetic_count": 0,
            "vocab_pairs": 0,
            "page_type": "blank",
            "type_label": "空白/插图",
            "preview_line": "",
        }

    first_5_lines = " ".join(lines[:5]).lower()
    full_text = "\n".join(lines).lower()

    # 1. 起始标题检测
    start_headers = [
        "vocabulary in each unit",
        "words and expressions in each unit",
        "words and phrases in each unit",
        "words and chunks in each unit",
        "words and expressions in alphabetical order",
        "words and phrases in alphabetical order",
        "words and chunks in alphabetical order",
        "words and expressions",
        "words and phrases",
        "words and chunks",
        "words in each unit",
        "word list",
        "wordlist",
        "wordlist (by unit)",
        "word list (by unit)",
        "生词表",
        "词汇表",
        "单词表",
        "生词和短语",
        "vocabulary by unit",
        "unit vocabulary",
        "vocabulary list",
        "vocabulary ( i )",
        "vocabulary (i)",
        "vocabulary ( 1 )",
        "vocabulary (1)",
        "vocabulary (一)",
    ]
    is_start_header = any(h in first_5_lines for h in start_headers)
    if not is_start_header:
        if bool(re.search(r"vocabulary\s*\(\s*[i1一]\s*\)", first_5_lines)):
            is_start_header = True
        elif "vocabulary" in first_5_lines and ("unit 1" in first_5_lines or "unit i" in first_5_lines):
            is_start_header = True

    # 2. 一般词汇标题
    is_vocab_header = (
        is_start_header
        or ("vocabulary" in first_5_lines)
        or ("word list" in first_5_lines)
        or ("wordlist" in first_5_lines)
        or ("words for primary" in first_5_lines)
        or ("words and expressions" in first_5_lines)
        or ("words and phrases" in first_5_lines)
        or ("words and chunks" in first_5_lines)
    )

    # 3. 干扰标题（语法、正文、听力材料等）
    non_vocab_headers = [
        "irregular verbs",
        "grammar in use",
        "grammar focus",
        "grammar",
        "tapescripts",
        "listening scripts",
        "listening materials",
        "notes to the texts",
        "notes to the",
        "notes:",
        "guide to the language",
        "reading and thinking",
        "key sentences in each unit",
        "spelling rules",
        "phonetics and sounds",
        "pronunciation",
        "rules of reading",
        "sound families",
        "list of proper names",
        "proper names",
        "english names",
        "structures and expressions",
        "workbook",
        "fun time",
        "culture corner",
        "project",
    ]
    is_non_vocab_header = any(h in first_5_lines for h in non_vocab_headers)
    if is_start_header:
        is_non_vocab_header = False

    # 4. 版权与封底
    copyright_keywords = [
        "isbn ",
        "责任编辑",
        "定价:",
        "定价",
        "印张",
        "版权所有",
        "cip数据",
        "icphoto",
        "插图绘制",
        "本册主编",
        "著作权所有",
        "书号",
    ]
    is_copyright = any(k in full_text for k in copyright_keywords)

    # 5. 内容级特征
    pos_matches = len(re.findall(r"\b(n|v|adj|adv|prep|pron|conj|num|art|interj|vt|vi|det)\.", full_text))
    phonetic_matches = len(re.findall(r"/.*?/|\[.*?\]", "\n".join(lines)))
    unit_tags = len(re.findall(r"\bunit\s+\d+\b", full_text))
    page_tags = len(re.findall(r"\bp\.\s*\d+\b", full_text))

    # 长句子检测（课文/语法例句通常单行很长）
    long_sentences = sum(1 for l in lines if len(l) > 45 and not re.search(r"\b(n|v|adj|adv)\.", l.lower()))

    # 小学常见的中英文单词配对（如 "apple 苹果", "food 食物、食品"）
    vocab_pairs = 0
    for l in lines:
        s = l.strip()
        if re.search(r"^[a-zA-Z\s\-\']{2,20}\s+[\u4e00-\u9fa5]{1,10}$", s):
            vocab_pairs += 1
        elif re.match(r"^[a-zA-Z]{2,15}(\s+[a-zA-Z]{1,10})?\s+[\u4e00-\u9fa5\w\(\)\,\.\/\*\+\-\—\·\s]{1,25}$", s) and len(s) < 35:
            vocab_pairs += 1

    # 综合打分
    score = (
        pos_matches * 2.0
        + phonetic_matches * 1.5
        + vocab_pairs * 2.0
        + unit_tags * 2.0
        + page_tags * 1.0
        - long_sentences * 3.0
    )

    if is_start_header:
        score += 35.0
    elif is_vocab_header:
        score += 15.0

    if is_non_vocab_header:
        score -= 40.0
    if is_copyright:
        score -= 60.0

    # 初步确定页面类型
    if is_copyright:
        page_type = "copyright"
        type_label = "📌 封底版权"
    elif is_non_vocab_header and ("grammar" in first_5_lines):
        page_type = "grammar"
        type_label = "🏷️ 语法总结"
    elif is_non_vocab_header and ("irregular" in first_5_lines):
        page_type = "appendix"
        type_label = "🏷️ 不规则动词"
    elif is_non_vocab_header:
        page_type = "appendix"
        type_label = "🏷️ 附录/课文"
    elif is_start_header:
        page_type = "vocab_start"
        type_label = "⭐ 单词表首页"
    elif score >= 6.0 or pos_matches >= 6 or vocab_pairs >= 6:
        page_type = "vocab"
        type_label = "📖 单词表"
    else:
        page_type = "text"
        type_label = "📄 课文/正文"

    return {
        "score": round(score, 1),
        "is_start_header": is_start_header,
        "is_vocab_header": is_vocab_header,
        "is_non_vocab_header": is_non_vocab_header,
        "is_copyright": is_copyright,
        "pos_count": pos_matches,
        "phonetic_count": phonetic_matches,
        "vocab_pairs": vocab_pairs,
        "page_type": page_type,
        "type_label": type_label,
        "preview_line": lines[0][:40] if lines else "",
    }


