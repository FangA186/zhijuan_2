"""Fake Hermes Runs server for T2 queue-integration tests.

Mirrors the frozen vendor shape (vendor/hermes-agent/gateway/platforms/
api_server_runs.py) that services/hermes_adapter/http_adapter.py expects:

- POST /v1/runs            -> 202 {"run_id": "run_..."}
- GET  /v1/runs/{id}       -> 200 {"run_id", "status", "completed", "partial", "output", "usage"}
- POST /v1/runs/{id}/stop  -> 200 {"status": "stopping"|"failed_to_stop"}
- GET  /health             -> 200 {"status": "ok"}

Counters expose admission/status/stop totals so tests can assert that
duplicate delivery, reconnects or unknown results never re-bill.

Test-only: bind loopback, never a production fallback.
"""
from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


class FakeHermesServer:
    """Configurable double of the Hermes Runs API for deterministic fault injection."""

    def __init__(self, output_payload: dict[str, Any] | None = None,
                 usage: dict[str, Any] | None = None,
                 complete_after_polls: int = 1) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, dict[str, Any]] = {}
        self.counters = {"admissions": 0, "status_gets": 0, "stops": 0, "admit_failures": 0}
        self.admitted_task_refs: list[str] = []       # sha256 idempotency keys
        self.admission_roles: list[str] = []
        self.admission_models: list[str] = []
        self.behaviors: dict[str, Callable[[dict[str, Any]], dict[str, Any]] | None] = {}
        self.complete_after_polls = complete_after_polls
        # default completed output payload; callers override per run
        self.output_payload = output_payload if output_payload is not None else {"ok": True}
        self.usage = usage if usage is not None else {
            "prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120,
        }

    @staticmethod
    def key_for(task_ref: str) -> str:
        """The adapter sends sha256(task_ref) as the Idempotency-Key header."""
        import hashlib
        return hashlib.sha256(task_ref.encode()).hexdigest()

    # -- configuration -----------------------------------------------------
    def reset(self) -> None:
        with self._lock:
            self._state.clear()
            self.counters = {"admissions": 0, "status_gets": 0, "stops": 0, "admit_failures": 0}
            self.admitted_task_refs.clear()
            self.admission_roles.clear()
            self.admission_models.clear()

    def set_behavior(self, run_id_or_task_ref: str,
                     behavior: Callable[[dict[str, Any]], dict[str, Any]] | None) -> None:
        """Register a transform applied to the run state on each status GET.

        The callable receives the state dict and returns a (possibly) mutated
        dict, enabling: drop run_id, wrong run_id, bad JSON via "raw" key,
        status overrides, delay-until-N-polls, never completing, etc.
        """
        with self._lock:
            self.behaviors[run_id_or_task_ref] = behavior

    # -- introspection -----------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self.counters),
                "admitted_task_refs": list(self.admitted_task_refs),
                "admission_roles": list(self.admission_roles),
                "runs": {k: dict(v) for k, v in self._state.items()},
            }

    # -- server ------------------------------------------------------------
    def start(self) -> tuple[str, int]:
        server = ThreadingHTTPServer(("127.0.0.1", 0), self._make_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self._server = server
        self._thread = thread
        return server.server_address[0], server.server_address[1]

    def stop(self) -> None:
        if getattr(self, "_server", None) is not None:
            self._server.shutdown()
            self._server.server_close()
            self._thread.join(timeout=5)

    # -- protocol ----------------------------------------------------------
    def _make_handler(self) -> type[BaseHTTPRequestHandler]:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:  # silence test noise
                pass

            def _send(self, code: int, body: Any, raw: bytes | None = None) -> None:
                data = raw if raw is not None else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:
                if self.path == "/health":
                    self._send(200, {"status": "ok"})
                    return
                if self.path.startswith("/v1/runs/"):
                    with outer._lock:
                        outer.counters["status_gets"] += 1
                    run_id = self.path[len("/v1/runs/"):].split("/")[0]
                    with outer._lock:
                        state = outer._state.get(run_id)
                    if state is None:
                        self._send(404, {"error": {"code": "run_not_found",
                                                   "message": f"Run not found: {run_id}"}})
                        return
                    state = dict(state)
                    state["run_id"] = run_id
                    state["polls"] = int(state.get("polls", 0)) + 1
                    if (state["status"] not in {"completed", "failed", "cancelled"}
                            and state["polls"] >= outer.complete_after_polls):
                        state["status"] = "completed"
                        state["completed"] = True
                    behavior = outer.behaviors.get(run_id) or outer.behaviors.get(
                        state.get("idempotency_key", ""))
                    if behavior is not None:
                        state = behavior(state)
                    if state.get("raw") is not None:
                        self._send(200, b"not-json")
                        return
                    self._send(200, state)
                    return
                self._send(404, {"error": {"code": "not_found", "message": self.path}})

            def do_POST(self) -> None:
                if self.path == "/v1/runs":
                    length = int(self.headers.get("Content-Length") or 0)
                    body = json.loads(self.rfile.read(length) or b"{}") if length else {}
                    idem = self.headers.get("Idempotency-Key") or ""
                    with outer._lock:
                        behavior = outer.behaviors.get("__admission__")
                        if behavior is not None:
                            outcome = behavior(body)
                            if outcome.get("reject") is not None:
                                outer.counters["admit_failures"] += 1
                                self._send(outcome["reject"], {"error": {"code": "rejected"}})
                                return
                        run_id = "run_" + uuid.uuid4().hex
                        outer.counters["admissions"] += 1
                        outer.admitted_task_refs.append(idem)
                        outer.admission_models.append(str(body.get("model")))
                        # Role is embedded in the instructions text by the adapter.
                        instructions = str(body.get("instructions") or "")
                        role = "solver" if "Role: solver" in instructions else (
                            "author" if "Role: author" in instructions else "unknown")
                        outer.admission_roles.append(role)
                        outer._state[run_id] = {
                            "idempotency_key": idem,
                            "model": body.get("model"),
                            "status": "running",
                            "completed": False,
                            "partial": False,
                            "polls": 0,
                            "output": json.dumps(outer.output_payload),
                            "usage": dict(outer.usage),
                        }
                    self._send(202, {"run_id": run_id})
                    return
                if self.path.endswith("/stop"):
                    run_id = self.path[len("/v1/runs/"):-len("/stop")]
                    with outer._lock:
                        outer.counters["stops"] += 1
                        state = outer._state.get(run_id)
                        behavior = outer.behaviors.get(run_id) or outer.behaviors.get(
                            (state or {}).get("idempotency_key", ""))
                        if behavior is not None and behavior({}).get("stop_fails"):
                            self._send(500, {"error": {"code": "stop_failed"}})
                            return
                        if state is not None:
                            state["status"] = "cancelled"
                            state["completed"] = False
                    self._send(200, {"status": "stopping"})
                    return
                self._send(404, {"error": {"code": "not_found", "message": self.path}})

        return Handler
