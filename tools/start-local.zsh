#!/bin/zsh
# Start this project's existing local workbench and generation services.
emulate -L zsh
set -euo pipefail

ROOT=${0:A:h:h}
WEB_DIR="$ROOT/apps/web"
PYTHON="$ROOT/.venv/bin/python"
UVICORN="$ROOT/.venv/bin/uvicorn"
LOG_DIR="$ROOT/.runtime/logs"
API_LABEL=com.zhijuan.local.api
WEB_LABEL=com.zhijuan.local.web

# launchd starts these modes outside the invoking terminal/session.
if [[ "${1-}" == --serve-api ]]; then
  mkdir -p "$LOG_DIR"
  cd "$ROOT"
  exec "$UVICORN" services.api.main:app --host 127.0.0.1 --port 8000 --reload \
    >> "$LOG_DIR/api.log" 2>&1
elif [[ "${1-}" == --serve-web ]]; then
  mkdir -p "$LOG_DIR"
  cd "$WEB_DIR"
  exec npm run dev -- --port 3000 --strictPort >> "$LOG_DIR/vite.log" 2>&1
fi
die() { print -u2 -- "启动失败：$*"; exit 1; }
[[ "${1-}" == "" || "${1-}" == --workbench-only ]] || die "用法：$0 [--workbench-only]"
for tool in docker open curl lsof npm launchctl; do
  command -v "$tool" >/dev/null 2>&1 || die "缺少命令：$tool"
done
[[ -x "$PYTHON" && -x "$UVICORN" ]] || die "缺少项目 .venv；请先安装后端依赖"
[[ -d "$WEB_DIR/node_modules" ]] || die "缺少前端依赖；先在 apps/web 运行 npm install"

cd "$ROOT"
PG_CONTAINER=$("$PYTHON" -c 'from tools.local_runtime import PG_CONTAINER; print(PG_CONTAINER)')
mkdir -p "$LOG_DIR"

if ! docker info >/dev/null 2>&1; then
  print -- "启动 Docker Desktop，等待 Docker 就绪…"
  open -a Docker || die "无法打开 Docker Desktop"
  for attempt in {1..60}; do
    docker info >/dev/null 2>&1 && break
    sleep 2
  done
fi
docker info >/dev/null 2>&1 || die "Docker 在 120 秒内未就绪"

if ! pg_state=$(docker inspect --format '{{.State.Running}}' "$PG_CONTAINER" 2>/dev/null); then
  die "找不到本项目原有 PG 容器 $PG_CONTAINER；为保护草稿，不自动创建新库"
fi
if [[ "$pg_state" != true ]]; then
  print -- "启动原有 PG 容器：$PG_CONTAINER"
  docker start "$PG_CONTAINER" >/dev/null || die "PG 容器启动失败"
fi
for attempt in {1..30}; do
  docker exec "$PG_CONTAINER" pg_isready -q >/dev/null 2>&1 && break
  sleep 1
done
docker exec "$PG_CONTAINER" pg_isready -q >/dev/null 2>&1 || die "PG 在 30 秒内未就绪"

# Parse .env as data, never source it in a shell; verify the exact draft database.
"$PYTHON" - <<'PY' || die "数据库身份或表结构检查失败"
import os
from tools.local_runtime import database_check, load_dotenv

load_dotenv()
ok, detail, _ = database_check(os.getenv("DATABASE_URL"), 3)
print(detail)
raise SystemExit(0 if ok else 1)
PY

listener_pid() {
  lsof -nP -tiTCP:"$1" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}
owned_listener() {
  local pid="$1" expected_cwd="$2" expected_command="$3"
  local process_cwd=$(lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -n 1)
  local process_command=$(ps -p "$pid" -o command= 2>/dev/null)
  [[ "$process_cwd" == "$expected_cwd" && "$process_command" == *"$expected_command"* ]]
}
http_ok() { curl -fsS --max-time 3 "$1" >/dev/null 2>&1; }

ensure_port_free_or_healthy() {
  local port="$1" url="$2" cwd="$3" marker="$4"
  local pid=$(listener_pid "$port")
  [[ -z "$pid" ]] && return 1
  owned_listener "$pid" "$cwd" "$marker" || die "$port 端口被非本项目进程占用（PID $pid），未接管"
  if http_ok "$url"; then
    print -- "$port 端口的本项目服务已可用（PID $pid）"
    return 0
  fi
  print -- "本项目 $port 端口进程无响应，停止旧进程（PID $pid）…"
  kill -TERM "$pid" || die "无法停止旧进程 $pid"
  for attempt in {1..20}; do
    [[ -z "$(listener_pid "$port")" ]] && return 1
    sleep 1
  done
  die "旧进程未释放 $port 端口；未强制终止，请手动检查 PID $pid"
}

wait_http() {
  local url="$1" label="$2" log="$3"
  for attempt in {1..30}; do
    http_ok "$url" && { print -- "$label 已就绪：$url"; return; }
    sleep 1
  done
  die "$label 在 30 秒内未就绪；请查看 $log"
}

if ! ensure_port_free_or_healthy 8000 http://127.0.0.1:8000/healthz "$ROOT" 'uvicorn services.api.main:app'; then
  print -- "启动后端…"
  launchctl remove "$API_LABEL" >/dev/null 2>&1 || true
  launchctl submit -l "$API_LABEL" -- "$ROOT/tools/start-local.zsh" --serve-api || die "无法注册后端 launchd 服务"
  wait_http http://127.0.0.1:8000/healthz 后端 "$LOG_DIR/api.log"
fi

if ! ensure_port_free_or_healthy 3000 http://localhost:3000/ "$WEB_DIR" vite; then
  print -- "启动前端…"
  launchctl remove "$WEB_LABEL" >/dev/null 2>&1 || true
  launchctl submit -l "$WEB_LABEL" -- "$ROOT/tools/start-local.zsh" --serve-web || die "无法注册前端 launchd 服务"
  wait_http http://localhost:3000/ 前端 "$LOG_DIR/vite.log"
fi

generation_ready() {
  "$PYTHON" - <<'PY' >/dev/null 2>&1
import json, urllib.request
with urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=5) as response:
    data = json.load(response)
raise SystemExit(0 if data.get('generation', {}).get('ready') is True else 1)
PY
}

if [[ "${1-}" == --workbench-only ]]; then
  print -- "工作台：http://localhost:3000/；PG：复用 $PG_CONTAINER / zhijuan_local。"
  print -- "仅工作台模式：未启动命题服务。"
  exit 0
fi

if ! generation_ready; then
  # A running worker could resume an old job and bill the model. Refuse that
  # transition unless the current database has no active work or outbox item.
  "$PYTHON" - <<'PY' || die "存在活动/待投递任务，未自动启动命题服务；请先核对或对账"
import os
import psycopg
from tools.local_runtime import load_dotenv

load_dotenv()
with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=3) as db:
    if db.execute('select current_database()').fetchone()[0] != 'zhijuan_local':
        raise SystemExit('数据库不是 zhijuan_local')
    active = db.execute("select count(*) from generation_jobs where snapshot->>'status' "
                        "in ('QUEUED','RUNNING','PAUSED','RECONCILING')").fetchone()[0]
    pending = db.execute('select count(*) from generation_job_outbox where dispatched_at is null').fetchone()[0]
print(f'启动前核对：活动作业 {active}，待投递消息 {pending}')
raise SystemExit(0 if active == pending == 0 else 1)
PY

  # Reuse the project's safe stop/start flow, including its ownership checks.
  "$PYTHON" tools/local_runtime.py stop-generation || die "旧 Worker/调度器无法安全回收"
  for service in budget-proxy author-hermes solver-hermes solver-entry; do
    name="zhijuan-workflow-20260922-live-$service-1"
    if ! state=$(docker inspect --format '{{.State.Running}}' "$name" 2>/dev/null); then
      die "缺少原有容器 $name；未创建替代网关"
    fi
    if [[ "$state" != true ]]; then
      print -- "启动 $service…"
      docker start "$name" >/dev/null || die "$service 启动失败"
    fi
  done
  "$PYTHON" tools/local_runtime.py start-generation || die "命题服务启动失败；请运行 doctor 核对状态"
  generation_ready || die "启动命令返回成功，但 /readyz 未确认命题服务就绪"
fi

print -- "工作台：http://localhost:3000/；生成服务 READY。"
