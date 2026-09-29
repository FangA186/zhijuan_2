"""Start and stop the project's worker and scheduler with injected facade hooks."""
from __future__ import annotations

import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.local_runtime_config import MQ_CONTAINER, PG_CONTAINER, ROOT

def start_generation(hooks) -> dict[str, Any]:
    """确认 PG → 恢复 MQ（仅 Exited 时 docker start）→ vhost → 启 Worker+调度器 → 验证真就绪。"""
    timeout = float(os.getenv("ZHIJUAN_READINESS_PROBE_TIMEOUT", "2.0"))
    started_at = datetime.now(timezone.utc).isoformat()
    worker_proc = scheduler_proc = None

    # 1. API 必须已在跑：工具不代启/重启 API 与 Vite。
    api_ok, api_detail = hooks.api_health(timeout)
    if not api_ok:
        return {"ok": False, "step": "api", "detail": api_detail,
                "next_action": "先启动 8000 API（工具检测不到 API 时如实报告，不代启）"}

    # 2. PG 必须在跑：工具绝不代启 PG。
    pg_state, pg_line = hooks.container_state(PG_CONTAINER)
    if pg_state != "running":
        return {"ok": False, "step": "pg", "detail": pg_line,
                "next_action": "请先手动启动 PG 容器 zhijuan-workflow-20260922-pg"}
    db_ok, db_detail, db_code = hooks.database_check(os.getenv("DATABASE_URL"), timeout)
    if not db_ok:
        return {"ok": False, "step": "database", "detail": db_detail,
                "next_action": "确认迁移已执行且 DSN 指向 zhijuan_local"}

    # 3. MQ：仅当 Exited 时对其执行 docker start；绝不 down/重建。
    mq_state, mq_line = hooks.container_state(MQ_CONTAINER)
    if mq_state == "exited":
        proc = subprocess.run(["docker", "start", MQ_CONTAINER],
                              capture_output=True, text=True, timeout=60.0)
        if proc.returncode != 0:
            return {"ok": False, "step": "mq", "detail": f"docker start 失败: {proc.stderr.strip()}",
                    "next_action": "手动运行 docker start zhijuan-workflow-20260922-mq"}
    elif mq_state not in ("running", "up"):
        return {"ok": False, "step": "mq", "detail": mq_line,
                "next_action": "仅允许在容器 Exited 时自动 start"}
    if not hooks._wait_amqp_ready():
        return {"ok": False, "step": "mq", "detail": "AMQP 握手超时，MQ 未就绪",
                "next_action": "手动检查 docker start zhijuan-workflow-20260922-mq 日志"}

    # 4. vhost zhijuan-local（仅 add_vhost / set_permissions；失败转手动步骤）。
    vhost_ok, vhost_detail = hooks._ensure_vhost()
    if not vhost_ok:
        return {"ok": False, "step": "vhost", "detail": vhost_detail,
                "next_action": "按提示手动执行 rabbitmqctl（工具已给出可复制命令）"}

    # 5. 配置前提。
    if not os.getenv("CELERY_BROKER_URL"):
        return {"ok": False, "step": "broker",
                "detail": "CELERY_BROKER_URL 未配置",
                "next_action": "在 configs/local-runtime.env.example 配置 amqp://…/zhijuan-local"}

    # 6. PID 冲突防护：已有存活的本项目 Worker/调度器时拒绝再次启动。
    for kind in ("worker", "scheduler"):
        existing = hooks._read_pid_file(kind)
        if existing:
            owned, detail = hooks.verify_pid_ownership(existing)
            if owned:
                return {"ok": False, "step": kind,
                        "detail": f"已有运行中的 {kind}（PID {existing}）",
                        "next_action": "先运行 tools/local_runtime.py stop-generation"}
            hooks._remove_pid_file(kind)  # 旧 PID 文件残留，进程已不存在

    # 7. 启动 Worker 与调度器（env 由 Python 注入，不打印）。
    try:
        worker_proc = hooks.spawn_process(
            [str(ROOT / ".venv/bin/celery"), "-A", "services.worker.jobs:app", "worker",
             "--pool=solo", "--concurrency=1", "--without-gossip",
             "--without-mingle", "--without-heartbeat", "--loglevel=INFO"],
            "worker")
        scheduler_proc = hooks.spawn_process(
            [str(ROOT / ".venv/bin/python"), "-m", "services.worker.scheduler"], "scheduler")
    except OSError as exc:
        hooks._recycle_newly_started(worker_proc, scheduler_proc)
        return {"ok": False, "step": "spawn", "detail": f"启动失败: {type(exc).__name__}",
                "next_action": "检查 .venv/bin/celery 与 python 是否可执行"}

    hooks._write_pid_file("worker", worker_proc.pid)
    hooks._write_pid_file("scheduler", scheduler_proc.pid)

    # 8. 轮询 /readyz，验证真就绪后才报成功。
    deadline = time.monotonic() + 90.0
    last = None
    while time.monotonic() < deadline:
        if worker_proc.poll() is not None or scheduler_proc.poll() is not None:
            break
        last = hooks._readiness_snapshot(timeout)
        if last["ok"]:
            break
        time.sleep(2.0)

    if last and last["ok"]:
        return {"ok": True, "step": "ready", "detail": "生成服务真就绪",
                "worker_pid": worker_proc.pid, "scheduler_pid": scheduler_proc.pid,
                "started_at": started_at,
                "next_action": "日常入口 3000 可开始命题；停用请运行 stop-generation"}

    hooks._recycle_newly_started(worker_proc, scheduler_proc)
    return {"ok": False, "step": "ready",
            "detail": "启动后未确认真就绪（fail-closed）" + (f"；{last['error']}" if last else ""),
            "next_action": "日志在 .runtime/logs/worker.log 与 scheduler.log（工具不导出其中内容），请按 doctor 逐项排查"}


def recycle_newly_started(hooks, *procs: subprocess.Popen | None) -> None:
    """启动失败/未就绪时，只回收本次新起且确认属于本项目的进程。"""
    for proc in procs:
        if proc is None or proc.poll() is not None:
            continue
        owned, detail = hooks.verify_pid_ownership(proc.pid)
        if owned:
            hooks._terminate_owned(proc.pid)
            print(f"[start-generation] 已回收本次新起进程: {detail}")
        else:
            print(f"[start-generation] 不回收 PID {proc.pid}: {detail}")


def _active_jobs() -> tuple[list[tuple[str, str]], str | None]:
    """读取 zhijuan_local.generation_jobs 的活动任务；DB 不可用时返回 None 判定。"""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return [], "DATABASE_URL 未配置，无法核对活动任务"
    import psycopg
    try:
        with psycopg.connect(dsn, connect_timeout=5.0) as conn:
            rows = conn.execute(
                "SELECT snapshot->>'job_id', snapshot->>'status' FROM generation_jobs "
                "WHERE snapshot->>'status' IN ('QUEUED','RUNNING','PAUSED','RECONCILING')"
            ).fetchall()
            return [(str(r[0]), str(r[1])) for r in rows], None
    except Exception as exc:
        return [], f"无法读取 generation_jobs: {type(exc).__name__}"


def stop_generation(hooks) -> dict[str, Any]:
    """先核对无活动任务，再按 调度器→Worker→mq 收尾；绝不碰 PG/Vite/API/其他容器。"""
    active, db_error = hooks._active_jobs()
    if db_error:
        return {"ok": False, "step": "database", "detail": db_error + "（为安全起见拒绝收尾）",
                "next_action": "确认 DATABASE_URL 与迁移后再重试"}
    if active:
        return {"ok": False, "step": "active_jobs",
                "detail": f"存在活动任务 {active}，默认拒绝直接停止",
                "next_action": "先通过 API 取消任务或对账（RECONCILING 需先处理未知结果）"}

    # kill 前先全部校验归属：任一不匹配即拒绝，一个都不杀。
    targets: list[tuple[str, int]] = []
    for kind in ("scheduler", "worker"):
        pid = hooks._read_pid_file(kind)
        if pid is None:
            continue
        owned, detail = hooks.verify_pid_ownership(pid)
        if not owned:
            return {"ok": False, "step": "ownership", "detail": detail,
                    "next_action": "核对 .runtime/*.pid 后手动处理；工具不会误杀"}
        targets.append((kind, pid))

    # 调度器→Worker 顺序收尾。
    for kind, pid in targets:
        hooks._terminate_owned(pid)
        hooks._remove_pid_file(kind)

    if not targets:
        return {"ok": True, "step": "done-no-processes",
                "detail": "没有由本工具启动的 Worker/调度器（无 PID 文件）",
                "next_action": "无需收尾（工具从不停止 PG/Vite/API）"}

    # 仅对精确名称 mq 容器 stop（不 down），且仅当其在跑。
    mq_state, mq_line = hooks.container_state(MQ_CONTAINER)
    if mq_state in ("running", "up"):
        proc = subprocess.run(["docker", "stop", MQ_CONTAINER],
                              capture_output=True, text=True, timeout=60.0)
        if proc.returncode != 0:
            return {"ok": False, "step": "mq", "detail": f"docker stop 失败: {proc.stderr.strip()}",
                    "next_action": "手动运行 docker stop zhijuan-workflow-20260922-mq"}

    return {"ok": True, "step": "done",
            "detail": "调度器与 Worker 已停止，mq 容器已停止（PG/Vite/API 未触碰）",
            "next_action": "再次启用请运行 start-generation"}
