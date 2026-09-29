# DEV-009：生成任务受理错误契约与受理顺序

状态：PROPOSED
提出人/日期：编码子代理（W3）/ 2026-09-23
批准人/日期：尚未批准
关联任务/功能：M1-04/M1-06；实施计划 §7.2、§9 W3；对外契约 C5/C4

## 背景和约束

`start_generation_job` 原来是“If-Match → configured → start_job 一把梭”，把一切异常包成裸 400，且没有幂等重放、没有真实就绪门禁、没有预算门禁，也没有随任务持久化的预算快照。断网/双击/服务重启时客户端无法安全重放（可能重复创建任务、重复计费）。实施计划 §9.1 要求：受理必须按固定顺序执行门禁，错误按机器可读 code 分类，禁止裸异常、禁止全部包成 400/500。

本文件只定义**受理入口**的行为；心跳表、就绪探测探针、预算代理状态接口分别由并行契约 C1/C2/C3 覆盖，这里引用它们的用途但不重定义。

## 可选方案与证据

- **方案 A：全部错误包成 400**。旧行为。前端无法区分版本冲突、未确认、未就绪、预算不足，无法给出精确禁用原因（计划 §10.2 要求按钮附近精确原因）。拒绝。
- **方案 B：自定义异常 `AcceptError(status, code, reason, **fields)`，路由统一转 `JSONResponse`，body 为 `{code, reason(中文), ...}`**。保留 HTTP 状态语义（428/412/409/503），附加机器 code 与可读中文。经本机 FastAPI 0.141 实测：路由 `status_code=202` 不会覆盖显式返回的 `JSONResponse(409/503/…)`；`HTTPException(detail=dict)` 会包一层 `{"detail": …}`，而 `JSONResponse(content=…)` 保持扁平 `{code, reason, …}`。选用方案 B。
- **方案 C：全局异常中间件**。改动 `main.py`（不在本任务文件清单）会扩大回归面，且路由内显式返回更贴合既有代码风格。不用。
- **幂等重放方案**：在同 `spec_revision + plan_hash` 已有任务时，任何状态都返回既有 `job_id`/`status`，不新建 outbox、不查预算、零副作用。相对“每次都新建”避免了掉线后客户端重复提交导致重复受理。repository 新增只读 `find_by_plan`。

## 选择及原因

1. **受理顺序固定**：current 范围与 If-Match（缺→428、过期→412）→ 已确认蓝图（无→409 PLAN_NOT_CONFIRMED）→ 幂等重放（同版本已有任务→202 返回既有身份，零副作用）→ 真就绪门禁（503 GENERATION_NOT_READY 含 reason_codes）→ 预算门禁（GET /internal/budget 带 min_requests=2×slot_count；不足→409 BUDGET_INSUFFICIENT 带动态字段；不可核对→503 BUDGET_UNAVAILABLE）→ 锁内二次核对持久化蓝图（复用 `repositories.create` 既有 advisory 锁 + `generation_exam_revisions`/`generation_exam_state` 核对）→ 单事务写 job+outbox（预算快照随 job 持久化）→ 提交后由既有 dispatch 调度。HTTP 线程绝不调用模型。
2. **幂等重放优先于就绪/预算门禁**：服务暂时掉线时客户端重放不应因“就绪不足”被误拒，更不应诱导再次建任务（计划 §9.1 第 2 条）。重放路径永不收费。
3. **预算快照**：`budget_snapshot`（run_id、checked_at、min_requests）写入 job 快照 jsonb，随任务创建同事务持久化。`generation_jobs.snapshot` 本就是 jsonb，无需新列；旧任务没有该字段仍可读（“旧行可读”），因此**不新建 006 迁移文件**（任务允许“视需要”）。金额保持整数（score_x100 之外也不引入 float 累加；快照只记录代理返回的整数/时间戳）。
4. **错误 body 一律 `{code, reason(中文), ...}`**；只有“生成服务未配置”沿用旧 detail 字符串文案（冻结测试 `tests/test_generation_configuration.py` 断言 `'暂不能开始出题' in detail`，与 C5 不冲突——它不是 C5 列出的错误类别之一，保留为配置缺口提示）。未知内部异常不再包含 `str(exc)`，统一“开始命题时发生内部错误，请稍后重试”。

## 数据、接口、权限、成本与兼容影响

- 端点行为变化：`POST /v1/exams/{exam_id}/generation-jobs`。202 成功返回 `{job_id, status}`；错误返回 C5 规定的状态码 + `{code, reason, ...}`。
- 对外契约 C4 新增环境变量落在 `services/api/settings.py`（`runtime_id`、`budget_internal_url`、`budget_proxy_token`、`budget_ledger_path`、`heartbeat_ttl_seconds`、`readiness_probe_timeout`、`readiness_cache_ttl`），读取方式沿用该文件现有 `Field(default_factory=os.environ.get)` 风格。
- 预算探测是**只读** GET `/internal/budget`：不预留、不调用上游、不改账本。幂等重放路径不调用预算接口。
- 兼容：`GenerationJobService.start_job` 保留为旧直接创建入口（既有单元测试与 worker 依赖它的语义），新增 `accept_job` 承担完整门禁；路由改调 `accept_job`。`replay_job` 提供掉线后的 GET 对账入口，零副作用。
- 旧任务：生成任务没有 `budget_snapshot` 字段时所有现有读取路径照常工作；`_public` 不暴露该字段给 202 响应，属内部审计记录。
- 预算快照只随任务持久化，绝不在 HTTP 线程被用于扣费；代理仍在每次上游 I/O 前原子预留（DEV-004），预检不替代真正的扣限。

## 实施/迁移/回滚

- 修改文件：`services/api/routes/exams.py`、`services/exam/job_service.py`、`services/api/repositories.py`、`services/api/settings.py`；新增测试 `tests/test_generation_accept.py`。不建新表，无需数据迁移。
- 回滚：恢复旧路由实现即可；不删除任何表、不改动旧账本。预算快照字段缺失不影响旧任务读取。

## 必须重跑的测试

- 本任务新增离线测试 `tests/test_generation_accept.py`（12 项，覆盖 428/412/409/503/409-BUDGET/503-BUDGET/重放 202 零副作用/成功 202/锁内二次核对拒绝/预算快照字段），全部通过。
- 冻结测试 `tests/test_generation_configuration.py`、`tests/test_generation_pipeline.py` 不回归（一并运行共 18 项通过）。
- 真实验收仍须按测试矩阵 J01–J13 与 B05/B06 在专属 PG/队列环境复核；本决策不代签产品验收。

## 关联文件及被替代决定

关联：C1（readyz/runtime_readiness，由并行任务落地）、C2（心跳）、C3（预算状态只读接口）；实施计划 §7.2、§9；`tests/test_generation_pipeline.py`（旧 start_job 语义）。不替代 DEV-004（预算代理方案）。本文件记录的受理顺序与错误 code 是对外契约 C5 的实现决策。
