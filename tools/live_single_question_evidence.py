"""Read-only L01 job polling and evidence projection."""
from __future__ import annotations

import time
from typing import Any

from tools.live_single_question_config import TERMINAL_JOB_STATUSES

def poll_job(test_dsn: str, job_id: str, *, timeout: float = 900.0, interval: float = 2.0) -> dict[str, Any]:
    """只读轮询测试库 generation_jobs 直到终态；超时抛 RuntimeError。

    绝不自动重试：终态为 RECONCILING/UNKNOWN/FAILED 时如实返回并停止。
    """
    import psycopg
    deadline = time.monotonic() + timeout
    last: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        with psycopg.connect(test_dsn, connect_timeout=10) as conn:
            row = conn.execute(
                "SELECT snapshot FROM generation_jobs WHERE snapshot->>'job_id' = %s",
                (job_id,),
            ).fetchone()
        job = dict(row[0]) if row else None
        last = job
        if job is None:
            time.sleep(interval)
            continue
        if job.get("status") in TERMINAL_JOB_STATUSES:
            return job
        time.sleep(interval)
    raise RuntimeError(
        f"作业轮询超时（{timeout:.0f}s），最后状态: {last and last.get('status')}。"
        f"不自动重试；请人工核对 run_refs/事件后决定对账。")


def job_evidence(job: dict[str, Any], results_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """从终态 job 快照聚合证据：各槽状态、validation overall、run_refs/usage。

    有 run_id/usage 则记录；无则记 None（证据层面"未知"）。从未发生的阶段
    不产生幻影行（run_refs 里没有该 phase 键就过滤掉）。
    """
    run_refs = job.get("run_refs") or {}
    phases = [r for runs in run_refs.values() for r in runs.values()]

    def records_for(phase: str) -> list[dict[str, Any]]:
        out = []
        for runs in run_refs.values():
            if not isinstance(runs, dict):
                continue
            rec = runs.get(phase)
            if isinstance(rec, dict) and rec:
                out.append(rec)
        return out

    author_refs = records_for("author")
    solver_refs = records_for("solver")

    def run_summary(records: list[dict[str, Any]]) -> list[dict[str, str | None]]:
        out = []
        for rec in records:
            out.append({
                "task_ref": rec.get("task_ref"),
                "run_id": rec.get("run_id"),  # 有则记；无则为 None（证据里显示"未知"）
                "state": rec.get("state"),
                "usage_total_tokens": (rec.get("usage") or {}).get("total_tokens"),
            })
        return out

    validations = []
    for r in results_rows:
        validation = r.get("validation") or {}
        validations.append({
            "slot_id": r.get("slot_id"),
            "overall_status": validation.get("overall_status"),
        })

    return {
        "job_id": job.get("job_id"),
        "status": job.get("status"),
        "total_slots": job.get("total_slots"),
        "completed_slots": job.get("completed_slots"),
        "usage_status": job.get("usage_status"),
        "tokens_used": job.get("tokens_used"),
        "tokens_used_known": job.get("tokens_used_known"),
        "slots": [
            {"slot_id": s.get("slot_id"), "status": s.get("status"),
             "kind": s.get("kind"), "score_x100": s.get("score_x100"),
             "target_topic": s.get("target_topic")}
            for s in (job.get("slots") or [])
        ],
        "validation_overall": [v["overall_status"] for v in validations] or [],
        "author_runs": run_summary(author_refs),
        "solver_runs": run_summary(solver_refs),
        "phase_count": len(phases),
    }
