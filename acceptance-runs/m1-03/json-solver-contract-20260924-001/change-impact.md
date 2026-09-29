# 变更影响

M1-03 / FEAT-ADAPTER，涉及M1-04生成服务与M2-02盲解。用户明确要求解决JSON结构化返回和四步限制；沿用已授权真实生成验证，不新增自动重试。

直接影响：tools/deepseek_json_contract.py、live_budget_proxy.py、live_budget_status.py，两个Compose配置；solver_output共享契约、isolation_gateway、QuestionService；worker失败提示及相应测试。

JSON模式首轮仍出现非法JSON，因此升级为官方Beta strict函数返回封装，函数不执行，只解包result；Hermes仍是唯一Agent框架且隔离不变。输出结构的实际业务约束继续本地验证。费用与调用正常记账，未知结果不重发。

步数上限移除，保留每步500字、合计6000字、字段白名单和私有推理禁止条件；这不是放宽数学规则或审批标准。无业务数据库迁移、公开端口扩张、发布或Git操作。运行部署保留既有账本、容器状态卷及凭据。

基线/实际分支与文件快照见handoff。回归：51项基础相关测试、54项含严格返回测试、200行门禁、真实旧模式失败证据、严格模式探针和整卷回归。完整结果见report.md。不把REVIEW或模型同意当数学PASS。

决策与恢复：DEV-016。需要回滚时仅恢复本次出口/摘要契约与模块挂载并在空闲时更新对应服务，不重置账本或清空试卷数据。

最终补充：strict-json-v3按角色直接schema，移除result包装。仅已完成坏JSON最多一次额外格式请求，每次单独记账并合计实际usage；这不是一般失败题业务重生成。最终430项离线、57项相关回归及verified-full证据见report.md。
