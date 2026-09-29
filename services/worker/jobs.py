"""Celery consumer for generation jobs. Deployment must supply RabbitMQ and PostgreSQL."""
from __future__ import annotations

import os

from services.api.repositories import PostgresJobRepository
from services.exam.job_service import _now
from services.exam.question_service import QuestionService
from services.worker.failures import record_failure

_worker_heartbeat_thread = None


def _start_worker_heartbeat():
    """Start the process-scoped worker heartbeat thread (idempotent).

    The heartbeat is a real background thread, not a Celery task consumed by
    the blocking single-thread worker, so it cannot falsely prove liveness.
    Only one thread is created per process; the generated instance_id changes
    on every process start, so a restarted worker's stale rows expire via TTL.
    """
    global _worker_heartbeat_thread
    if _worker_heartbeat_thread is None:
        from services.worker.heartbeat import HeartbeatThread
        _worker_heartbeat_thread = HeartbeatThread("worker")
        _worker_heartbeat_thread.start()
    return _worker_heartbeat_thread


def _stop_worker_heartbeat():
    """Stop the worker heartbeat thread; the old instance's rows expire via TTL (DEV-007)."""
    global _worker_heartbeat_thread
    thread = _worker_heartbeat_thread
    _worker_heartbeat_thread = None
    if thread is not None:
        thread.stop()


def _register_worker_signals():
    """Bootstrap the worker heartbeat from Celery's own signals.

    worker_ready fires after the worker is fully usable; worker_shutdown fires
    on a clean exit. There is no heartbeat task consumed by the same worker
    thread, so the heartbeat cannot prove itself alive.
    """
    try:
        from celery.signals import worker_ready, worker_shutdown
    except Exception:
        return
    worker_ready.connect(lambda **kw: _start_worker_heartbeat(), weak=False)
    worker_shutdown.connect(lambda **kw: _stop_worker_heartbeat(), weak=False)


_register_worker_signals()


def run_job(job_id: str, *, repository=None, generate=None):
    repo = repository or PostgresJobRepository()
    generate = generate or QuestionService.generate_slot_result
    # The outbox carries only a job id; lookup prevents stale dispatches from running.
    job = repo.get_by_job_id(job_id)
    if not job or job["status"] != "QUEUED":
        return
    if job.get("job_kind") == "planning":
        from services.worker.planning import run_planning
        run_planning(job_id)
        return
    exam_id = job["exam_id"]
    expected = job["version"]
    job["status"] = "RUNNING"
    job["started_at"] = job["started_at"] or _now()
    job = repo.replace(job, expected)
    for slot in job["slots"]:
        current = repo.get(exam_id)
        if current["job_id"] != job_id or current["status"] != "RUNNING":
            return
        if slot["status"] in {"READY", "REVIEW_REQUIRED", "FAIL"}:
            continue
        local_id = f"q{slot['order']:02d}"
        try:
            # A timeout/crash after this point may have billed the model. Reconcile manually.
            slot_id = slot["slot_id"]
            for item in current["slots"]:
                if item["slot_id"] == slot_id:
                    item["status"] = "AUTHORING"
            current = repo.replace(current, current["version"])
            fence = current["version"]
            task_refs = {phase: f"{job_id}:{slot_id}:{phase}" for phase in ("author", "solver", "reviewer")}

            def record(event):
                nonlocal fence
                fence = repo.record_run_event(job_id, slot_id, fence, event)

            def cancelled():
                observed = repo.get(exam_id)
                return not observed or observed["job_id"] != job_id or observed["status"] != "RUNNING"

            previous = [r['candidate']['public'] for r in repo.results(job_id)]
            result = generate(local_id, exam_id, spec=current["spec_snapshot"], slot={**slot, "spec_revision":current["spec_revision"], "plan_revision":current["revision"], "question_revision_id":f"{job_id}:{slot_id}"},
                              task_refs=task_refs, run_event=record, cancellation_requested=cancelled, previous_questions=previous)
        except Exception as exc:
            if record_failure(repo, exam_id, job_id, slot_id, exc):
                continue
            return
        latest = repo.get(exam_id)
        if not latest or latest["job_id"] != job_id or latest["status"] != "RUNNING" or latest["version"] != fence:
            return
        try:
            repo.complete_slot(job_id, slot_id, fence, result["candidate"], result["validation"])
        except RuntimeError:
            return
    current = repo.get(exam_id)
    if current and current["job_id"] == job_id and current["status"] == "RUNNING":
        current["status"] = "PARTIAL_FAILED" if any(s["status"] == "FAIL" for s in current["slots"]) else "COMPLETED"
        repo.replace(current, current["version"])


def celery_app():
    broker = os.getenv("CELERY_BROKER_URL")
    if not broker or not broker.startswith("amqp"):
        raise RuntimeError("CELERY_BROKER_URL must point to RabbitMQ")
    from celery import Celery
    from kombu import Queue
    app = Celery("zhijuan_jobs", broker=broker)
    app.conf.update(
        task_queues=(Queue("generation", durable=True),),
        task_default_queue="generation",
        task_default_delivery_mode="persistent",
        task_create_missing_queues=True,
        broker_transport_options={"confirm_publish": True},
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        worker_enable_remote_control=False,
        worker_send_task_events=False,
        task_send_sent_event=False,
        beat_schedule={
            "dispatch-generation-outbox": {"task": "zhijuan.dispatch_generation_outbox", "schedule": 2.0},
            "reconcile-stale-generation": {"task": "zhijuan.reconcile_stale_generation", "schedule": 60.0},
        },
    )
    app.task(name="zhijuan.run_generation_job", ignore_result=True)(run_job)
    app.task(name="zhijuan.dispatch_generation_outbox", ignore_result=True)(dispatch_outbox)
    app.task(name="zhijuan.reconcile_stale_generation", ignore_result=True)(reconcile_stale)
    return app


def dispatch_outbox(*, repository=None, send=None) -> int:
    """Publish committed jobs to RabbitMQ, then acknowledge outbox rows."""
    repo = repository or PostgresJobRepository()
    if send is None:
        send = celery_app().send_task
    count = 0
    for outbox_id, job_id in repo.pending_dispatches():
        send("zhijuan.run_generation_job", args=[job_id])
        repo.mark_dispatched(outbox_id)
        count += 1
    return count


def reconcile_stale(*, repository=None) -> int:
    return (repository or PostgresJobRepository()).reconcile_stale()


def main():
    """Run the worker process with the heartbeat bootstrapped (for local `python -m`).

    Production uses the Celery CLI (`celery -A services.worker.jobs:app worker`),
    whose worker_ready/worker_shutdown signals drive the heartbeat via
    _register_worker_signals at import time. This entry point is a convenience
    for running the same app object directly.
    """
    _start_worker_heartbeat()
    try:
        app.worker_main()
    finally:
        _stop_worker_heartbeat()


app = celery_app() if os.getenv("CELERY_BROKER_URL") else None
