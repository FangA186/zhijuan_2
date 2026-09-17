"""Runtime Factory for Hermes roles.

Provides isolated runtime environments according to role.
Enforces security isolation: blind solver runtimes never receive author context or reference answers.
"""
from __future__ import annotations
from typing import Literal

from .adapter import HermesDeepSeekAdapter
from .blind_runtime import BlindSolverRuntime

Role = Literal["planner", "author", "solver", "reviewer", "exam_reviewer"]

class RuntimeFactory:
    """Factory for creating role-specific Hermes execution runtimes."""

    def __init__(self, adapter: HermesDeepSeekAdapter | None = None):
        self.adapter = adapter or HermesDeepSeekAdapter()

    def get_runtime_for_role(self, role: Role):
        """Return the dedicated runtime for the requested role."""
        if role == "solver":
            # Blind solver runtime strictly isolates prompt and strips private answers
            return BlindSolverRuntime(adapter=self.adapter)
        elif role in ("author", "planner", "reviewer", "exam_reviewer"):
            return self.adapter
        else:
            raise ValueError(f"Unsupported Hermes role: {role}")
