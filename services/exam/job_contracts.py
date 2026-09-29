from __future__ import annotations
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()



class AcceptError(RuntimeError):
    """Service-side acceptance rejection carrying the C5 error contract body."""

    def __init__(self, status_code: int, code: str, reason: str, **fields: Any):
        super().__init__(code)
        self.status_code = status_code
        self.body = {"code": code, "reason": reason}
        self.body.update(fields)
        if "detail" in fields:
            # Kept as extra diagnostics; the route only forwards non-secret fields.
            self.body["detail"] = fields["detail"]

