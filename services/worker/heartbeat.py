"""Background heartbeat thread for worker/scheduler components.

Explicit start()/stop() lifecycle; a daemon thread plus an Event drives one
process-scoped heartbeat loop. The instance_id changes on every process start
so a restarted process cannot keep proving readiness with the old instance's
rows; after shutdown the old heartbeat simply expires via TTL.
"""
from __future__ import annotations

import os
import threading
from threading import Event, Thread
import uuid
from typing import Any, Callable

from services.api.runtime_heartbeats import upsert_heartbeat

# Gateway-role configuration-version plate: bump when the fingerprint contract
# (metadata shape or the endpoint set) changes. It is deliberately a constant
# here so all roles share one non-secret definition per code release.
GATEWAY_ROLE_CONFIG_VERSION = "v1"

DEFAULT_INTERVAL_SECONDS = 5.0


def runtime_id() -> str:
    return os.getenv("ZHIJUAN_RUNTIME_ID", "zhijuan-local")


def instance_id() -> str:
    """Process-unique id, regenerated at every process start."""
    return uuid.uuid4().hex


def _model_id() -> str:
    from services.api.settings import settings
    return os.getenv("ZHIJUAN_DEEPSEEK_MODEL_ID") or settings.deepseek_model_id


def _host_port(url: str) -> str:
    """Extract host:port from a gateway base URL; never include credentials."""
    url = (url or "").rstrip("/")
    if url.startswith("http://") or url.startswith("https://"):
        remainder = url.split("://", 1)[1]
        if "@" in remainder:
            remainder = remainder.rsplit("@", 1)[1]
        return remainder.split("/", 1)[0]
    return ""


def gateway_role_fingerprint() -> dict[str, str]:
    """Non-secret fingerprint of the author/solver gateway roles.

    Only host:port (and the config-version plate) are recorded; never tokens,
    keys or full URLs with embedded credentials.
    """
    return {
        "author_host_port": _host_port(os.getenv("HERMES_API_BASE_URL", "")),
        "solver_host_port": _host_port(os.getenv("HERMES_SOLVER_API_BASE_URL", "")),
        "gateway_config_version": GATEWAY_ROLE_CONFIG_VERSION,
    }


class HeartbeatThread:
    """Writes one component's heartbeat on a fixed interval.

    - ``poll`` may be injected for offline tests; by default it calls
      ``upsert_heartbeat`` with a real connection opened per tick.
    - stop() waits for the loop to notice the stop event so no interleaved
      tick writes after stop returns.
    """

    def __init__(self, component: str, *, interval: float = DEFAULT_INTERVAL_SECONDS,
                 poll: Callable[[dict[str, Any]], None] | None = None,
                 run_id: str | None = None, inst_id: str | None = None,
                 metadata: dict[str, Any] | None = None):
        self.component = component
        self.interval = float(interval)
        if self.interval <= 0:
            raise ValueError("heartbeat interval must be positive")
        self.run_id = run_id or runtime_id()
        self.inst_id = inst_id or instance_id()
        self.metadata = metadata if metadata is not None else self.default_metadata()
        self._poll = poll or self._default_poll
        self._stop = Event()
        self._thread: Thread | None = None

    def default_metadata(self) -> dict[str, Any]:
        return {"model_id": _model_id(), **gateway_role_fingerprint()}

    def _default_poll(self, metadata: dict[str, Any]) -> None:
        import psycopg
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            return
        with psycopg.connect(dsn) as conn:
            upsert_heartbeat(conn, self.run_id, self.component, self.inst_id, metadata)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(target=self._loop, name=f"heartbeat-{self.component}", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        self._thread = None

    def send(self) -> None:
        """Write one heartbeat now (used by the scheduler after a successful round)."""
        self._poll(self.metadata)

    def _loop(self) -> None:
        # Write immediately on start, then every interval.
        while not self._stop.is_set():
            try:
                self._poll(self.metadata)
            except Exception:
                # A lost database connection must not kill the worker; the
                # readiness probe's TTL will expire the heartbeat naturally.
                pass
            self._stop.wait(self.interval)
