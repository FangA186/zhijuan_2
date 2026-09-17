"""Hermes HTTP Adapter conforming to reference_code/adapter_contract.py.

Handles role dispatch, cancellation checks, error mapping, and event emission.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Mapping

from reference_code.adapter_contract import HermesAdapter, RunRequest, RunResult
from .adapter import HermesDeepSeekAdapter
from .runtime_factory import RuntimeFactory
from .status_map import map_provider_status

class HermesHttpAdapter:
    """Implementation of HermesAdapter Protocol for 知卷."""

    def __init__(self, base_adapter: HermesDeepSeekAdapter | None = None):
        self._adapter = base_adapter or HermesDeepSeekAdapter()
        self._factory = RuntimeFactory(adapter=self._adapter)
        self._cancelled_tasks: set[str] = set()

    def run_stage(
        self,
        request: RunRequest,
        emit_event: Callable[[Mapping[str, Any]], None],
        cancellation_requested: Callable[[], bool],
    ) -> RunResult:
        """Execute a pipeline stage conforming to the adapter contract."""
        if cancellation_requested() or request.task_ref in self._cancelled_tasks:
            return RunResult(
                status="CANCELLED",
                payload=None,
                provider_request_ids=(),
                usage={"tokens": 0},
                error_code="TASK_CANCELLED_BEFORE_START",
            )

        emit_event({
            "event": "stage_started",
            "task_ref": request.task_ref,
            "role": request.role,
            "model_id": request.model_id,
            "timestamp": time.time(),
        })

        try:
            if request.role == "author":
                candidate = self._adapter.execute_author_role(
                    slot_spec=request.input_payload.get("slot_spec", {}),
                    stage=request.input_payload.get("stage", "junior"),
                    subject=request.input_payload.get("subject", "初中数学"),
                    model_id=request.model_id,
                )
                emit_event({"event": "stage_completed", "task_ref": request.task_ref})
                return RunResult(
                    status="SUCCEEDED",
                    payload=candidate,
                    provider_request_ids=(f"req_{request.task_ref}",),
                    usage={"estimated_tokens": 1500},
                    error_code=None,
                )

            elif request.role == "solver":
                runtime = self._factory.get_runtime_for_role("solver")
                report = runtime.run_blind_solve(
                    question_candidate=request.input_payload.get("candidate", {}),
                    model_id=request.model_id,
                )
                emit_event({"event": "stage_completed", "task_ref": request.task_ref})
                status = "SUCCEEDED" if report.match_reference else "FAILED"
                return RunResult(
                    status=status,
                    payload=report.to_dict(),
                    provider_request_ids=(f"req_{request.task_ref}",),
                    usage={"duration_ms": report.duration_ms},
                    error_code=None if report.match_reference else "DISCREPANCY_DETECTED",
                )

            else:
                emit_event({"event": "stage_failed", "task_ref": request.task_ref, "error": f"Role {request.role} not yet implemented"})
                return RunResult(
                    status="FAILED",
                    payload=None,
                    provider_request_ids=(),
                    usage={},
                    error_code=f"UNSUPPORTED_ROLE_{request.role.upper()}",
                )

        except Exception as exc:
            emit_event({"event": "stage_failed", "task_ref": request.task_ref, "error": str(exc)})
            return RunResult(
                status="FAILED",
                payload=None,
                provider_request_ids=(),
                usage={},
                error_code=exc.__class__.__name__,
            )

    def cancel(self, task_ref: str) -> None:
        """Flag task as cancelled."""
        self._cancelled_tasks.add(task_ref)
        self._adapter.cancel(task_ref)

    def health(self) -> Mapping[str, Any]:
        """Return adapter health status."""
        return self._adapter.health()

    def capabilities(self) -> Mapping[str, Any]:
        """Return adapter capabilities."""
        return self._adapter.capabilities()
