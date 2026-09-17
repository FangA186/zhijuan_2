"""Status mapping between raw provider / Hermes responses and standard RunResult.

Conforms to M1-03:
- completed requires both transport 200 and schema validation.
- partial, timeout, or errors map to FAILED / TIMED_OUT / CANCELLED.
- Unknown status mapped to UNKNOWN for backend reconciliation.
"""
from __future__ import annotations
from typing import Literal

RunStatus = Literal["SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT", "BUDGET_EXCEEDED", "UNKNOWN"]

def map_provider_status(
    raw_status: str | None,
    http_code: int,
    has_schema_error: bool = False,
    is_cancelled: bool = False,
) -> RunStatus:
    """Map raw execution states to canonical RunStatus."""
    if is_cancelled:
        return "CANCELLED"

    if http_code == 408 or raw_status == "timed_out":
        return "TIMED_OUT"

    if http_code == 429 or raw_status == "budget_exceeded":
        return "BUDGET_EXCEEDED"

    if http_code != 200:
        return "FAILED"

    if has_schema_error:
        return "FAILED"

    status_lower = (raw_status or "").strip().lower()
    if status_lower in ("completed", "succeeded", "success"):
        return "SUCCEEDED"
    elif status_lower in ("failed", "error", "rejected"):
        return "FAILED"
    elif status_lower in ("cancelled", "canceled", "stopped"):
        return "CANCELLED"
    elif status_lower in ("running", "in_progress", "pending"):
        return "UNKNOWN"

    return "UNKNOWN"
