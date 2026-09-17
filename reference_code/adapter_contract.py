"""Project-owned Hermes adapter boundary, not a Hermes SDK implementation.

DeepSeek is the v1.3 provider. This is a thin Python boundary, not LangChain/LangGraph.
Prefer the verified internal HTTP Runs transport, or an approved isolated Python
process using the SAME Hermes framework. Business DTO fields are NOT native API
parameters. Implement against an audited, fixed Hermes commit. Keep the real blocking engine
in a task worker/isolated process, not a web async request. Never inherit author
files or historical sessions into a blind-solving run.
"""
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Protocol

Role = Literal["planner", "author", "solver", "reviewer", "exam_reviewer"]

@dataclass(frozen=True)
class RunRequest:
    task_ref: str
    provider: Literal["deepseek"]
    model_id: str
    role: Role
    input_payload: Mapping[str, Any]
    schema_name: str
    skill_bundle_hash: str
    policy_hash: str
    max_iterations: int
    deadline_utc: str
    capability_grant_ref: str

@dataclass(frozen=True)
class RunResult:
    status: Literal["SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT", "BUDGET_EXCEEDED", "UNKNOWN"]
    payload: Mapping[str, Any] | None
    provider_request_ids: tuple[str, ...]
    usage: Mapping[str, Any]
    error_code: str | None

class HermesAdapter(Protocol):
    def run_stage(
        self,
        request: RunRequest,
        emit_event: Callable[[Mapping[str, Any]], None],
        cancellation_requested: Callable[[], bool],
    ) -> RunResult:
        """Contract requirement: validate payloads/isolation. UNKNOWN needs backend reconciliation."""
        ...

    def cancel(self, task_ref: str) -> None:
        """Best-effort provider cancellation plus mandatory local stop policy."""
        ...

    def health(self) -> Mapping[str, Any]:
        """Return pinned Hermes commit, image digest and capability checks."""
        ...

    def capabilities(self) -> Mapping[str, Any]:
        """Report tested tool/format limits; must not imply untested capabilities."""
        ...
