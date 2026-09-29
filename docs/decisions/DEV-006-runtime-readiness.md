# DEV-006：生成运行时真实就绪探测（readyz 升级）

状态：PROPOSED
提出人/日期：编码子代理 / 2026-09-23（实施计划 §8 W2-B）
批准人/日期：尚未批准
关联任务/功能：M1-03/M1-04；本地日常生成接通（W2-B）

## 背景和约束

现有 `/readyz` 的 `generation_configuration()` 只检查环境变量是否存在（`services/api/health.py`），
`runtime_verified` 恒为 false，不能作为"确认计划并开始命题"的真实门禁。实施计划 §8 要求从"存在配置"
升级为逐组件真实探测，且必须：只读（不创建任务、不调模型、API 不自写心跳）、总时间预算约 8 秒、
结果 TTL 缓存、缓存过期后不得延续旧绿状态、/health 继续只代表 API 存活。

跨任务契约（C1–C6）据此立项：C1 定义 /readyz generation 块结构（ready/checked_at/reason_codes/
components 与限定的 reason_codes 集合）；C2 定义心跳表与 `runtime_heartbeats.py` 的
`fresh_components`（由并行任务实现）；C3 定义只读预算端点；C4 定义环境变量默认值；C5/C6 分别约束
受理错误与前端展示。本决策只覆盖 readiness 侧实现与隔离网关的窄 readiness 路由。

## 可选方案与证据

- 保留纯配置检查：不满足"真实就绪"要求，按钮会错误可用。
- 探测 worker/dispatcher 用 celery inspect/ping 或通道探测：实施计划 §6.3 已说明关闭了 Celery
  remote control/events 以适配 RabbitMQ4，inspect 无响应不能判死；改用心跳（C2）。
- author 探活用发起真实 Run：会计费且不可接受；改为固定 Hermes 源码真实存在的无鉴权、不计费
  `GET /health`（读 `vendor/hermes-agent/gateway/platforms/api_server.py`：`_http_route_table`
  注册 `("GET", "/health", self._handle_health)`，`_handle_health` 返回
  `{"status": "ok", "platform": "hermes-agent", "version": _hermes_version()}`，不读环境密钥）。
- solver 探活复用通用转发：违反"健康路由也不能扩大转发权限"（实施计划 §11）；改为在
  `isolation_gateway.py` 新增窄内部路由 `/internal/readiness`，保留既有 hmac Bearer 鉴权与 role 边界，
  只返回非秘密配置状态，绝不转发任何内容。
- budget 探活把 `/v1/models` 当账本校验：DEV-004 已说明 `/v1/models` 纯本地静态列表，
  不访问上游也不代表计费连接；改为只读 GET /internal/budget（C3），未知/不可达一律 fail-closed。

## 选择及原因

采用：`runtime_readiness()` 并发探测 7 个组件（database/broker/worker/dispatcher/author/solver/
budget），每组件独立短超时（默认 2.0s，C4），TTL 缓存（默认 3.0s，C4）；缓存键含配置签名与
单调时间戳，任何配置变化或缓存过期都整体重建结果，永不把旧 ok=true 带进失败周期。
/readyz 返回 READY / NOT_READY / NOT_CONFIGURED；/health 保持不变。
失败原因只使用 C1 限定的 reason_codes；components 中每个条目形如 {ok, detail?}（内部 reason
不输出给前端，仅用于汇总 reason_codes）。

- database：独立连接短超时 `SELECT 1` + information_schema 断言 6 张 generation_* 表
  （database/003_generation_jobs.sql、004_generation_exam_state.sql 建表范围）；异常即
  DATABASE_UNAVAILABLE。禁止自动迁移、禁止异常时落回 seed。
- broker：kombu Connection 短超时连接（复用 CELERY_BROKER_URL）；连接可达≠消费者存在，
  消费者由心跳判定。
- worker/dispatcher：调用 C2 `fresh_components(runtime_id, TTL)`；无表/无心跳/过期即不可用；
  metadata.model_id 与 `settings.deepseek_model_id` 不一致即 MODEL_MISMATCH；心跳 age 到达 TTL
  边界防御性判为 HEARTBEAT_STALE；跨 runtime_id 的心跳一律不在结果中（被拒）。
- author：GET {HERMES_API_BASE_URL}/health（vendor 真实存在，无鉴权、不计费）。
- solver：GET {SOLVER_API_BASE_URL}/internal/readiness 带 Bearer HERMES_SOLVER_API_KEY；
  author 与 solver base URL 相同（含仅尾斜杠差异）→ ISOLATION_MISCONFIG。
- budget：GET C3（URL+token，C4 默认）；token 未配置/超时/非 JSON/缺字段/字段非法均
  BUDGET_UNAVAILABLE（fail-closed，不得当 0 已花或无限额度）。

## 数据、接口、权限、成本与兼容影响

- `generation_configuration()` 字段（configured/checks/runtime_verified）原样保留，兼容既有调用
  （`routes/exams.py` 的 503 门禁与既有测试）。
- generation 块新增 ready/checked_at/reason_codes/components，按 C1。
- /readyz 新增 /v1/readyz 别名（前端按 /v1 前缀调用，C6/现有 Web 均以 /v1 readyz 读取）。
- API 进程只读心跳表，绝不写心跳（避免 API 自写心跳冒充 Worker）；心跳仍由 Worker/调度器线程负责。
- 无鉴权、无计费调用、无写库、无 schema 变更；solver 网关新增路由需要 HERMES_SOLVER_API_KEY
  才能访问，不暴露任何上游内容。
- 预算探测需要 ZHIJUAN_BUDGET_PROXY_TOKEN；未配置时生成服务按不可用处理（BUDGET_UNAVAILABLE）。

## 实施/迁移/回滚

- 修改 `services/api/health.py`（探测、缓存、/readyz 升级）与
  `services/hermes_adapter/isolation_gateway.py`（窄 readiness 路由）。
- 新增 `tests/test_runtime_readiness.py`（离线，mock 各探测点 + 127.0.0.1 临时 HTTP 服务器）。
- 依赖并行任务落地的 `services/api/runtime_heartbeats.py::fresh_components`（C2）与
  settings.py 的 C4 字段；本实现以 os.getenv 同名读取，模块缺失时 worker/dispatcher 按不可用降级。
- 回滚：恢复 health.py /isolation_gateway.py 旧版本即可，无数据迁移；心跳表保留不回滚 DROP。

## 必须重跑的测试

`tests/test_runtime_readiness.py`（54 例：全绿、DB 断、broker 断、无心跳、心跳过期边界前后、
跨 runtime_id 拒绝、模型不一致、author==solver、budget 401/超时/坏 JSON fail-closed、缓存过期
不延续旧绿、reason_codes 精确性、网关路由鉴权与不转发），以及既有
`tests/test_generation_configuration.py` 兼容性。

## 关联文件及被替代决定

`services/api/health.py`、`services/hermes_adapter/isolation_gateway.py`、
`tests/test_runtime_readiness.py`；契约详见 W2-B 与 C1–C6。不替代 DEV-004（预算闸门）与
正式架构审批。
