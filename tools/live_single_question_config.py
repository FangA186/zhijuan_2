"""Static identifiers for the isolated L01 acceptance environment."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENV_PATH = ROOT / ".env"

RUNTIME_DIR = ROOT / ".runtime"

LOG_DIR = RUNTIME_DIR / "logs"

TEST_DATABASE_NAME = "zhijuan_accept_w6"

TEST_VHOST = "zhijuan-accept-w6"

ACCEPT_RUNTIME_ID = "zhijuan-accept-l01"

API_PORT = 8020

API_BASE = f"http://127.0.0.1:{API_PORT}"

GENERATION_TABLES = (
    "generation_exam_state",
    "generation_exam_revisions",
    "generation_jobs",
    "generation_job_outbox",
    "generation_job_results",
    "generation_job_history",
)

REQUIRED_TABLES = (*GENERATION_TABLES, "runtime_heartbeats")

TERMINAL_JOB_STATUSES = ("COMPLETED", "PARTIAL_FAILED", "FAILED", "CANCELLED", "RECONCILING", "UNKNOWN")

NOT_RESPONSIBLE_STATUSES = ("RECONCILING", "UNKNOWN", "FAILED")

WORKER_MARKERS = ("services.worker.jobs", "services.worker.scheduler")

API_MARKERS = ("services.api.main",)

REPORT_DIR = ROOT / "acceptance-runs" / "workflow" / "handoff-localgen-20260922-2000" / "l01-live"

REPORT_PATH = REPORT_DIR / "report.json"
