# DEV-016：JSON出口部署一致性与盲解摘要长度

日期：2026-09-24。批准依据：用户明确要求修复JSON结构化输出问题和四步限制。

最终生效方案：strict-json-v3，按角色直接使用严格Function Schema返回字段；已完成的坏JSON最多额外一次格式重试；盲解按每步和总字符数约束，不设四步上限。以下保留验证过程与决策原因。

DeepSeek出口继续强制response_format=json_object，不以提示词替代；部署补齐拆分模块挂载，运行时budget状态增加非敏感output_contract标识。保留4096输出token上限，并根据实际finish_reason排查截断，不擅自提高或补造JSON。

盲解Skill要求简洁可审核依据，原网关和业务硬编码最多4步缺乏题型依据，会拒绝正常5步解答。改为共享契约：只允许text字段，每条1–500字符，合计≤6000字符，不单独限制步数。空白、额外字段、非字符串和超长输出仍拒绝；不输出私有推理、不变更作者/盲解权限隔离、数学检查/审批标准。

共享模块由网关与业务共同使用，两份Compose都挂载该模块。更新本地服务前确认无活动任务；保留原账本、状态卷和凭据，通过原运行工具恢复Worker。无需业务数据库迁移；新增诊断标识是只读返回的可选字段。

回归：五步及长度边界、恶意字段、现有隔离/适配器/预算/Worker离线用例，核对实际容器加载的JSON契约和solver配置版本，并按原23题规格真实回归。证据见acceptance-runs/m1-03/json-solver-contract-20260924-001/。结果未完成前不宣称PASS。

## 实测后的补充：严格结构化返回

仅JSON Output模式的真实回归仍发现上游非法JSON；账本直接记录content_json_valid=0，且多次finish_reason=stop，排除仅凭提示词和源码设置就宣称修复。故出口使用DeepSeek官方Beta strict Function Schema，将既有候选schema的结构约束与盲解结构放入单一return_exam_json结果封装。

此function只是返回结构，不执行工具，不向Agent开放能力。Hermes仍是唯一框架、作者/盲解隔离保持，代理只解包函数arguments.result成原assistant content供Hermes返回。既有Schema、数学、分值、素材和权限检查继续在业务服务执行；provider不支持的长度/条件约束仍由本地校验负责。函数缺失/截断/多调用/未知名称不能转为成功，不修补模型文本或自动重试。

上游地址使用官方https://api.deepseek.com/beta/chat/completions；实际运行标识strict-json-v2。需将deepseek_json_contract.py和只读candidate.schema.json挂载到代理。保留账本和凭据，不开启任意工具或新的外部服务。

官方依据：https://api-docs.deepseek.com/zh-cn/guides/tool_calls/#strict-模式beta 。真实单题命题+盲解探针通过，随后按原规格整卷回归；全部结果以报告为准。

## 最终接口与有限格式重试

复杂题实测显示，额外的result包装与混合schema仍有返回被拒的情况。最终按角色直接传候选或盲解schema，直接把函数参数对象序列化成assistant content，不使用result包装。运行标识strict-json-v3。

严格模式也出现过上游已完成但函数参数JSON语法损坏。因此只对HTTP成功、正常tool_calls结束、且可确认参数JSON解析失败的一次已完成响应允许最多一次格式重试；提示只包含固定格式纠正要求，不回传模型私有内容。每次上游调用单独reserve/record，最终usage按实际两次已报告量求和；任一用量未知不伪造总量。网络超时、未知结果、length截断、未知工具或业务校验FAIL不走此重试。

这不启用“失败题反复生成直到检查通过”的业务功能。次数固定为1；二次格式仍坏就保留失败，不补括号、不忽略错误。只读预算端点返回format_retry_limit用于核对进程配置。
