"""Same-paper public stems only; textual similarity is a warning, not semantic proof."""
import re
import unicodedata
from difflib import SequenceMatcher


def stem(question):
    if not isinstance(question, dict) or not isinstance(question.get('prompt', []), list):
        return ''
    return '\n'.join(str(block.get('text') or block.get('latex') or '') for block in question.get('prompt', []) if isinstance(block, dict))


def normalize(text):
    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'[（(](?:本[题小卷].*?)?原创[^)）]*[)）]', '', text)
    text = re.sub(r'本题为原创生成题[.。]?', '', text)
    text = re.sub(r'\\(?:left|right)', '', text)
    return re.sub(r'\s+', '', text)


def same_paper_check(question, previous):
    current = normalize(stem(question))
    if not current:
        return 'REVIEW', '题干不足以检查同卷重复'
    similar = None
    for other in previous:
        if other.get('local_id') == question.get('local_id'):
            continue
        old = normalize(stem(other))
        if old and old == current:
            return 'FAIL', f"与本卷 {other.get('local_id')} 的题干相同，须重新设计本题"
        if min(len(current), len(old)) >= 20 and SequenceMatcher(None, current, old, autojunk=False).ratio() >= .82:
            similar = f"与本卷 {other.get('local_id')} 题干高度相似，需审核条件与解题任务是否重复"
    if similar:
        return 'REVIEW', similar
    return 'PASS', '未发现文本相同或高度相似的已生成题干；不代表语义多样性已获证明'


def public_summaries(previous):
    return [{'local_id': q.get('local_id'), 'kind': q.get('kind'), 'stem': stem(q)[:700]} for q in previous]
