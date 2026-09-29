"""Choose explicit curriculum targets, balanced across selected chapter families."""
import json
import re
from pathlib import Path

GENERIC_TOPICS = frozenset(json.loads((Path(__file__).resolve().parents[2] / 'configs/template-topic-labels.json').read_text()))
NUMBER = re.compile(r'^(\d+(?:\.\d+)*)(?!\d)')
CHAPTER = re.compile(r'^第[一二三四五六七八九十百\d]+[章单元]')
AUXILIARY = re.compile(r'^(小结|复习参考题|阅读与思考|文献阅读|信息技术应用|数学探究)|习题课$')


def topic_number(topic):
    match = NUMBER.match(topic.strip())
    return match.group(1) if match else None


def topic_pool(topics):
    """Prefer child nodes to their selected parent; never invent a curriculum item."""
    numbers = [topic_number(t) for t in topics]
    leaves = [t for t, number in zip(topics, numbers)
              if not number or not any(n and n.startswith(number + '.') for n in numbers)]
    if any(topic_number(t) for t in leaves):
        leaves = [t for t in leaves if not CHAPTER.match(t) and not AUXILIARY.search(t)]
    return leaves or topics


def choose_topic(topics, topic_counts, chapter_counts):
    pool = topic_pool(topics)
    def family(topic):
        number = topic_number(topic)
        return number.split('.')[0] if number else topic
    chosen = min(pool, key=lambda t: (topic_counts.get(t, 0), chapter_counts.get(family(t), 0), pool.index(t)))
    topic_counts[chosen] = topic_counts.get(chosen, 0) + 1
    group = family(chosen)
    chapter_counts[group] = chapter_counts.get(group, 0) + 1
    return chosen
