# DEV-017：Hermes升级至v0.21.5

2026-09-24，用户明确授权升级并验证。目标为官方稳定标签v2026.9.24，提交f97608f178d1ffeca59860195ab7da295f7c8e5f；不追踪main/latest。

## 变更与边界

- vendor源码切换至锁定标签，更新来源锁定与哈希，从已跟踪源码的独立构建目录生成Python3.12镜像。构建上下文不含业务数据、.env或会话目录。
- 作者/盲解使用新镜像、独立新状态卷；旧镜像和旧卷保留，不迁移/删除。知卷PostgreSQL数据、账本、批准模型和隔离网关不变。
- 新版interrupted状态映射UNKNOWN并进入RECONCILING，不作为普通题目失败继续派发，不自动重发。
- 真实探针发现额外自动标题调用；关闭auxiliary.title_generation.enabled/model_upgrade_enabled。关闭框架api_max_retries和auto_recovery_cycles，避免与受控格式恢复叠加。
- 保留DEV-016严格输出与一次已完成坏格式恢复；上游通用工具参数修复不代替业务schema/数学检查。不开放额外工具。

## 验证

镜像与双服务包版本、依赖检查、原生嵌套JSON修复和interrupted模拟；真实HTTP拒绝作者会话/答案字段且零付费；双服务工具集为空、uid10001；432项离线通过；实际整卷23槽完成，21 REVIEW、2业务FAIL；44阶段均由批准模型完成，45上游调用含一次受控格式恢复，无未知调用。桌面/窄屏/刷新与控制台检查通过。

第一题状态GET短暂超时，轮询同一run恢复且未重复POST；不把健康探测替代真实验证。容器SQLite版本触发Hermes的DELETE journal安全回退提示，不启用受影响WAL；未升级SQLite或操作业务库。

## 回退

保存旧镜像sha256:3c0a3ff6194200c92346a11a633588c997db071a11e27002d0a61b3296cd7654及回退标签zhijuan-hermes:rollback-20260924；旧author-state/solver-state卷不删除。空闲时在原Compose恢复旧image与旧卷引用，恢复source-lock-before.json所指vendor提交；不清空账本或试卷历史。新旧Hermes运行记录各保留在对应卷，旧运行ID不迁入新卷。

证据：acceptance-runs/m1-03/hermes-upgrade-20260924-001/report.md。升级/技术验证不等于教学质量验收；未发布、未提交推送。
