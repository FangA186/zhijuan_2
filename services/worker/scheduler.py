"""Lightweight outbox scheduler run loop.

Polls the committed-job outbox every tick, dispatching new jobs and reconciling
stale ones, then records a dispatcher heartbeat for readiness probes.

Single-process assumption: exactly one scheduler instance per runtime is
expected, so at most one dispatch tick overlaps another tick of the same
runtime. This is a local runtime loop only, not a distributed job queue.
"""
from __future__ import annotations

import os
from threading import Event
import time
from typing import Callable

from services.worker.heartbeat import HeartbeatThread

DEFAULT_TICK_SECONDS = 2.0


def _tick(*, dispatch=None, reconcile=None) -> tuple[int, int]:
    """Run one dispatch+reconcile pass. Returns (dispatched, reconciled) counts."""
    from services.worker.jobs import dispatch_outbox, reconcile_stale
    dispatched = (dispatch or dispatch_outbox)()
    reconciled = (reconcile or reconcile_stale)()
    return dispatched, reconciled


class OutboxScheduler:
    """One instance owns one dispatcher heartbeat thread and the polling loop.

    stop() sets the event, joins the loop, then stops the heartbeat thread so
    no dispatcher heartbeat row remains fresh after shutdown (it expires via
    TTL once this process exits).
    """

    def __init__(self, *, tick_seconds: float | None = None,
                 on_tick: Callable[[], None] | None = None,
                 heartbeat: HeartbeatThread | None = None,
                 dispatch=None, reconcile=None):
        self.tick_seconds = float(tick_seconds if tick_seconds is not None else _env_tick_seconds())
        if self.tick_seconds <= 0:
            raise ValueError("scheduler tick interval must be positive")
        self.on_tick = on_tick or (lambda: None)
        self.dispatch = dispatch
        self.reconcile = reconcile
        self._stop = Event()
        self.heartbeat = heartbeat or HeartbeatThread("dispatcher", interval=self.tick_seconds)

    def run(self) -> None:
        """Blocking loop; call stop() from another thread or a signal handler."""
        self.heartbeat.start()
        try:
            while not self._stop.is_set():
                started = time.monotonic()
                try:
                    _tick(dispatch=self.dispatch, reconcile=self.reconcile)
                    self.on_tick()
                    # A successfully processed round is the proof of life.
                    self.heartbeat.send()
                except Exception:
                    # A lost broker/database must not crash the scheduler; the
                    # next tick retries and the heartbeat stays stale until TTL.
                    pass
                if not self._stop.is_set():
                    elapsed = time.monotonic() - started
                    self._stop.wait(max(self.tick_seconds - elapsed, 0.0))
        finally:
            self.heartbeat.stop()

    def stop(self) -> None:
        self._stop.set()


def _env_tick_seconds() -> float:
    raw = os.getenv("ZHIJUAN_SCHEDULER_TICK_SECONDS")
    if not raw:
        return DEFAULT_TICK_SECONDS
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TICK_SECONDS
    if value <= 0:
        return DEFAULT_TICK_SECONDS
    return value


if __name__ == "__main__":
    import signal
    scheduler = OutboxScheduler()

    def _request_stop(signum, frame):
        scheduler.stop()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    scheduler.run()
