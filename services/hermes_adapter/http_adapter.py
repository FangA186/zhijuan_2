"""Pinned Hermes gateway /v1/runs client."""
from __future__ import annotations

import os
from typing import Any, Callable, Mapping

import httpx

from reference_code.adapter_contract import RunRequest, RunResult
from .http_runner import execute_stage
from .run_stream import RunStream, TransportInfo


class HermesHttpAdapter(TransportInfo):
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 client: httpx.Client | None = None, poll_interval: float = 0.2):
        self.base_url = (base_url or os.getenv("HERMES_API_BASE_URL", "")).rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("HERMES_API_KEY", "")
        self.client = client or httpx.Client(timeout=10, trust_env=False)
        self.poll_interval = poll_interval
        self._run_ids: dict[str, str] = {}
        self._cancelled: set[str] = set()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        headers.update(kwargs.pop("headers", {}))
        return self.client.request(method, self.base_url + path, headers=headers, **kwargs)

    def run_stage(self, request: RunRequest,
                  emit_event: Callable[[Mapping[str, Any]], None] = lambda _: None,
                  cancellation_requested: Callable[[], bool] = lambda: False) -> RunResult:
        stream = RunStream(self, request, emit_event)
        try:
            return execute_stage(self, request, emit_event, cancellation_requested, stream)
        finally:
            stream.close()

    def cancel(self, task_ref: str) -> None:
        self._cancelled.add(task_ref)
        run_id = self._run_ids.get(task_ref)
        if run_id:
            try:
                self._request("POST", f"/v1/runs/{run_id}/stop")
            except Exception:
                pass
