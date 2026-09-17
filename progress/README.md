# 实际工程记录（可持续更新）

features.yaml 是功能账本；work.yaml 是实际任务状态；handoffs/ 是独立会话检查点；current.md 是自动摘要。原 execution/acceptance 的未执行标签是不可冒充运行结果的历史基线，不阻碍在这里记录真实进展。

实现状态：NOT_STARTED / IN_PROGRESS / IMPLEMENTED / DEPRECATED。不能凭目标路径或接口声明标 IMPLEMENTED，必须登记真实存在的 implementation_paths；脚本只校验存在，不判断代码语义或自动批准。

验证由 last_evidence 报告派生：NOT_RUN、OFFLINE_PASS、STALE、FAILED、INCOMPLETE、INVALID。相关代码、依赖或登记范围变动会变 STALE；不必手动把多个文档的“通过”改一遍。报告不签名，不能防止有权修改脚本/报告的人一起造假，必须结合 CI、审查与权限。

未来产品的 LIVE/G-MIN/G-FULL 证据仍使用 acceptance-runs/ 的实际验收记录；本工具只识别 offline-quality-v1，不能把手写产品报告自动解释为发布授权。

真实 tasks 字典可以新增 M0-01 等已知任务的状态。DONE 必填 completed_by、completed_at、evidence_refs；这些字段只是结构检查，不是审核者自动签名。新增产品需求时，应先有批准变更，在 progress/extra-tasks.yaml 添加完整新任务卡，再在账本关联，不能暗改原 32 项固定基线测试。
