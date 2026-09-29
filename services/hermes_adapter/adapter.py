"""Business-facing adapter backed exclusively by the pinned Hermes Runs gateway."""
from __future__ import annotations

import os
import uuid
from typing import Any, Callable, Mapping

from reference_code.adapter_contract import RunRequest, RunResult
from .http_adapter import HermesHttpAdapter
from .skills_loader import load_skill


class HermesDeepSeekAdapter:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 default_model: str | None = None, timeout: float = 60.0,
                 transport: HermesHttpAdapter | None = None):
        # Legacy api_key/base_url are DeepSeek settings. Never use them as Hermes credentials.
        self.default_model = default_model or os.getenv("ZHIJUAN_DEEPSEEK_MODEL_ID", "deepseek-chat")
        self.timeout = timeout
        self._transport = transport or HermesHttpAdapter()
        self._solver_transport = transport or HermesHttpAdapter(
            base_url=os.getenv("HERMES_SOLVER_API_BASE_URL", ""),
            api_key=os.getenv("HERMES_SOLVER_API_KEY", ""),
        )
        self.api_key = self._transport.api_key
        self.base_url = self._transport.base_url

    def health(self) -> Mapping[str, Any]:
        return {"agent_framework": "hermes", "provider": "deepseek",
                "model_id": self.default_model, "api_configured": bool(self._transport.api_key),
                "solver_gateway_configured": bool(self._solver_transport.base_url and self._solver_transport.api_key
                                                  and self._solver_transport.base_url != self._transport.base_url),
                **self._transport.health()}

    def capabilities(self) -> Mapping[str, Any]:
        return self._transport.capabilities()

    def cancel(self, task_ref: str) -> None:
        self._transport.cancel(task_ref)
        if self._solver_transport is not self._transport:
            self._solver_transport.cancel(task_ref)

    def run_stage(self, request: RunRequest,
                  emit_event: Callable[[Mapping[str, Any]], None] = lambda _: None,
                  cancellation_requested: Callable[[], bool] = lambda: False) -> RunResult:
        skill = load_skill({
            "planner": "exam-planner", "author": "question-author",
            "solver": "blind-solver", "reviewer": "question-reviewer",
            "exam_reviewer": "exam-reviewer",
        }[request.role])
        from dataclasses import replace
        scoped = replace(request, input_payload={
            "skill_name": skill.name,
            "skill_instructions": skill.system_prompt,
            "input": dict(request.input_payload),
        })
        selected = self._solver_transport if request.role == "solver" else self._transport
        if request.role == "solver" and (not selected.base_url or selected.base_url == self._transport.base_url):
            return RunResult("FAILED", None, (), {}, "HERMES_SOLVER_ISOLATION_NOT_CONFIGURED")
        return selected.run_stage(scoped, emit_event, cancellation_requested)

    def execute_author_role(self, slot_spec: dict[str, Any], stage: str,
                            subject: str, model_id: str = "deepseek-chat") -> dict[str, Any]:
        result = self.run_stage(RunRequest(
            task_ref=f"author-{uuid.uuid4().hex}", provider="deepseek", model_id=model_id,
            role="author", input_payload={"stage": stage, "subject": subject, "slot": slot_spec},
            schema_name="candidate", skill_bundle_hash="", policy_hash="",
            max_iterations=1, deadline_utc="", capability_grant_ref=""))
        if result.status != "SUCCEEDED" or result.payload is None:
            raise RuntimeError(result.error_code or result.status)
        return dict(result.payload)

    def execute_solver_role(self, public_question: dict[str, Any],
                            model_id: str = "deepseek-chat") -> dict[str, Any]:
        result = self.run_stage(RunRequest(
            task_ref=f"solver-{uuid.uuid4().hex}", provider="deepseek", model_id=model_id,
            role="solver", input_payload={"public_question": public_question},
            schema_name="blind_solver", skill_bundle_hash="", policy_hash="",
            max_iterations=1, deadline_utc="", capability_grant_ref=""))
        if result.status != "SUCCEEDED" or result.payload is None:
            raise RuntimeError(result.error_code or result.status)
        return dict(result.payload)

    def _call_deepseek_chat(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Direct provider calls are disabled; use Hermes run_stage")

    async def stream_deepseek_chat_async(self, *args: Any, **kwargs: Any):
        raise RuntimeError("Direct provider streaming is disabled; use Hermes run events")
        yield
