"""Topic filtering for canonical, teacher-confirmed scope."""
from __future__ import annotations


class TopicAllocator:
    @staticmethod
    def clean_topics(topics: list[str], excluded: list[str]) -> list[str]:
        excluded_set = {item.strip().casefold() for item in excluded}
        result: list[str] = []
        for topic in topics:
            cleaned = topic.strip()
            if cleaned and cleaned.casefold() not in excluded_set and cleaned not in result:
                result.append(cleaned)
        return result
