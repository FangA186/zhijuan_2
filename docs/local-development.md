# 本机工作台启动与生成服务状态

常用入口为 `http://localhost:3000/`，默认连接 `http://localhost:8000/v1`。项目资料页独立读取文件，能打开资料页并不证明出卷后端配置完整。

## 一键启动本地工作台与生成服务

在仓库根运行 `./tools/start-local.zsh`。脚本可从其他目录调用：它会启动 Docker Desktop（若尚未运行），只启动本项目已有的 `zhijuan-workflow-20260922-pg` 容器，核对连接确实指向 `zhijuan_local` 且任务表齐全，再启动后端 8000 与前端 3000。已有健康的本项目进程会复用；无响应的本项目进程会先正常停止。其他项目占用端口时脚本报错，不接管，也不创建新数据库。

默认还会恢复现有调用记录代理、命题与隔离盲解 Hermes 网关，并调用 `tools/local_runtime.py` 安全启动 RabbitMQ、Worker 和调度器。启动前要求当前库没有活动作业或待投递消息，以免自动续跑旧任务；完成后必须由 `/readyz` 确认为 `READY`。本地链路依 DEV-013 不设请求/金额总上限，教师主动发起生成可产生真实模型费用。若只需编辑草稿，用 `./tools/start-local.zsh --workbench-only`。

API 和前端由 macOS `launchctl` 托管，运行日志分别在 `.runtime/logs/api.log` 和 `.runtime/logs/vite.log`。重复执行不会重启健康进程。启动脚本不会自动发起出卷或模型请求，也不会重建容器、清库或重置费用账本。

## 当前本机存储

2026-09-22 已将常用 8000 服务连接到本地 PostgreSQL 的独立 `zhijuan_local` 数据库（127.0.0.1:55432）。沿用本项目之前创建的 PostgreSQL 容器；与验收数据库分开。原草稿、题目和版本已先备份，再复制到该库；未清空验收库或其他项目库。

数据库连接保存在仓库根目录被 Git 忽略的 `.env` 的 `DATABASE_URL` 中。已有 DeepSeek 设置保留；不要把 `.env` 或带口令的连接串加入交接或提交。首次新环境须先在专属本地库执行 `database/003_generation_jobs.sql`、`004_generation_exam_state.sql`；不要将这些本地表当作正式多租户生产迁移。

在仓库根运行：

```bash
# 本机已存在该容器；不要在新机器直接照搬容器名称。
docker start zhijuan-workflow-20260922-pg
.venv/bin/uvicorn services.api.main:app --host 127.0.0.1 --port 8000 --reload
```

另一个终端在 `apps/web` 运行 `npm run dev`。默认 API 地址已指向 8000；仅使用其他明确的环境时设置 `VITE_API_BASE_URL`。API 加载根 `.env`；修改该文件后重启 API。`ZHIJUAN_SKIP_DOTENV=1` 仅供显式注入隔离配置的测试等用途，使用该开关时不会加载 `.env`。

## 哪些操作现在可以进行

数据库连接正常且没有任务时，当前任务 GET 返回 404，前端将其解释为“没有任务”，而不是服务故障。出卷设置可读取、修改和预览蓝图。

真实生成还需要 RabbitMQ、消费任务的 Worker，以及分别配置的命题/盲解 Hermes 网关。`/v1/health` 的 `generation` 给出这些配置项的布尔状态，不返回连接串或令牌。`configured=true` 只说明设置齐全，不证明进程存活或教学质量通过；`runtime_verified=false` 明确这一边界。

配置未齐备时，页面说明当前可编辑/预览并禁用“确认并开始”；后端也以 503 拒绝创建任务，不进入空队列或模拟成功。仅有 DeepSeek Key 不表示完整生成环境就绪。

调用记录账本沿用原数据，脚本不会清零或自动发起模型请求。`/readyz` 只证明组件运行，不证明题目质量、费用总额或当前旧作业可以重新生成。

2026-09-29 起，蓝图改由 Hermes 规划 Agent 设计；编辑范围不计费，点击规划会调用模型。新增输出契约需要重载结构化代理与Worker，详见 [规划Agent使用与重载](planner-agent.md)。原规则预览不再作为模型失败后的替代结果。
