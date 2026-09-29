# DEV-005：本地运行接线工具（tools/local_runtime.py）

状态：ACCEPTED（仅本地运行接线，不是生产编排框架）
提出人/日期：编码子代理 / 2026-09-23
批准依据：实施计划 W1（§6.1–§6.3）与跨任务契约 C1/C4；用户批准实施计划即批准本决策范围内的本地接线工具。
关联任务/功能：W1 本地启动和资源边界（M1-02/M1-04）

## 背景和约束

日常入口 `localhost:3000/8000` 需要持久数据库、RabbitMQ、活着且配置一致的 Worker/outbox 调度器才能真正受理命题。长期靠人工 `docker compose up` 与手敲 Celery 命令既易误停其他服务，也无法给 C1 readyz 提供可靠参照。需要一个最小运行工具：`doctor`（只读巡诊）、`start-generation`、`stop-generation`，刻意不做通用编排框架。

约束（继承 AGENTS.md 与实施计划 §6.3）：
- 根 `.env` 用 Python 按键值数据加载，禁止 `source`、禁止 shell 解析——当前 `DATABASE_URL` 是含空格的 libpq conninfo，shell 拆分会破坏它；DSN/令牌只进内存绝不打印。
- 配置加载必须完成在 import 任何 worker/repositories 模块之前——本项目不允许依赖 Python 模块偶然的导入顺序。
- `doctor` 只读：不代启服务、不改状态；容器只允许对精确名称 `zhijuan-workflow-20260922-pg` 与 `zhijuan-workflow-20260922-mq` 执行 `docker ps --format` 只读查询。
- `start-generation` 不重启 API 与 Vite、不代启 PG；mq 容器只在 Exited 时 `docker start`；vhost 仅 `add_vhost`/`set_permissions`；启动失败只回收本次新起且确认属于本项目的进程。
- `stop-generation` 有活动任务时默认拒绝；kill 前必须校验 PID 归属；绝不停止 PG、Vite、API 或其他项目容器。
- 金额与分值一律整数（本工具不涉及费用计算；预算状态读取保持原样）。

## 可选方案与证据

1. **通用编排框架**（如 docker-compose 全家桶或进程管理器）：超出最小需求，容易触碰范围外容器/服务，且 plan §14 明令"不做通用编排框架"。
2. **shell 脚本封装**：`source .env` 会破坏含空格 conninfo；bash 环境下注入 env 除非用 `env ` 显式传参，否则难以在子进程间精确复购；且容易误 kill 或误 stop。
3. **Python 键值加载 + 子进程 spawn**（选择此方案）：`.env` 按行 `KEY=VALUE` 解析保留中间空格；`subprocess.Popen(env=dict(os.environ))` 由 Python 注入环境；PID 记录写入 `.runtime/`（mkdir 且 chmod 700），kill 前用 `ps -p <pid> -o command=` 校验命令行包含 `services.worker.jobs` 或 `services.worker.scheduler`。

选择方案 3。证据：本仓库 `services/api/settings.py:12-26` 已在用等价的 Python 键值加载（`_load_env_file` 不 source、不 shell 解析），本工具复用同一约定；`services/worker/jobs.py:116` 与 `services/worker/scheduler.py:31-88` 已提供 Worker/调度器入口。

## 数据、接口、权限、成本与兼容影响

- 新增 `tools/local_runtime.py`：只有 `doctor` / `start-generation` / `stop-generation` 三个子命令。
  - `doctor` 输出组件名/状态/下一动作，C1 原因码（未就绪组件 → `NOT_CONFIGURED`、`DATABASE_UNAVAILABLE`、`BROKER_UNAVAILABLE`、`WORKER_UNAVAILABLE`、`DISPATCHER_UNAVAILABLE`、`AUTHOR_UNAVAILABLE`、`SOLVER_UNAVAILABLE`、`BUDGET_UNAVAILABLE` 等），失败给原因码；不回显任何秘密。
  - `start-generation` 步骤：确认 8000 API 在跑（检测不到就如实报告，不代启）→ 确认 PG running（不代启）→ 若 mq 容器 Exited 则仅对其 `docker start` → 确保 vhost `zhijuan-local`（仅 `add_vhost`/`set_permissions`，失败转手动步骤）→ spawn 一份 Worker（`.venv/bin/celery -A services.worker.jobs:app worker --pool=solo --concurrency=1 --without-gossip --without-mingle --without-heartbeat --loglevel=INFO`）与一份调度器（`python -m services.worker.scheduler`）→ 轮询 `/readyz`（或 `/v1/readyz`）确认 `generation.ready=true` 才算成功。
  - `stop-generation` 先查 `zhijuan_local.generation_jobs` 是否有 `QUEUED/RUNNING/PAUSED/RECONCILING`，有则默认拒绝；无活动任务则按 调度器→Worker→mq 容器（仅 `stop` 不 `down`）收尾；kill 前校验 PID 归属。
- PID 目录 `.runtime/`（mkdir + chmod 700）。`.gitignore` 需要增加 `.runtime/`，由本任务如实写进 openIssues，不直接改 `.gitignore`（文件清单边界）。
- 环境变量读取按契约 C4：`ZHIJUAN_RUNTIME_ID`（默认 `zhijuan-local`）、`ZHIJUAN_BUDGET_INTERNAL_URL`（默认 `http://127.0.0.1:8650/internal/budget`）、`ZHIJUAN_BUDGET_PROXY_TOKEN`（默认空=预算不可用）、`ZHIJUAN_HEARTBEAT_TTL_SECONDS`（默认 20）、`ZHIJUAN_READINESS_PROBE_TIMEOUT`（默认 2.0）、`ZHIJUAN_READINESS_CACHE_TTL`（默认 3.0）。这些由 T5 在 `services/api/settings.py` 落地；本工具用 `os.getenv` 同名读取。
- 心跳：`doctor` 查 `runtime_heartbeats` 的 `worker`/`dispatcher` 新鲜度（C2 表由 T3 落地，`services/api/runtime_heartbeats.py` 已存在）；表不存在视为未就绪（`WORKER_UNAVAILABLE`/`DISPATCHER_UNAVAILABLE`），行过期给 `HEARTBEAT_STALE`。
- 兼容影响：本工具只读健康接口、只在明确授权下启停 Worker/调度器与 mq 容器，不修改任何生成任务、outbox、结果或预算账本；不依赖 `database/` 新迁移（心跳表缺失只影响巡诊结果，不阻塞工具本身）。

## 实施/迁移/回滚

- 实施：上述三个子命令全部实现；`configs/local-runtime.env.example` 覆盖 §6.2 全部变量与 C4 全部变量（只写占位符）；`tools/offline_gate.sh` 提供净化环境的离线测试门禁。
- 迁移：无数据迁移。`.runtime/` 为新建本机运行目录，删除其中 PID 文件不影响数据库、任务或结果；心跳表回滚见 DEV-007（保留表、只停新写入）。
- 回滚：删除/停用 `tools/local_runtime.py`、`configs/local-runtime.env.example`、`tools/offline_gate.sh` 即可回到人工启动方式；不触碰现有任务、结果、心跳表或任何容器卷数据。任何由本工具启动的进程停用后由 `stop-generation` 或手动按同校验规则终止。

## 必须重跑的测试

- `tests/test_local_runtime.py`（离线：键值 .env 解析含空格 conninfo、PID 归属校验 mock subprocess、doctor 输出结构 mock 探测；测试中不调用 docker、不发真实网络）。
- 主流程统一门禁（offline / unittest discover 会纳入新增测试）；本工具真实 doctor 属只读巡诊，可在授权主流程执行。

## 关联文件及被替代决定

- `tools/local_runtime.py`（新建）、`configs/local-runtime.env.example`（新建）、`tools/offline_gate.sh`（新建）、`tests/test_local_runtime.py`（新建）。
- 依赖：`services/api/runtime_heartbeats.py`（T3）、`services/worker/heartbeat.py`（T3）、`services/worker/scheduler.py`（T3）、`database/005_local_runtime_heartbeats.sql`（DEV-007）。
- 不替代 DEV-004（费用代理）、DEV-007（心跳表）与任何架构决策；工作台真实验收仍以 W2/W3 后端就绪与受信预算为准。
