"""T2 queue integration: dedicated RabbitMQ vhost + real Celery worker + fake Hermes.

Run only with both:
- ZHIJUAN_TEST_DATABASE_URL pointing at an isolated disposable PostgreSQL DB
- CELERY_BROKER_URL pointing at a dedicated acceptance vhost

No official model calls: the Hermes Runs API is doubled by
tests/framework/fake_hermes_server.py on loopback. The assertions target the
billing-critical invariants: one admission per stage, duplicate dispatches and
cancelled jobs never re-admit, unknown admissions park the job in RECONCILING.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.framework.fake_hermes_server import FakeHermesServer  # noqa: E402

BROKER = os.getenv("CELERY_BROKER_URL", "")
DSN = os.getenv("ZHIJUAN_TEST_DATABASE_URL", "")
RUNTIME_ID = "zhijuan-accept-w6"
REQUIRED = BROKER.startswith("amqp") and bool(DSN)


def _author_payload(local_id: str, kind: str, score: int) -> dict:
    """Contract-valid author candidate that passes deterministic checks."""
    return {
        "public": {
            "local_id": local_id,
            "kind": kind,
            "prompt": [{"type": "text", "text": "解方程：$2x + 1 = 5$，求 $x$。"}],
            "options": [],
            "score_x100": score,
            "material_ids": [],
            "children": [],
            "answer_space_lines": 2,
        },
        "private": {
            "answers": [{
                "local_question_id": local_id,
                "answer_kind": "free_text",
                "correct_option_ids": [],
                "accepted_answers": [{"value": "x = 2", "format": "text", "conditions": "唯一解"}],
                "solution": [{"type": "text", "text": "移项得 $2x = 4$，故 $x = 2$。"}],
                "rubric": [{"id": "r1", "description": "正确解出 x=2",
                            "score_x100": score, "acceptable_variants": []}],
            }],
        },
    }


SOLVER_PAYLOAD = {
    "derived_answer": "x = 2",
    "selected_option_ids": [],
    "steps": [{"text": "移项得 2x = 4。"}, {"text": "所以 x = 2。"}],
}


__all__ = [name for name in globals() if not name.startswith("__")]
