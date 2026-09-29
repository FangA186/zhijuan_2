# DEV-008：费用代理只读内部预算端点

状态：PROPOSED
提出人/日期：编码子代理 / 2026-09-23
批准人/日期：尚未批准
关联任务/功能：W2-A（实施计划 §7.2）；T4

## 背景和约束

实施计划 §7.2 要求费用代理新增只读、内部鉴权的预算状态端点，供 API 在执行计划确认前获取预算快照。当前代理只暴露 `/v1/chat/completions`（转发上游）和 `/v1/models`（本地静态列表），没有可供 Worker/API 查询当前额度、预留和未决申请的内部接口。

约束：
- 端点必须只读：不产生预留、不调用上游、不改账本。
- 内部鉴权使用 `ZHIJUAN_BUDGET_PROXY_TOKEN`；代理未配置该令牌时端点返回 503 "未启用"。
- 响应遵循契约 C3（`readiness JSON` 中的 `generation` 字段），包含 `run_id`、计数、上限、预留额、未决条数、充足性判断、缺口和检查时刻。
- 可选查询参数 `min_requests`（正整数），用于检查当前额度是否足够支撑一次完整计划；不足时返回 `BUDGET_INSUFFICIENT` 及具体缺口。
- 账本路径默认保持 `/tmp/zhijuan-workflow-20260922/budget/acceptance.sqlite`；新增可选环境变量 `ZHIJUAN_BUDGET_LEDGER_PATH` 覆盖。
- 响应不得包含 Key、提示词、题目正文或推理中间结果。

## 可选方案与证据

1. **在现有代理进程中新增只读路由**：修改 `tools/live_budget_proxy.py` 的 HTTP handler，在 `do_GET` 中识别 `/internal/budget` 路径，调用新方法直接读 SQLite 账本。改动最小，不引入新依赖，复用已有鉴权和账本访问逻辑。
2. **独立 HTTP 端点进程**：启动一个独立 Web 服务读取同一 SQLite 账本。增加部署复杂度、端口管理和并发一致性问题（两个进程读同一 SQLite 文件可能产生锁争用）。
3. **通过现有 API 路由查询预算状态**：让 API 直接读 SQLite 文件。这会破坏代理作为唯一模型出口的安全边界，且需要 API 拥有文件系统权限。

选择方案 1，因为它在现有安全边界内以最小成本满足需求，且一致性最好（单一进程读自身内存状态+SQLite）。

## 选择及原因

选择方案 1（新增代理进程内路由）。原因：
- 零新增依赖：代理已包含 `http.server`、`sqlite3`、`json`。
- 原子性：单进程读取自己的账本，无外部文件锁竞争。
- 安全边界保持：预算状态只通过内部鉴权后的 HTTP 接口暴露，不把文件系统权限扩散到 API 进程。
- 实施计划 §7.2 明确要求"代理仍必须每次上游 I/O 之前在 SQLite 事务中原子预留"，在代理进程内添加只读路由不改变这一语义。

## 数据、接口、权限、成本与兼容影响

### 接口

```
GET /internal/budget
Authorization: Bearer <ZHIJUAN_BUDGET_PROXY_TOKEN>
可选查询参数: ?min_requests=<正整数>
```

成功响应 200：
```json
{
  "run_id": "zhijuan-workflow-20260922",
  "calls": 16,
  "max_requests": 20,
  "reserved_cny": 16,
  "max_reserved_cny": 30,
  "remaining_requests": 4,
  "remaining_cny": 14,
  "reserve_per_request_cny": 1,
  "pending_count": 0,
  "sufficient": true,
  "reason_code": "BUDGET_OK",
  "shortfall": {"requests": 0, "cny": 0},
  "estimate_note": "最低估计不是严格最坏上界",
  "checked_at": "2026-09-23T12:00:00+00:00"
}
```

不足时（带 `min_requests`）：
```json
{
  "run_id": "zhijuan-workflow-20260922",
  "calls": 19,
  "max_requests": 20,
  "reserved_cny": 19,
  "max_reserved_cny": 30,
  "remaining_requests": 1,
  "remaining_cny": 11,
  "reserve_per_request_cny": 1,
  "pending_count": 0,
  "sufficient": false,
  "reason_code": "BUDGET_INSUFFICIENT",
  "shortfall": {"requests": 1, "cny": 1},
  "estimate_note": "最低估计不是严格最坏上界",
  "checked_at": "2026-09-23T12:00:00+00:00"
}
```

未配置令牌时 503：
```json
{"error": "budget_proxy_not_configured", "reason": "预算代理未启用：ZHIJUAN_BUDGET_PROXY_TOKEN 未配置"}
```

鉴权失败 401：`{"error":"unauthorized"}`

### 权限

端点受 `ZHIJUAN_BUDGET_PROXY_TOKEN` Bearer 鉴权保护。该令牌仅由代理启动时的环境变量提供，不写入日志或响应。未配置令牌时代理仍可启动，但该端点固定返回 503。

### 成本与兼容

- 只读操作不产生预留、不调用上游 DeepSeek API、不改账本。
- 不修改 `MAX_REQUESTS`/`MAX_RESERVED_CNY`/`RESERVE_CNY`/`MAX_BODY_BYTES`/`MAX_OUTPUT_TOKENS`/`RUN_NAME` 常量。
- 不改变"每次上游 I/O 前 SQLite 事务内原子预留"的语义。
- 新增环境变量 `ZHIJUAN_BUDGET_LEDGER_PATH`：若设置，覆盖默认账本路径。优先级：CLI `--ledger` > env `ZHIJUAN_BUDGET_LEDGER_PATH` > 内建默认值。
- 现有 `models()` 和 `process()` 方法及其鉴权逻辑不变。

### 未决计数

`pending_count` = 状态为 `RESERVED` 或 `UNKNOWN` 的行数（按现有 `reservations` 表的 `status` 字段语义：`RESERVED` = 已预留但未完成；`UNKNOWN` = 上游结果未知但已收费）。

## 实施/迁移/回滚

### 实施步骤

1. 修改 `tools/live_budget_proxy.py`：
   - 构造函数允许 `internal_token` 为空（空串时不抛出 `ValueError`），各方法自行处理。
   - 新增 `budget_status(authorization, query_params)` 方法：鉴权 → 读 `budget` 表统计 → 读 `reservations` 表 pending 计数 → 按 `min_requests` 判断充足性 → 返回 JSON。
   - HTTP handler `do_GET` 增加 `/internal/budget` 路径路由（含查询参数解析）。
   - `main()` 中 `--ledger` 改为可选，默认值优先使用 `ZHIJUAN_BUDGET_LEDGER_PATH` 环境变量，其次内建默认路径。

2. 扩展 `tests/test_live_budget_proxy.py`：覆盖鉴权、边界、旧账延续、幂等、秘密隔离、非法输入。

3. 新增 `docs/decisions/DEV-008-budget-internal-endpoint.md`（本文）。

### 账本路径迁移（预留给后续执行，本任务不执行）

如需将账本从 `/tmp` 迁至持久受限目录：
1. 停止代理进程。
2. 备份目标账本：`cp <旧路径> <备份路径>`。
3. 校验行数和 `RUN_NAME`：`sqlite3 <旧路径> "SELECT COUNT(*), name FROM budget"` 与目标一致。
4. 原样复制：`cp -p <旧路径> <新路径>`，保留文件权限。
5. 保留原文件不变，不凭复制操作重置 16 次预留记录。
6. 更新代理启动参数或设置 `ZHIJUAN_BUDGET_LEDGER_PATH`。
7. 更新相关挂载配置与文档。

### 回滚

- 代码：恢复 `tools/live_budget_proxy.py` 和 `tests/test_live_budget_proxy.py` 到修改前版本。
- 决策文档：保留本文，追加回滚记录（不删除）。

## 必须重跑的测试

`tests/test_live_budget_proxy.py` 新增以下测试类（Mock 上游，全离线，临时 SQLite 账本）：

| 测试 | 验证点 |
|------|--------|
| `test_no_token_returns_503` | 未配置 internal_token 时 `/internal/budget` 返回 503 |
| `test_wrong_token_returns_401` | 错误 Bearer token 返回 401 |
| `test_min_requests_equal_boundary` | `min_requests` 恰好等于余量时 `sufficient=true` |
| `test_min_requests_one_less_boundary` | `min_requests` 比余量大 1 时 `sufficient=false` 且 `BUDGET_INSUFFICIENT` |
| `test_preexisting_ledger_preserved` | 预置 16 calls/16 元账本读出不变 |
| `test_get_idempotent_no_reservation` | GET 不产生新预留行 |
| `test_response_no_secrets` | 响应不含 key/提示词/题目正文 |
| `test_invalid_min_requests_rejected` | 非法 `min_requests` 参数返回 400 |
| `test_no_min_requests_always_sufficient` | 不带 `min_requests` 时 `sufficient` 恒为 true |

## 关联文件及被替代决定

- `tools/live_budget_proxy.py` — 修改
- `tests/test_live_budget_proxy.py` — 扩展
- `docs/decisions/DEV-004-live-budget-proxy-proposal.md` — 前序决定，本决定在其基础上增加只读端点，不替代或修改其已批准内容。
