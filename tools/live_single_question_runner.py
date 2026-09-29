"""One-run orchestration, bounded evidence output, and ordered process teardown."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.live_single_question_config import ACCEPT_RUNTIME_ID, API_BASE, API_MARKERS, NOT_RESPONSIBLE_STATUSES, WORKER_MARKERS

def run(hooks, out_path: Path) -> dict[str, Any]:
    """执行一次单题真实验收：preflight -> 起进程 -> 心跳 -> 受理 -> 轮询 -> 证据 -> 收尾。"""
    started_at = datetime.now(timezone.utc).isoformat()
    test_dsn = os.getenv("ZHIJUAN_TEST_DATABASE_URL", "")
    result: dict[str, Any] = {
        "tool": "live-single-question-run",
        "runtime_id": ACCEPT_RUNTIME_ID,
        "started_at": started_at,
        "ok": False,
        "reason": None,
    }
    procs: dict[str, subprocess.Popen] = {}

    try:
        # 1. preflight 全过。
        pre = hooks.preflight()
        result["preflight"] = pre
        if not pre["ready"]:
            result["ok"] = False
            result["reason"] = "preflight 未通过，拒绝进入 run"
            print("[run] preflight 未通过，拒绝进入 run")
            return result

        # 2. 预算 before。
        budget_before = hooks.budget_query(min_requests=2)
        result["budget_before"] = budget_before

        # 3. 启动 API / worker / scheduler。
        #    API 同样需要 CELERY_BROKER_URL：/readyz 的 broker 探测与
        #    start_generation_job 的 configured 门禁都读它（health.py / exams.py）。
        master_env = hooks.child_env(broker=os.getenv("CELERY_BROKER_URL", ""))
        api_env = hooks.child_env(broker=os.getenv("CELERY_BROKER_URL", ""))
        procs["api"] = hooks.spawn_process(hooks.api_command(), "api", api_env, log_name="l01-api")
        procs["worker"] = hooks.spawn_process(hooks.worker_command(), "worker", master_env, log_name="l01-worker")
        procs["scheduler"] = hooks.spawn_process(hooks.scheduler_command(), "scheduler", master_env, log_name="l01-scheduler")

        # 4. 心跳等待（超时由调用方最后统一收尾）。
        result["heartbeats"] = hooks.wait_heartbeats(test_dsn, timeout=60.0)

        # 5. 真实受理链路。
        accepted = hooks.run_acceptance_chain(API_BASE, hooks.build_seed_spec())
        result["job_id"] = accepted["job_id"]
        result["accept_status"] = accepted["status"]

        # 6. 只读轮询到终态，绝不自动重试。
        final = hooks.poll_job(test_dsn, accepted["job_id"], timeout=900.0)
        result["final_status"] = final.get("status")
        result["job"] = final
        if final.get("status") in NOT_RESPONSIBLE_STATUSES:
            result["ok"] = False
            result["reason"] = (f"作业终态 {final.get('status')}：上游结果未知/失败，"
                                f"如实记录并停止，绝不重新受理")
            hooks.write_report(out_path, result)  # 如实记录终态证据
            return result

        # 7. 采集证据（results 行 + 事件里的真实 run_id/usage）。
        import psycopg
        with psycopg.connect(test_dsn, connect_timeout=10) as conn:
            rows = conn.execute(
                "SELECT slot_id, candidate, validation FROM generation_job_results "
                "WHERE job_id = %s ORDER BY slot_id", (accepted["job_id"],),
            ).fetchall()
            results_rows = [{"slot_id": r[0], "candidate": r[1], "validation": r[2]} for r in rows]
        result["evidence"] = hooks.job_evidence(final, results_rows)
        result["results_count"] = len(results_rows)

        # 8. 预算 after + 差值（require_sufficient=False：仅作账本快照，
        #    本次运行已消耗额度时"当前不足"不是失败）。
        budget_after = hooks.budget_query(min_requests=2, require_sufficient=False)
        result["budget_after"] = budget_after
        result["budget_delta"] = {
            "calls": hooks._int_or_none(budget_after.get("calls")) - hooks._int_or_none(budget_before.get("calls")),
            "reserved_cny": hooks._int_or_none(budget_after.get("reserved_cny")) - hooks._int_or_none(budget_before.get("reserved_cny")),
        }

        # 9. 证据 JSON。先置 ok 再写报告，成功运行不得被记成 false。
        result["ok"] = True
        hooks.write_report(out_path, result)
        result["report_path"] = str(out_path)
        print(f"[run] 完成，report: {out_path}")
        return result
    except Exception as exc:
        result["ok"] = False
        # 只记异常类型名，绝不嵌入 str(exc)：psycopg 认证失败消息里可能带
        # 数据库用户名（复测过），原始错误正文只在服务日志回归，不进
        # report.json 的 reason 字段与控制台输出（计划 §7：不输出口令）。
        # 与 verify_test_database 的 f"PG 连接失败: {type(exc).__name__}"
        # 同款 fail-closed 写法。
        result["reason"] = f"运行中止: {type(exc).__name__}"
        print(f"[run] 失败: {result['reason']}")
        try:
            hooks.write_report(out_path, result)
        except Exception:
            pass  # 证据写失败也如实保留内存结果
        return result
    finally:
        # 收尾（幂等）：先 worker 后 scheduler 后 API；只终止已校验归属的本次进程。
        hooks._terminate_all(procs)


def _int_or_none(value: Any) -> int:
    """把预算响应里的整数字段安全取出（说明性：值应为 int）。"""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def terminate_all(hooks, procs: dict[str, subprocess.Popen]) -> None:
    """按 worker -> scheduler -> api 顺序收尾；PID 归属校验不过则不杀（仅记录）。

    进程保留、测试库数据保留作为证据；不删除任何行。
    """
    order = ("worker", "scheduler", "api")
    for kind in order:
        proc = procs.get(kind)
        if proc is None or proc.poll() is not None:
            continue
        markers = WORKER_MARKERS if kind in ("worker", "scheduler") else API_MARKERS
        owned, detail = hooks.verify_pid_ownership(proc.pid, markers)
        if owned:
            print(f"[run] 收尾 {kind}（PID {proc.pid}）")
            hooks.terminate_owned(proc.pid)
        else:
            print(f"[run] 不回收 {kind} PID {proc.pid}: {detail}")


def write_report(hooks, out_path: Path, result: dict[str, Any]) -> None:
    """证据 JSON（mkdir -p；失败不吞，让 run 报错）。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({
            "report_kind": "l01-live-single-question-v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "runtime_id": hooks.ACCEPT_RUNTIME_ID,
            "preflight": result.get("preflight"),
            "budget_before": result.get("budget_before"),
            "budget_after": result.get("budget_after"),
            "budget_delta_calls": result.get("budget_delta", {}).get("calls"),
            "budget_delta_reserved_cny": result.get("budget_delta", {}).get("reserved_cny"),
            "job": {
                "job_id": result.get("job_id"),
                "status": result.get("final_status"),
                "accept_status": result.get("accept_status"),
                "evidence": result.get("evidence"),
                "results_count": result.get("results_count", 0),
                "slots": (result.get("evidence") or {}).get("slots"),
                "validation_overall": (result.get("evidence") or {}).get("validation_overall"),
                "author_runs": (result.get("evidence") or {}).get("author_runs"),
                "solver_runs": (result.get("evidence") or {}).get("solver_runs"),
            },
            "limitations": [
                "单题真实链路不构成教学质量验收；REVIEW 表示待教师复核，不代表题目正确。",
                "本证据只覆盖 L01 单题：author 1 次 + solver 1 次真实上游请求的最低链路。",
                "完整 23 题、学段覆盖、学生 API 与发布/导出不在本报告范围（按预算另行门控）。",
            ],
            "ok": result.get("ok") is True,
            "reason": result.get("reason"),
            "report_path": str(out_path),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
