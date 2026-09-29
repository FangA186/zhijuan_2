"""Stable import surface for the PostgreSQL generation-job repository."""
from __future__ import annotations

import os
from typing import Any
from .job_repository_execution import JobRepositoryExecutionMixin
from .job_repository_outbox import JobRepositoryOutboxMixin
from .job_repository_reads import JobRepositoryReadMixin


class PostgresJobRepository(JobRepositoryReadMixin, JobRepositoryExecutionMixin, JobRepositoryOutboxMixin):
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is required for generation jobs")
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("psycopg is required for generation jobs") from exc
        self.psycopg = psycopg

