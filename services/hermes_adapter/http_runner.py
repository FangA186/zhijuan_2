"""Stage execution and polling for Hermes HTTP adapter."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from typing import Any, Callable, Mapping

import httpx

from reference_code.adapter_contract import RunRequest, RunResult
from .run_stream import RunStream, safe_text, terminal_failure
from .schema_validator import validate_candidate


def get_capture(request_meta: dict | None = None):
    """Return a RawCapture instance if capture is enabled; else None."""
    if not os.getenv("ZHIJUAN_RAW_API_DIR", ""):
        return None
    try:
        from tools.raw_api_capture import RawCapture
        return RawCapture(request_meta or {}, source="hermes-adapter")
    except Exception:
        return None


def execute_stage(
    adapter,
    request: RunRequest,
    emit_event: Callable[[Mapping[str, Any]], None],
    cancellation_requested: Callable[[], bool],
    stream: RunStream,
) -> RunResult:
    def cancellation_state() -> bool | None:
        if request.task_ref in adapter._cancelled:
            return True
        try:
            return bool(cancellation_requested())
        except Exception:
            return None

    initial_cancel = cancellation_state()
    if initial_cancel is None:
        return RunResult("UNKNOWN", None, (), {}, "HERMES_CANCEL_CHECK_UNKNOWN")
    if initial_cancel:
        return RunResult("CANCELLED", None, (), {}, "TASK_CANCELLED_BEFORE_START")
    if request.provider != "deepseek":
        return RunResult("FAILED", None, (), {}, "UNSUPPORTED_PROVIDER")
    if not adapter.base_url or not adapter.api_key:
        return RunResult("FAILED", None, (), {}, "HERMES_GATEWAY_NOT_CONFIGURED")
    try:
        deadline = datetime.fromisoformat(request.deadline_utc.replace("Z", "+00:00")).timestamp() if request.deadline_utc else time.time() + 60
    except ValueError:
        return RunResult("FAILED", None, (), {}, "INVALID_DEADLINE")
    if deadline <= time.time():
        return RunResult("TIMED_OUT", None, (), {}, "DEADLINE_EXPIRED_BEFORE_ADMISSION")

    body = {
        "provider": "deepseek",
        "model": request.model_id,
        "instructions": (
            str(request.input_payload.get("skill_instructions", "")) + "\n"
            f"Role: {request.role}. Return one JSON object matching {request.schema_name}. "
            "Use only the input supplied for this run."
        ),
        "input": json.dumps(request.input_payload.get("input", request.input_payload), ensure_ascii=False),
    }
    capture = get_capture({
        "model": request.model_id, "role": request.role,
        "schema": request.schema_name, "provider": request.provider,
        "thinking": {"type": os.getenv("ZHIJUAN_DIAGNOSTIC_THINKING", "disabled")},
    })
    key = hashlib.sha256(request.task_ref.encode()).hexdigest()
    try:
        response = adapter._request("POST", "/v1/runs", json=body, headers={"Idempotency-Key": key})
    except httpx.HTTPError:
        if capture:
            capture.write("response", status="network_error")
        return RunResult("UNKNOWN", None, (), {}, "HERMES_ADMISSION_UNKNOWN")
    if capture:
        capture.write("response", status=response.status_code)
    if response.status_code != 202:
        if response.status_code >= 500 or response.status_code in {408, 429}:
            return RunResult("UNKNOWN", None, (), {}, f"HERMES_ADMISSION_HTTP_{response.status_code}")
        return RunResult("FAILED", None, (), {}, f"HERMES_ADMISSION_HTTP_{response.status_code}")
    try:
        run_id = response.json()["run_id"]
        if not isinstance(run_id, str) or not run_id.startswith("run_"):
            raise ValueError("invalid run_id")
    except (ValueError, KeyError, TypeError):
        return RunResult("UNKNOWN", None, (), {}, "HERMES_ADMISSION_MALFORMED")
    adapter._run_ids[request.task_ref] = run_id

    def stop_if_needed(usage: Mapping[str, Any] | None = None) -> RunResult | None:
        state = cancellation_state()
        if state is False:
            return None
        try:
            adapter.cancel(request.task_ref)
        except Exception:
            pass
        return RunResult("UNKNOWN", None, (), usage or {},
                         "HERMES_CANCEL_CHECK_UNKNOWN" if state is None else "HERMES_STOP_PENDING")

    try:
        emit_event({"event": "hermes_run_admitted", "task_ref": request.task_ref, "run_id": run_id})
    except Exception:
        try:
            adapter.cancel(request.task_ref)
        except Exception:
            pass
        return RunResult("UNKNOWN", None, (), {}, "HERMES_ADMISSION_EVENT_UNKNOWN")
    if request.capability_grant_ref == 'isolated-local-generation':
        stream.start(run_id)

    while True:
        try:
            stream.drain()
        except Exception:
            adapter.cancel(request.task_ref)
            return RunResult("UNKNOWN", None, (), {}, "HERMES_EVENT_PERSIST_UNKNOWN")
        if stop_result := stop_if_needed():
            return stop_result
        if time.time() >= deadline:
            adapter.cancel(request.task_ref)
            return RunResult("UNKNOWN", None, (), {}, "HERMES_DEADLINE_RECONCILE")
        try:
            response = adapter._request("GET", f"/v1/runs/{run_id}")
        except httpx.TimeoutException:
            time.sleep(adapter.poll_interval)
            continue
        except httpx.HTTPError:
            return RunResult("UNKNOWN", None, (), {}, "HERMES_STATUS_UNKNOWN")
        if response.status_code != 200:
            return RunResult("UNKNOWN", None, (), {}, f"HERMES_STATUS_HTTP_{response.status_code}")
        try:
            state = response.json()
            status = state["status"]
        except (ValueError, KeyError, TypeError):
            return RunResult("UNKNOWN", None, (), {}, "HERMES_STATUS_MALFORMED")
        if state.get("run_id") != run_id:
            adapter.cancel(request.task_ref)
            return RunResult("UNKNOWN", None, (), {}, "HERMES_STATUS_RUN_ID_MISMATCH")
        if stop_result := stop_if_needed():
            return stop_result
        if status in {"queued", "started", "running", "stopping", "waiting_for_approval"}:
            time.sleep(adapter.poll_interval)
            continue
        usage = state.get("usage") if isinstance(state.get("usage"), dict) else {}
        if capture:
            raw_output = state.get("output", "")
            capture.body(json.dumps({
                "hermes_status": status, "run_id": run_id,
                "usage": usage, "output": raw_output,
            }, ensure_ascii=False), kind="hermes_output")
        if status == "interrupted":
            return RunResult("UNKNOWN", None, (), usage, "HERMES_INTERRUPTED_RECONCILE")
        if status == "cancelled":
            return RunResult("CANCELLED", None, (), usage, "HERMES_CANCELLED")
        if status not in {"queued", "started", "running", "stopping", "waiting_for_approval"}:
            try:
                stream.drain()
                emit_event({"event": "activity", "task_ref": request.task_ref, "run_id": run_id,
                            "data": {"event": "run.result", "status": status,
                                     "error": safe_text(state.get("error")),
                                     "output": safe_text(state.get("output"))}})
            except Exception:
                return RunResult("UNKNOWN", None, (), usage, "HERMES_EVENT_PERSIST_UNKNOWN")
        if status == "failed" or state.get("partial") or state.get("completed") is False:
            return terminal_failure(state, usage)
        if status != "completed" or state.get("completed") is not True:
            return RunResult("UNKNOWN", None, (), usage, "HERMES_TERMINAL_UNKNOWN")
        payload = None
        try:
            payload = json.loads(state["output"])
            if not isinstance(payload, dict):
                raise ValueError("output is not a JSON object")
            if request.role == "author":
                validate_candidate(payload)
        except (ValueError, KeyError, TypeError) as exc:
            detail = getattr(exc, 'diagnostic_code', type(exc).__name__)
            if isinstance(exc, json.JSONDecodeError):
                detail += f":L{exc.lineno}:C{exc.colno}"
            return RunResult("FAILED", payload if isinstance(payload, dict) else {"rejected_output": safe_text(state.get("output"))}, (), usage, f"HERMES_OUTPUT_INVALID:{detail}")
        if stop_result := stop_if_needed(usage):
            return stop_result
        try:
            emit_event({"event": "hermes_run_completed", "task_ref": request.task_ref, "run_id": run_id, "usage": usage})
        except Exception:
            try:
                adapter.cancel(request.task_ref)
            except Exception:
                pass
            return RunResult("UNKNOWN", None, (), usage, "HERMES_COMPLETION_EVENT_UNKNOWN")
        if stop_result := stop_if_needed(usage):
            return stop_result
        return RunResult("SUCCEEDED", payload, (), usage, None)
