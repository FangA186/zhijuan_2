# 知卷：日常工作台真实命题接通实施计划

版本：交接计划 v1，2026-09-22。本文是待实施设计，不是完成报告。

仓库：`/Users/fangzengxing/zhijuan_spec_v1_4`。

**执行范围澄清（用户于2026-09-22补充）：只实施和排查知卷。`zygf-gitea`、`zygf-postgres` 等均属于其他项目，只是排除对象，不是知卷依赖或调查任务。不得进入其仓库、读取配置/环境变量/日志、连接其数据库、诊断其健康状态，或调整/重启/停止其服务。** 如核对知卷指定端口时恰好发现其他项目占用，仅记录最少的进程/容器名称、监听地址和端口，然后停止向该项目深入调查。

执行者先读本文，再读同目录 [详细测试与验收矩阵](2026-09-22-local-generation-test-plan.md)。用户本次要求写计划，由其他 AI 接手实施；写计划不等于允许现在启动计费测试、改变架构或提交代码。

## 0. 目标、成功定义和不包含的工作

首要目标：用户在日常 `http://localhost:3000/` 中完成“选择教材/范围 → 导入模板或配置规格 → 预览 → 确认 → 实际命题/独立盲解 → 查看真实候选和检查结果”。这条路径必须实际连接 `8000` 服务，不能另起 `3002/8001` 验收成功后宣称日常入口已可用。

本轮完成的判定同时要求：

1. 日常入口确实连接持久数据库、RabbitMQ、活着且配置一致的 Worker、outbox 调度，以及独立命题/盲解 Hermes。
2. “确认计划并开始命题”只在真实就绪、预算可受理、计划版本仍有效时可用；后端有同等门禁，不能靠禁用按钮保护。
3. 断网、刷新、双击、Worker 重启和未知响应不会导致重复计费、重复创建任务、覆盖新版本或显示虚假成功。
4. 用户当前 23 题/150 分的规格与逐题分值保持正确；原有章节选择不会被初始化、热更新或切换教材的遗留状态误覆盖。
5. 能在真实授权额度内完成小规模真实验收。完整 23 题真实验收若额度不足，必须明确未验收，不能由一题成功代签。
6. 停闲置服务降低资源占用时，不能影响用户正在用的草稿、配置、预览及已启用功能。
7. 有可复查的命令、测试计数、数据库/队列/运行状态、浏览器观察和记录交接。

不将以下范围偷偷并入本轮：完整租户/RLS、全学科可信数学求解、正式审核发布/PDF/DOCX、有限修订、版本化单题重生成、公共互联网部署。它们仍须保留未完成状态；本轮不能解除它们现有的阻断。

## 1. 当前事实：不要重新从空项目开发

以下是写计划时的本机核对结果，接手时必须重查易变运行状态。

| 项目 | 当前事实 | 接手时的动作 |
| --- | --- | --- |
| Git | `main`，既有基准 `1a89b534…`，大量修改和新增源码尚未提交 | 保留全部现场；不能 reset、clean、批量覆盖或把未跟踪文件当垃圾 |
| 日常前端 | `localhost:3000` 的 Vite 默认请求 `http://localhost:8000/v1` | 检查实际网络请求，不能只看页面标题 |
| 日常 API | 宿主机 Uvicorn `8000 --reload`，根 `.env` 中已增加本地 DATABASE_URL | 环境变更需要重启生效；不要输出 `.env` 内容 |
| 数据库 | 项目 PG 容器 `zhijuan-workflow-20260922-pg`，本机 `127.0.0.1:55432`；日常库 `zhijuan_local` | 这是当前草稿依赖，必须保持可用 |
| 当前草稿 | 23 题、15000 个 score_x100 单位；解答题分值 1200、1400×5；计划尚未确认 | 备份后再做任何改变；验收不要覆写用户当前草稿 |
| 当前健康投影 | database=true，queue=false，author=false，isolated_solver=false，runtime_verified=false | 目前只是配置存在性检查，不是存活性检查 |
| RabbitMQ | `zhijuan-workflow-20260922-mq`，本机端口 55672，当前停止 | 启用真实命题时恢复，不能误连其他项目队列 |
| Hermes / 费用代理 | 本轮验收命题、盲解、入口和预算代理容器均已停止 | 接入前复核环境、权限、来源与预算，不直接恢复所有旧测试容器 |
| 范围外保护对象 | `zygf-gitea`、`zygf-postgres` 属于其他项目 | 不调查其内部，不作为知卷依赖；不操作、不全局 stop、不退出 Docker |
| 内存 | 最近本项目 PG 约26 MiB；RabbitMQ 停前约147 MiB；Docker stats 的7.75 GiB为上限 | 不把上限当实际用量，不承诺关两个小容器能释放8GB |
| 费用账本 | 已受理16次请求，保守预留16元；不等于实际账单 | 旧账本必须延续，不能换文件/改RUN_NAME清零 |
| 界面按钮 | 真实生成配置不全，所以“确认计划并开始命题”禁用；已加邻近原因说明 | 不能只删 disabled；必须接好执行路径 |

已存在的关键实现：

- `services/api/store.py`：本地单份 current 草稿、规格版本、蓝图、数据库状态 CAS；规格变更取消旧任务；运行中拒绝同规格重拟蓝图。
- `services/api/repositories.py`：PG 任务、outbox、结果、历史；任务创建幂等、版本检查、旧结果拒写、run_id/用量事件落库。
- `services/exam/job_service.py`：显式启动、只读 GET/SSE、暂停/恢复/取消；活动槽结果不明时恢复进入 RECONCILING。
- `services/worker/jobs.py`：领取任务、按冻结题槽执行、每阶段登记外部运行、保存结果；`dispatch_outbox`、`reconcile_stale` 已存在。
- `services/hermes_adapter/http_adapter.py`：固定 Hermes 原生 Runs 受理/轮询/停止；身份不匹配或受理不明不重发；HTTP client 不继承系统代理。
- `services/exam/question_service.py`：author→确定性检查→隔离 solver→证据；确定性 FAIL 不继续付费盲解；不支持共享材料时失败关闭。
- `services/validators/candidate.py`：确定性检查；内容哈希和完整检查证据哈希分离；没有可信数学证明时 REVIEW。
- `apps/web/src/lib/scoring.ts`：逐题分值、严格配平、`canonicalSections` 保序转换不等分题；支持按既有契约把89个考点分到每组最多30个考点，超过容量明确拒绝。
- `apps/web/src/lib/sectionScope.ts`：将旧题型范围限制在教师已选范围内；调整后仍要求重新确认。
- `tools/project_memory.py` / `memory_finish.py`：记录闭环；`project_overview.py`：阶段证据展示。不要重建另一个记忆系统。

## 2. 先读取这些证据，正确理解通过范围

| 路径 | 证明什么 | 不证明什么 |
| --- | --- | --- |
| `acceptance-runs/workflow/sol-six-features-final-20260922-003/report.md` | 六个模块前一轮集成及边界 | 六项产品已全部完成 |
| `…/offline-final-004/report.json` | 当轮216项离线主测试及专项组通过 | 本轮后续改动仍被覆盖 |
| `acceptance-runs/workflow/workbench-startup-20260922-001/` | 日常库接线、219项Python、8项专属PG回归、前端及11题预览 | 日常真实生成已经启用 |
| `acceptance-runs/workflow/template-scoring-20260922-001/pipeline.json` | 实际Word解析→实际TS规范转换→专属PG保存→23题150分蓝图 | 调用了模型或验证了教学正确性 |
| `…/browser-readback.json` | 常用8000/Chrome的23题150分回读 | 确认开始按钮已经可用 |
| `acceptance-runs/workflow/sol-six-features-20260922-001/live-queue-strict.json` | 旧源码时真实单题队列链路完成，最终 REVIEW，6823 tokens | 最终源码的完整23题通过、学生API隔离或生产签收 |
| `acceptance-runs/maintenance/docker-restore-20260922-001/runtime.json` | 用户澄清不能影响使用，必要PG已恢复 | 可以再次停PG释放内存 |

早期 JSON 解析失败、评分表 FAIL 和超时记录必须保留。HTTP200、Hermes完成、任务COMPLETED、题目检查PASS、教师批准是五件不同的事。

## 3. 不变量与授权边界

- 保持 React/TypeScript、FastAPI、PostgreSQL、Celery/RabbitMQ、Hermes、DeepSeek 官方 API。不能用内存队列/SQLite 替换应用PG，不能旁路 Hermes 或加入其他 Agent 框架。
- SQLite 只在已有费用代理中作为限额账本，不是应用数据库替代物。
- 命题与盲解保持不同网关密钥、HOME、状态卷、工作目录、文件权限和工具集。不能因省内存合并为共享会话。
- 真正 provider key 只进入授权的模型出口；API、Worker、author、solver 使用各自内部凭据。禁止写进日志、计划、前端、报告或Git。
- `score_x100` 是整数；不改变题目分值来凑总分，不把REVIEW改PASS，不默认接受异常响应。
- 不停止必要数据库、其他项目容器、用户服务；不做 `docker compose down -v`、`docker system prune`、`git clean` 等清理。
- 不自动提交、推送、部署、发布题目。架构/接口/数据表/预算边界的新设计要写 decision，指出依据和影响；本文的建议字段和文件不能冒充已获生产批准。
- 本轮30元计费许可和本地限额代理许可只针对已有受控验收。接手先确认剩余额度与执行范围；不得推断获得长期无限调用授权。

## 4. 工作包顺序及修改责任

按 W0→W1→W2→W3→W4→W5→W6 执行。W1/W2可在接口约定后独立开展，W3必须等待预算和实际就绪检查。没有用户要求并行时不额外开代理。

| 工作包 | 对应原任务 | 主要文件 | 输出 |
| --- | --- | --- | --- |
| W0 现场保护和差异确认 | M0-05/M1-02 | 现有记录、运行状态 | 安全的现场快照、正确的数据库/进程归属 |
| W1 本地启动和资源边界 | M1-02/M1-04 | `infra/`、建议 `tools/local_runtime.py`、配置模板 | 可重复启动，不误停现有功能 |
| W2 真实就绪与预算预检 | M1-03/M1-04 | `health.py`、worker/repository、费用代理 | 只读真实依赖状态及明确失败原因 |
| W3 后端受理与任务状态 | M1-04/M1-06 | routes/job_service/repositories/worker | 持久、幂等、可恢复且不重复付费 |
| W4 前端完整状态闭环 | M1-05/M1-07/M2-01 | App、api、FoolproofSetup、Workbench | 有原因的按钮、真实进度、断网恢复 |
| W5 问题复核与失败收口 | M2-02/M2-03 | adapter、solver入口、validators | 隔离、检查、未知结果不重发 |
| W6 验收与交付 | 所有受影响任务 | tests、acceptance-runs、progress、docs | 独立证据和准确状态 |

如需增任务，使用经批准的 `progress/extra-tasks.yaml`，不改冻结的 `execution/task-index.yaml`。

## 5. W0：现场保护

1. 读取 `AGENTS.md`、`progress/current.md`，再用 `context --task M1-04` 等读相关交接。日期按真实UTC时刻排序；最新 Docker restore 交接取代此前 stop 建议。
2. `git status --short` 和必要的目标文件 diff；只读查看，不暂存、不提交。已存在的大量未跟踪教材图片、上传资料和源码均保留。
3. 只核对知卷已登记的容器及3000/8000/55432/55672/8643/8644等本项目使用的监听端口。容器优先按已确认的知卷名称筛选；不要做全机项目勘察。发现范围外服务时只记录必要的名称、监听地址/端口，不 inspect 其配置、卷、Env或日志，不连接它的数据库。知卷容器的 inspect 也只选所需非秘密字段，不整份输出 Env。
   - 同一个端口数字可能对应不同IPv4/IPv6或监听地址，不能只看“3000”就认定端口冲突。只需核对知卷目标URL的实际响应和自己的Vite监听。
   - 即使确认冲突，也不得自行修改/停止其他项目。先报告知卷受影响的入口和本项目可选的调整方案；用户未授权前不接管其他项目。
4. 从被忽略配置内部加载DSN，执行 `SELECT current_database(), current_schema()`；确认日常库为 `zhijuan_local`。不能通过“端口是55432”推断连接到了正确库。
5. 对日常库做本机受限目录备份，记录表行数和备份摘要，不把题目私有正文放进验收报告。备份不是允许清库。
6. 只读核对用户current草稿版本、计划哈希、题数、总分，留恢复点。所有故障注入/清理在新专属测试库或schema进行。
7. 记录预算账本 `calls/reserved_cny`、未决请求、文件权限及摘要，不记录provider key。当前账本路径见第7节。

完成条件：接手者能准确说出“谁依赖哪一个库/队列/网关”，且用户原页面仍能读保存和预览。

## 6. W1：日常本地运行接线

### 6.1 建议的最小本地拓扑

继续使用宿主机 Vite3000 + API8000；先不把整个应用重写为容器集群。

| 组件 | 日常连接 | 要求 |
| --- | --- | --- |
| API | `127.0.0.1:8000` | 根配置加载在导入store/worker之前；复用本项目.venv |
| PG | `127.0.0.1:55432/zhijuan_local` | 保留现有容器和卷，不创建第二份同名草稿 |
| MQ | `127.0.0.1:55672` | 建专用 vhost/队列或确保验收与日常broker严格分开；不要消费旧验收outbox |
| Worker | 一个本地进程，初始concurrency=1 | API/Worker/调度器必须相同DB/schema、部署标识、模型、网关配置 |
| outbox调度器 | 一个轻量本地进程 | 复用 `dispatch_outbox` 和 `reconcile_stale`；不得同时再启第二套beat |
| author | 现有验收使用 `127.0.0.1:8644` | 原生Hermes Runs；与solver独立 |
| solver-entry | `127.0.0.1:8643` | 精确白名单、内部鉴权；上游solver不直出宿主机 |
| budget-proxy | 专属Docker网络中8650 | 唯一官方模型出口；不可暴露无鉴权通用代理 |

**需要核查的复用限制：** `infra/workflow-acceptance/compose.yaml` 是验收专用，硬编码 `/tmp` 账本、镜像本机digest和验收profile，不能原样宣布为生产部署。日常复用其技术实现前，记录用途变更；新环境需要可重复构建的固定来源。现有 `infra/hermes-solver/Dockerfile` 仍有 `pip install -e .` 等构建期依赖，不能宣称全依赖可重现；复用当前已核验镜像或补锁定后再构建。

### 6.2 配置加载与文件

建议新增一份无密钥的 `configs/local-runtime.env.example`，列以下变量及用途：

| 变量 | 使用者 | 注意 |
| --- | --- | --- |
| DATABASE_URL | API/Worker/调度器 | 三者同一日常库；测试必须覆盖为专属库 |
| CELERY_BROKER_URL | API/Worker/调度器 | 相同vhost；不输出口令 |
| HERMES_API_BASE_URL / HERMES_API_KEY | Worker/API预检 | author入口及内部令牌 |
| HERMES_SOLVER_API_BASE_URL / HERMES_SOLVER_API_KEY | Worker/API预检 | solver-entry，不是solver上游 |
| HERMES_SOLVER_UPSTREAM_KEY | solver-entry / solver | 不给前端、不传给author |
| ZHIJUAN_DEEPSEEK_MODEL_ID | Worker/鉴别状态 | 与Hermes、proxy的允许模型一致；当前验收为deepseek-flash，执行前复核 |
| ZHIJUAN_BUDGET_PROXY_TOKEN | Hermes/proxy | 内部令牌，不是官方API key |
| DEEPSEEK_UPSTREAM_API_KEY | proxy单独持有 | 由本机凭据源内部注入；不能通过命令行打印 |
| ZHIJUAN_RUNTIME_ID（建议） | API/Worker/调度器 | 非秘密的本地部署ID，用于排除错误环境的心跳 |

复用 `services/api/settings.py` 的配置读取方式。不要 `source .env`：当前DATABASE_URL可能是含空格的libpq conninfo，根.env不是可信Shell脚本。应按键值数据加载，先完成加载再import worker模块；不得依赖Python模块偶然的导入顺序。

URL拼接必须核对：`HERMES_API_BASE_URL=http://127.0.0.1:8644`、`HERMES_SOLVER_API_BASE_URL=http://127.0.0.1:8643`，这里不追加`/v1`，因为适配器自己拼接`/v1/runs`；容器中的`DEEPSEEK_BASE_URL=http://budget-proxy:8650/v1`则包含`/v1`。当前共用`start.sh`即使启动author也读取名为`HERMES_SOLVER_MODEL_ID`的变量；不要只改变量名却不改启动脚本。API/Worker、两个Hermes及proxy的模型ID必须一致；不能遗漏设置而回退到另一个默认模型。

MQ若使用建议的新vhost `zhijuan-local`，显式配置该vhost及最小权限；API、Worker、调度器的URL全部一致。应用级队列仍可沿用`generation`，vhost隔离日常与验收；不要仅改队列名而让另一个组件继续消费旧队列。

### 6.3 最小运行工具

建议 `tools/local_runtime.py` 只提供 `doctor`、`start-generation`、`stop-generation`，不做通用编排框架：

- `doctor`：只读检查**知卷**的端口归属、目标库/schema、broker、心跳、网关配置、预算；输出组件名/状态/下一动作，不输出秘密。不得扩展为其他项目健康巡检。
- `start-generation`：确认PG已运行；仅启动本项目MQ和必要隔离网关；启动一份Worker与一份调度器；验证真实就绪后报告成功。用户已有API若必须重启，先保存/保护未提交草稿，等待活动任务处理策略明确。
- `stop-generation`：有活动任务时默认拒绝直接停进程，要求先取消或等待，并提示未知结果对账；无任务后按调度器→Worker→author/solver/费用出口→不再使用的MQ收尾。**绝不停止PG、Vite、API或其他项目容器。**
- PID记录写入被忽略、权限受限的本地运行目录；停止前验证PID当前身份与归属，不能只凭旧PID文件kill。
- 启动失败只停止本次新起且已确认属于本项目的进程；保留原来运行的PG和用户服务。
- Docker资源检查报告“实际使用/上限”两列，不能把 `/ 7.75GiB` 当实际使用；不要为了达成低内存数字关闭功能。

Worker命令候选（实现者需先验证参数与现有锁定版本）：

```bash
# 环境由安全的Python启动器注入；不要直接打印或source秘密文件。
.venv/bin/celery -A services.worker.jobs:app worker \
  --pool=solo --concurrency=1 --without-gossip --without-mingle --without-heartbeat \
  --loglevel=INFO
```

这是本地单并发选择，不是生产扩展建议。现有配置关闭了Celery remote control/events以适配RabbitMQ4；不要用 `inspect ping` 无响应就判死，也不要为了探测而盲开这些已知有兼容问题的队列。

## 7. W2-A：预算必须先于真实模型验收

### 7.1 当前不能直接跑23题的算术

`tools/live_budget_proxy.py` 当前常量：MAX_REQUESTS=20、MAX_RESERVED_CNY=30、RESERVE_CNY=1、MAX_BODY_BYTES=200000、MAX_OUTPUT_TOKENS=4096。账本已用16次，保守预留16元。

- 当前请求次数余量只有4次，不是14次。
- 成功命题+独立盲解，每题至少两次上游请求；23题至少46次，且Hermes续写/重试可能更多。
- 即使只提高20次上限，46×1元也超过剩余14元的保守预留额度。
- 实际token费用可能远低于预留，但没有官方账单/经验证结算逻辑时不能擅自把旧预留清零。

**默认执行选择：保留现有限额，先做完全无费用的集成/浏览器回归；额度允许时做小规模真实冒烟。完整23题验收单独受预算门控。**

想在原30元范围内支持更大测试，必须先设计并审查按严格上界预留的改进，或获得明确新增预算。不能让接手AI简单改MAX_REQUESTS、换RUN_NAME或新建账本绕过限制。

### 7.2 费用代理最低增强

1. 增加只读、内部鉴权的预算状态接口，例如 `/internal/budget`（新接口，记录decision）。返回 run_id/计数/上限/预留额/未决条数；不要返回key、提示词、题目正文或推理。
2. API发起计划确认前获取预算快照；服务端受理时再检查。记录 `budget_revision` 或快照时刻，前端的结果不能作为最终授权。
3. 返回机器原因 `BUDGET_INSUFFICIENT`，包含本计划最低请求量、可用余量和“最低估计不是严格最坏上界”的说明；不得先开始两题再发现整卷必然跑不完。
4. 代理仍必须每次上游I/O之前在SQLite事务中原子预留；预检不是替代真正的扣限。
5. 同一全局限额下的并发任务要么增加受审查的计划级额度租约，要么明确只允许一个活动验收任务，并测试预检后额度被其他请求消耗时安全终止。不能承诺没有预留的预检一定保证完成。
6. 把 `/tmp/zhijuan-workflow-20260922/budget/acceptance.sqlite` 迁到持久受限目录前，先停代理、备份/校验、原样复制所有历史行和RUN_NAME；保留原文件，不凭复制操作重置16次。位置变化必须同步挂载与文档。

### 7.3 如采用精确上界预留（可选，非默认已批准）

- 金额用整数微元/分或Decimal，不能用float累加；为旧整数元记录做显式迁移，保留历史16元预留。
- 记录当前官方模型价格来源、核查时间、输入token可证明上界、输出cap、兑换/税费余量和计算公式；**不能不加证明就把UTF-8字节数等同token数**。
- 上界预留必须包含消息包装开销、Hermes可能的附加请求、失败/未知结果；每次收费请求独立记账。
- 只允许受信计量在可核验结算时释放差额；UNKNOWN/缺usage不可当零费用退回。
- 价格或模型不在核验名单、格式不受支持时拒绝，不猜测新费率。
- 对迁移、并发、崩溃、重启、四舍五入边界、旧账延续做完整离线测试后，才考虑真实调用；修改金融/调用边界需新增decision和批准依据。

## 8. W2-B：从“存在配置”升级为真实就绪

当前 `generation_configuration()` 仅检查环境变量；`readyz`不检查数据库连接、Worker、outbox运行或网关可达性。不能将 `configured` 直接作为最终按钮使能条件。

建议保留当前字段兼容，增加 `generation.ready`、`checked_at`、`reason_codes` 和逐组件检查：

```json
{
  "configured": true,
  "ready": false,
  "runtime_verified": true,
  "reason_codes": ["WORKER_UNAVAILABLE"],
  "components": {
    "database": {"ok": true},
    "broker": {"ok": true},
    "worker": {"ok": false},
    "dispatcher": {"ok": true},
    "author": {"ok": true},
    "solver": {"ok": true},
    "budget": {"ok": true}
  }
}
```

该JSON是**拟定契约**，不是已有返回值。只读健康接口不因读取而创建任务或模型请求；参数和路径与项目decision对齐后实施。

具体实现要求：

- DB：带短连接/查询超时执行只读查询，核对需要的表和正确schema；不可自动迁移，也不能异常时落回seed。
- broker：短超时建立AMQP连接或被动检查目标队列；可达并不代表消费进程存在。
- Worker和调度器：建议新增 `database/005_local_runtime_heartbeats.sql` 与相应repository方法。最小字段 `runtime_id, component, instance_id, last_seen_at`，主键能区分实例；DB服务器时间写入。API只接受同部署ID且足够新鲜的心跳。
- Worker在真正就绪后每5秒发送一次轻量心跳，进程关闭时撤销/过期；建议用明确启停的后台线程，不能用“由同一个阻塞单线程Worker消费的心跳任务”证明自己始终存活。
- outbox调度器每轮成功读取/处理后登记心跳；初始建议2秒tick，过期阈值如20秒作为**待实测参数**；不能通过API自写心跳模拟Worker。
- 心跳身份必须绑定日常DB/schema/部署ID，不能接受连验收库的Worker心跳。实例ID在进程启动生成，重启后旧实例不能持续证明就绪。
- Worker心跳或安全运行元数据还要声明所用模型、网关角色配置版本；API发现默认模型或网关版本不一致时拒绝就绪，不能“连得到就算接对”。只能记录非秘密标识或配置版本，不记录令牌原文/可猜测秘密的哈希。
- author：使用固定Hermes源码真实存在且不计费的HTTP健康/鉴权路径。先查 `vendor/hermes-agent/gateway/platforms/api_server.py`，不要猜 `/health` 存在或通过发起Run探活。
- solver：当前 `isolation_gateway.py`只允许精确Runs接口，没有通用health。新增窄的内部readiness路由时维持鉴权及role边界；检查隔离上游进程与配置，不把任意URL转发做成健康接口。
- budget：读取上述只读预算状态，未知/不可达时禁用收费功能；不能把`/models`本地静态列表当账本或官方计费连接验证。
- 所有探测设置总时间预算、短超时和短TTL缓存，避免每个前端轮询建大量连接；缓存过期/探测失败不得延续旧绿色状态。测试时间参数，不把推荐阈值直接当生产结论。
- `/health`继续代表API活着；`/readyz`失败应返回明确非就绪状态。草稿服务和生成服务分开显示，生成不可用不能把全部工作台误标为损坏。

新增心跳表属于本地运行元数据方案，不是完整租户数据库迁移。执行前写decision、说明影响及回滚；测试库先执行，再核对日常库备份和版本，不跑全局生产迁移。

## 9. W3：服务端受理、幂等和状态恢复

### 9.1 受理入口

修改 `services/api/routes/exams.py::start_generation_job` 和 `GenerationJobService.start_job` 的直接调用链：

1. 校验current范围、If-Match和当前规格版本，仍保留428/412语义。
2. 检查已确认蓝图、规格/蓝图hash/revision、题槽、预算及真正运行就绪。已有同版本任务的重放应优先返回已有身份，不因为服务暂时掉线就诱导客户端再次建新任务；明确该判断与预算“只读回放不收费”的关系。
3. 在repository现有共享advisory事务锁中再次核对持久化蓝图与当前版本，不能信任提前读的plan。
4. 一个事务写job+outbox，提交之后由独立调度发送。HTTP线程不得调用模型。
5. 受理成功202，固定返回job_id和当前状态；前端只能据此切进度。配置/就绪不足503，版本冲突409/412，预算不足用明确409或429并锁定测试契约；不要把所有错误包成400或返回raw exception。
6. 后端保留当前禁止未版本化重生成、禁止正式发布的规则。不要借本次连通生成而重新打开这两个未完成入口。

### 9.2 Outbox和Worker

- 复用 `dispatch_outbox`，发送确认后才标记已发送。发送成功但确认丢失允许重复投递同job_id，不允许生成新的job_id。
- Worker对同job_id重复投递先读当前状态；只有QUEUED且成功CAS到RUNNING者可进入收费阶段。并发失败者退出，不能重发模型请求。
- 每一题、每一阶段坚持稳定task_ref：`job_id:slot_id:author|solver`；受理真实run_id后先持久化，再继续。
- 增加明确的安全error_code和用户可读reason，保留原始诊断在受限本机日志；API/SSE不输出密钥、私有推理或任意模型错误正文。
- 仅一个local current活动任务时，写明这一限制；不要把它伪装成多租户、无限并发产品。

### 9.3 状态语义

| 状态/转换 | 必须的行为 |
| --- | --- |
| QUEUED | 已持久受理，尚无模型调用；刷新/GET/SSE不产生执行 |
| RUNNING | Worker已成功领取，逐槽写状态；用量未知显示未知 |
| PAUSED | 停止新阶段；已受理上游尽力stop，不保证立即停止计费 |
| CANCELLED | 不启动新请求，不再写入迟到结果；保留账本/run_id |
| RECONCILING | 外部受理/结果未知；禁止自动重发，同run_id查回或人工处理 |
| FAILED | 有明确失败事实，例如不合格结构；不写成功题代替 |
| PARTIAL_FAILED | 至少一槽FAIL；保留其他结果但不显示整卷完成/可发布 |
| COMPLETED | 所有槽已走完流程；仍可含REVIEW，不能显示“题目全部正确” |

暂停恢复规则保留现有保守处理：槽处于AUTHORING时resume进入RECONCILING，不跳回QUEUED重复计费。确知上游未受理才能恢复未执行阶段；这需要受信对账证据，不靠模型文本声称。

### 9.4 明确的故障窗口

必须覆盖：写job前；job/outbox提交后发送前；broker收取后标记前；Worker领取后模型前；上游受理后run_id落库前；author完成后solver前；结果存储前；结果已存但前端断线。

各窗口先判定“确实未调用 / 已知run_id / 无法判断”再恢复。未知时宁可待对账，不盲目重发。已有状态机没有实现的恢复路径要登记待办，不能把重启Worker当作已经恢复。

## 10. W4：前端完整闭环

### 10.1 App与api客户端

修改入口：`apps/web/src/App.tsx`、`lib/api.ts`。

- 增加类型化运行状态，不再只取configured布尔值；旧服务缺字段时fail-closed，显示“服务版本/状态未确认”，不能误绿。
- 草稿、候选、生成状态分开加载并分别处理失败。草稿可读而生成不可用时页面仍可编辑；DB真的不可达必须说明保存受影响，不能返回seed冒充恢复。
- 以一个明确的草稿状态源驱动页头和编辑页。当前截图“高一150分编辑内容，页头仍九年级100分”是已知未修项；通过 `onDraftChange` 或提升状态修复，不靠直接DOM修改。
- 保留初始化保护；已输入内容不能被慢请求、热更新、就绪轮询覆盖。ETag过期时提示冲突和重载/保留副本的选择，不能静默丢编辑。
- 提供“重新检查生成服务”操作；可加轻量定时刷新，离开页面/切换任务清理请求和SSE。恢复就绪时不能清空用户23题计划或自动发起生成。

### 10.2 规格、模板、教材范围

修改入口：`FoolproofSetup.tsx`、`ExamSetup.tsx`、`lib/scoring.ts`、`lib/sectionScope.ts`、教材选择组件。

- 已修复的逐题分值链路保持：模板item_scores优先且与声明总分核对 → canonicalSections → 保存后的规范spec → 蓝图；两个配置页都用保存后的返回值。
- 不要再在请求构造处仅复制count/score_each而忽略逐题数组；原模板23题150分必须测试到后端持久结果。
- 按钮附近展示精确禁用原因：检查中、配置缺失、Worker掉线、预算不足、计划过期、未确认范围、已有活动任务。不能都归为“网络错误”。
- 当前math小测卡写“5题”，实际预设3+2+1=6题，是已知显示缺口；让卡片计数/总分从同一预设数据计算，不能复制多套硬编码文案。
- 导入模板时明确显示“自定义模板”，不要仍高亮月考并让用户误以为只有11题。时间、题数、分值明细使用当前实际数据。
- **范围遗留问题必须处理**：用户切到高中教材后，旧九年级4个考点仍留在已选范围，最新23题计划前几题仍可出现这些旧考点。不能把这种结构合法当课程正确。
- 设计最小范围来源信息，区分教材章节/手动补充/模板建议；跨学段或教材切换时明确提示哪些旧范围失效，让用户选择清除/保留适用项并重新确认。不得静默把别的学段考点加入新卷，也不能自动删除用户手工意图。
- 全书范围包含章节标题、正文小节、“阅读与思考”等；不要按字符串自动保证所有项都是可出题知识点。保留课程范围检查/教师确认，给出不适用项说明，后续能力注册未完成就标明限制。

### 10.3 确认与启动

确认前保存并生成的plan带spec_revision/plan_revision/hash。仅当本地规格未改、服务真就绪、预算通过且未在提交中时使能。

点击后立即加单次提交锁；POST202返回后转进度。若响应丢失，先GET同规格/同plan任务并对账，找到则恢复；找不到且是否受理未知时停在RECONCILING说明，不自动POST第二次。后端幂等是最终保护，按钮锁只是体验。

不能把“确认计划”与“收费任务受理”之间的错误吞掉。如果确认已成功但费用/就绪预检随后失败，保留已确认计划并显示可恢复原因，不让用户误以为已开始命题。

### 10.4 进度与候选页面

- 改 `ExamPaperWorkbench.tsx` 和仍被调用的 `JobProgress.tsx`。枚举和服务端一致，不把所有有job的状态都当“正在生成”。
- SSE连接掉线时显示重连/读取状态，先GET后订阅；绝不能发启动POST作为重连动作。
- FAILED、PARTIAL_FAILED、RECONCILING、CANCELLED需有终态/需处理页面，避免永远转圈；已产生结果按服务器允许范围展示。
- token只用受信usage；缺一阶段则显示部分已知/总量未知；费用未知保留未知。不要用时间或字数估算冒充真实用量。
- REVIEW题明确待教师复核；保留禁用的版本化单题重生成和未完成发布路径。
- 页面用户文案用中文题型名，slot里single_choice等内部枚举不直接堆给教师；诊断细节放开发信息区域。

## 11. W5：Hermes、隔离与输出完整性

固定来源先查 `install/` 锁定记录和vendor实际提交；不修改vendor规避边界。原生调用形状以 `http_adapter.py` 和固定 `api_server_runs.py` 为准。

保留以下已实现约束并补运行验证：

- author返回必须是契约JSON；缺答案/评分/内容字段失败，不补A、不重写分数、不丢弃复杂块换绿。
- solver只收公开题目投影；递归拒绝private、answers、rubric等。更换提示词不等于隔离。
- solver-entry拒绝任意session、工具、其他provider/model及未列路径；健康路由的新代码也不能扩大转发权限。
- GET状态的run_id与受理ID一致，完成标志和payload齐备后才成功；中断时保留真实ID。
- 受理事件、完成事件落库失败、取消检查失败均返回未知并尽力stop，不自动重开Run。
- shared materials仍未实现；必须在收费之前尽可能早拒绝，不能偷偷把私有材料或答案填进solver。
- 真实一致答案不足以证明数学正确；无可信数学求解保持REVIEW，不改checker规则让验收通过。

## 12. 运行数据、迁移与回滚要求

现有表及唯一用途：`generation_exam_state`草稿；`generation_exam_revisions`规格围栏；`generation_jobs`当前任务；`generation_job_outbox`派发；`generation_job_results`每槽结果；`generation_job_history`旧任务/run_refs。先画出读写清单再改事务。

如增加心跳/预算关联字段：

1. 新迁移文件，不原地假装旧表已部署；先在新专属测试schema执行。
2. 新版本必须能读旧任务缺可选字段的历史记录；不能因默认值把未知预算或状态改成成功。
3. 写入仍走受信服务，Agent不能修改检查规则、预算或发布状态。
4. 下线新runtime代码时保留原有任务和结果；迁移回滚不自动DROP结果表。优先停止新写入、回退代码/配置，再核对备份。
5. 本地文件迁移仅对自己创建的受限运行文件操作；用户上传、教材、其他项目数据库均在范围外。

## 13. 验收执行顺序与证据交付

详见 [测试矩阵](2026-09-22-local-generation-test-plan.md)。按顺序：静态/单元 → 隔离PG → 假Hermes+真实队列 → 故障注入 → 浏览器 → 限额内真实单题 → 获额度支持后的多题。未通过前级不靠真实模型碰运气。

每次用新 `acceptance-runs/<类型>/<唯一run-id>/`，至少包括：

- `report.md`：问题、变更、已验收范围、未验收、失败原因和恢复方式；
- `manifest.json`：源码指纹、Git现场、Python/Node/依赖/镜像版本、DB逻辑名/schema、命令/退出码；不含DSN密码；
- 单元/集成计数：0测试、skip、missing result均不算PASS；
- runtime探测：组件真实检查、Worker/调度心跳、broker归属、API是8000而不是8001；
- 任务/run_ref/结果数量和分值、版本围栏及副作用断言；不导出私有推理；
- 浏览器证明：正常、配置不足、网络异常、刷新恢复和终态的画面/可访问性观察；
- 费用前后账本摘要：请求数、预留额、未知条目；实际费用未知就写未知；
- `not_run`：明确列出全卷、教学质量、角色/学生API、发布/导出等未执行项。

更新对应 `progress/work.yaml`、`features.yaml` 和独立handoff，运行 `status --write`、`check --strict-evidence`、`finish --task`。工具PASS仅证明记录闭环；只有完整范围和独立应用验收满足时才把产品任务DONE。本计划不会预先提升任务状态。

## 14. 可复制给接手AI的执行要求

> 请接手 `/Users/fangzengxing/zhijuan_spec_v1_4`。先读 `AGENTS.md`、本实施计划和配套测试矩阵，再按W0–W6实施。用户要的是常用localhost:3000/8000真实可用，不接受只在另一个验收端口跑通。保留所有未提交/未跟踪修改、当前高一23题150分草稿和教材选择。数据库必须保持可用；不要停其他项目Docker服务。复用现有PG/outbox/Celery/Hermes隔离链路，禁止mock冒充真实生成、放宽校验或重发未知收费请求。现有30元验收账本已用16/20次，完整23题至少46次上游请求；先做无费用验证，不能清零账本或绕过预算。逐文件实现计划中的运行接线、真实就绪、预算预检、幂等和前端状态闭环；对架构/接口/预算新增项记录决策和批准依据。按测试矩阵保存真实结果，更新progress并通过finish；未做项如实说明，不把局部通过当全产品完成。未经用户明确要求不提交、推送或公开部署。
