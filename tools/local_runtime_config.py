"""Static local-runtime identifiers and inert dotenv parsing."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENV_PATH = ROOT / ".env"

RUNTIME_DIR = ROOT / ".runtime"

PG_CONTAINER = "zhijuan-workflow-20260922-pg"

MQ_CONTAINER = "zhijuan-workflow-20260922-mq"

ALLOWED_CONTAINERS = (PG_CONTAINER, MQ_CONTAINER)

VHOST = "zhijuan-local"

GENERATION_TABLES = (
    "generation_exam_state",
    "generation_exam_revisions",
    "generation_jobs",
    "generation_job_outbox",
    "generation_job_results",
    "generation_job_history",
)

WORKER_MARKERS = ("services.worker.jobs", "services.worker.scheduler")

ACTIVE_JOB_STATUSES = ("QUEUED", "RUNNING", "PAUSED", "RECONCILING")

API_HEALTH_URL = "http://127.0.0.1:8000/health"

READY_URLS = ("http://127.0.0.1:8000/readyz", "http://127.0.0.1:8000/v1/readyz")

BROKER_HOST = "127.0.0.1"

BROKER_PORT = 55672

def parse_env_key_value(text: str) -> dict[str, str]:
    """把 .env 风格的文本按行解析为键值（不做 shell 解释）。

    只支持 `KEY=VALUE`、空行与 `#` 注释；值两侧空白被去除，中间空格
    （如 libpq conninfo）原样保留。
    """
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            values[key] = value
    return values


def load_dotenv(path: Path = ENV_PATH) -> dict[str, str]:
    """把 .env 加载进 os.environ，已存在的变量不被覆盖。

    设置 ZHIJUAN_SKIP_DOTENV=1 时完全跳过（离线测试净化环境用）。
    """
    if os.getenv("ZHIJUAN_SKIP_DOTENV") == "1":
        return {}
    if not path.is_file():
        return {}
    values = parse_env_key_value(path.read_text(encoding="utf-8"))
    for key, value in values.items():
        if key not in os.environ:
            os.environ[key] = value
    return values
