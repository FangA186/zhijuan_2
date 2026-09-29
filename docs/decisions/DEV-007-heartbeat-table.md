# DEV-007：本地运行心跳表

状态：ACCEPTED（仅限本地运行元数据，不是租户迁移）
提出人/日期：Codex / 2026-09-23
批准依据：实施计划 §8 / §9.2（2026-09-22-local-generation-implementation-plan.md）内任务 T3，心跳表为本轮就绪检查的受控新增，不影响租户数据。
关联任务/功能：T3（心跳存储与 Worker/调度器接线）、W2-B

## 背景和约束

当前 /readyz 只检查环境变量是否存在，无法区分"配置齐全但进程死亡"与"真正可用"。实现计划 §8 要求新增心跳表，使 API 能判断 Worker、调度器、网关等组件的实时存活状态。

约束：
- 心跳表是本地运行元数据，不是完整租户 RLS 迁移。不在 001_schema_draft.sql 的多租户范围内。
- 数据行按 runtime_id 隔离；API 只接受同部署 ID 的心跳（`ZHIJUAN_RUNTIME_ID`，默认 "zhijuan-local"）。
- 心跳时间由数据库 `now()` 写入，不用应用时钟以避免时钟偏差。
- 实例 ID 进程启动时 uuid4.hex 生成，重启后旧实例心跳自然因 TTL 过期失效。
- 回滚只停写新数据、保留表；不 DROP 任何已有结果数据。

## 可选方案与证据

1. **内存/文件心跳**：进程退出时自动清除，但无法被 API 跨进程可靠读取；不支持多进程/多机场景。
2. **Redis 键过期**：增加额外依赖，违背"不引入 LangChain/LangGraph/额外框架"原则。
3. **PostgreSQL 心跳表**：复用项目已有 PG 依赖；用 `now()` 避免时钟偏差；主键 (runtime_id, component, instance_id) 天然支持同一组件多实例；TTL 过期在应用层由 `fresh_components()` 判断。

选择方案 3。

## 选择及原因

PostgreSQL 心跳表满足所有需求：
- 多组件、多实例共存
- 时间由数据库保证
- 无需额外依赖
- 与现有 outbox/generation_jobs 存储在同一数据库
- metadata JSON 字段可携带模型 ID、网关版本等非秘密指纹

## 数据、接口、权限、成本与兼容影响

- 新增表 `runtime_heartbeats`，不修改现有表。
- 新增模块 `services/api/runtime_heartbeats.py`：`upsert_heartbeat(conn, runtime_id, component, instance_id, metadata)` 和 `fresh_components(conn, runtime_id, ttl_seconds)`。
- Worker 和调度器各自起心跳线程，按 5s/2s 间隔 upsert。
- API 的 readyz 查询该表判断 worker/dispatcher 组件是否新鲜。
- 不影响现有 job/outbox/结果数据。旧代码不读此表，因此回滚时只需停止写入。

## 实施/迁移/回滚

实施：
1. 创建 `database/005_local_runtime_heartbeats.sql`（CREATE TABLE IF NOT EXISTS）。
2. 在测试 schema 验证后再在每日库执行。
3. 应用层代码按 C2 契约读写。

迁移：
- 新表不影响现有数据，无需数据迁移。
- 新代码部署后自动开始写入心跳。

回滚：
1. 停止新代码（心跳写入和读取）。
2. 保留 `runtime_heartbeats` 表及其数据——不 DROP。
3. 旧版 /readyz 回退到仅环境变量检查，不依赖该表。
4. 无数据丢失，无影响 tenant 表。

## 必须重跑的测试

- `tests/test_runtime_heartbeats.py`（离线单测：线程启停、instance_id 变化、fresh_components 过期/跨 runtime_id 拒绝、scheduler 心跳登记）
- 集成测试由主流程在真实 PG 上执行（不在本文件范围内）

## 关联文件及被替代决定

- `database/005_local_runtime_heartbeats.sql`
- `services/api/runtime_heartbeats.py`
- `services/worker/heartbeat.py`
- `services/worker/scheduler.py`
- `tests/test_runtime_heartbeats.py`

不替代任何现有决定。
