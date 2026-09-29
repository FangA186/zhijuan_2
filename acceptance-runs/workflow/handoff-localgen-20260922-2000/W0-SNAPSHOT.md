# W0 现场保护快照（handoff-localgen-20260922-2000）

时间：2026-09-22 深夜（接手会话，UTC+8）。执行范围澄清已读取：只实施和排查知卷；其他项目仅排除，不调查不操作。

## Git 现场
- 分支 `main`，HEAD `1a89b53 fix(adapter): make httpx optional with urllib fallback for offline CI`。
- 大量已修改与未跟踪文件（含教材 docx、acceptance-runs、多个新源码文件）全部保留，未暂存、未提交、未清理。

## 知卷容器与端口归属
| 组件 | 状态 | 端口 |
| --- | --- | --- |
| `zhijuan-workflow-20260922-pg` | Up | 127.0.0.1:55432 |
| `zhijuan-workflow-20260922-mq` | Exited(0) | 55672 未监听 |
| live-author/live-solver/live-solver-entry/live-budget-proxy | Exited（4–6 小时前） | 8643/8644/8650 未监听 |
| 日常 API（宿主 uvicorn `--reload`） | 运行中（reload 父子进程） | 127.0.0.1:8000，`GET /health` 返回知卷服务信息 |
| 日常 Vite（apps/web） | 运行中 | [::1]:3000；`curl http://localhost:3000/` 实测返回知卷 Vite 页面（react-refresh + 项目 HTML） |
| 非日常入口（不在本轮验收使用） | 运行中 | 127.0.0.1:3002（另一 vite）、127.0.0.1:8001（另一 uvicorn `services.api.main:app`） |

范围外最少记录：其他项目 `zygf-gitea` 容器亦监听 `*:3000`（IPv4 通配），`zygf-postgres` Up；仅记录此归属事实，未做任何 inspect/日志/数据库访问，未操作。知卷目标 URL `http://localhost:3000/` 实测由知卷 Vite 响应，日常入口可用。

## 数据库身份与行数（只读核对）
- `SELECT current_database(), current_schema()` → `zhijuan_local` / `public`；PostgreSQL 18.6。
- 行数：generation_exam_state=1、generation_exam_revisions=1、generation_jobs=0、generation_job_outbox=0、generation_job_results=0、generation_job_history=0。

## 用户 current 草稿（只读）
- version=12，spec_revision=4，stage=senior。
- 标题：2023-2024学年人教A版（2019）高中数学必修第一册期末综合测试卷。
- 13 个 section 共 23 题；总分 15000 score_x100（17×400 + 1200 + 1400×5）；slots=23；candidates=4。
- plan 未生成（尚未确认），plan_revision 为空；与实施计划描述一致。
- spec 规范化 sha256 前 16 位：`e15e2c8f5f0f2904`（恢复点参考）。

## 备份
- `backup/zhijuan_local_backup.sql`（84,036 字节，pg_dump --no-owner --no-privileges，经容器内 pg_dump，凭据未出现在任何输出）。
- SHA-256 见 `backup/zhijuan_local_backup.sql.sha256`（8cb463517782964b… 开头）。文件权限 600。备份不是清库许可。

## 费用账本（只读快照，未改动）
- 路径 `/tmp/zhijuan-workflow-20260922/budget/acceptance.sqlite`，权限 0600。
- budget 行：`(run_id=zhijuan-workflow-20260922, calls=16, reserved_cny=16)`。
- reservations 共 16 条，无 RESERVED/UNKNOWN/PENDING 未决条目。
- 按计划 §7：保留现有限额（MAX_REQUESTS=20、MAX_RESERVED_CNY=30、RESERVE_CNY=1）；完整 23 题至少 46 次上游请求，超出余量，必须先解决预算条件，不得清零或绕过。

## 归属结论（谁依赖什么）
- 日常前端（3000）→ 日常 API（8000，`/v1`）→ zhijuan_local（PG 容器 55432）。
- 生成链路当前未运行：MQ、Worker、outbox 调度器、author(8644)、solver-entry(8643)、budget-proxy(8650) 均未启动，等待 W1/W2 接线。
- 用户页面读写/保存/预览依赖 8000+55432；本轮任何操作不得停掉这两者。

## 未做项
- 未执行 `context --task` 全量任务遍历（仅 M1-04 及其交接，按需补充）。
- 未迁移费用账本到持久目录（计划 §7.2.6，需先停代理并原样复制，本轮未启动代理故未做）。
