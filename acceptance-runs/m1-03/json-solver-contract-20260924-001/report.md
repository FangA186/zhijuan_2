# JSON结构化输出与盲解四步限制修复

2026-09-24；主任务M1-03，涉及M1-04、M2-02。执行者Codex。用户明确要求修复两项问题，已有真实生成费用授权沿用。

## 最终结果

最终版本为 strict-json-v3 + 最多1次确定性格式重试。verified-full整卷23/23题处理完成：19题REVIEW_REQUIRED、4题FAIL。

- 42个逻辑命题/盲解结果，实际44次上游调用；2次上游正常结束但参数JSON损坏，各在一次格式重试后恢复。中间失败保留账本，usage按已报告实际量求和。
- 最终没有题目因JSON语法错误、四步上限失败。不是声称上游从未出错，更不是题目数学正确性全部通过。
- 第9题5步正常进入REVIEW；还有6、7、20步输出通过摘要契约，完整计数见verified-full/solver-step-counts.json。
- 剩余第11、12、20题为ANSWER_AND_RUBRIC失败；第13题选项文本不满足非空要求。保留失败，不降低检查换取全绿。

## 根因与实际修复

1. 原JSON Output源码配置不能证明进程已加载，且容器遗漏拆分后的ledger/status依赖挂载。补齐挂载，保留旧账本、状态卷与现有凭据，更新空闲服务；提供可核对的output_contract版本标识。
2. 重新加载json_object后真实整卷仍有上游非法JSON，账本直接验证，不归咎于Hermes。改用官方Beta strict Function Schema返回约束，按命题/盲解分别传结构。
3. 严格返回函数不执行任何工具，只将参数对象序列化为Hermes原本接收的assistant content；不旁路Hermes、不改变隔离。候选schema、分值、数学与审批检查保留。不得用修补括号接受错误输出。
4. strict本身也出现少量已完成坏参数，故仅对HTTP成功、正常tool_calls结束且参数JSON解析失败，最多额外一次格式重试。每次分别reserve和record；超时、结果未知、length截断、未知工具与业务FAIL不自动重试。测试覆盖停止边界及两次用量求和。
5. 盲解网关提示和业务检查共用solver_output.py；删除最多4步，保留每步≤500字符、合计≤6000字符、text字段白名单与不输出私有推理要求。原第9题的5步不再仅因数量被拒。

## 真实验证过程（保留失败，不覆盖）

- 本目录根：重新加载JSON Object后的首轮，仍有语法失败，不能称该方案已解决。
- strict-full：严格模式带额外包装，复杂题出现参数JSON损坏，未作为最终方案。
- final-full：去除包装、按角色直接返回；42/43格式正常，1次坏参数，故继续补有限格式保护。
- verified-full：最终整卷结果，44次调用含2次已恢复格式错误，最终0题JSON语法失败，0题四步上限失败。
- canary-result.json、canary-complex*.json：真实阶段探针与被拒结果。探针不替换业务试卷，不将错误试探冒充通过。

## 检查与证据

| 检查 | 结果 | 文件 |
|---|---|---|
| 最终全量离线 | 430项通过，零skip | offline-final.json / offline-final.log |
| 最终相关隔离、适配、JSON、重试、步骤测试 | 57项通过 | tests-final.log |
| 200行门禁 | 通过 | lines.log |
| 前端构建 | 通过 | build.log |
| 实际运行配置 | strict-json-v3，format_retry_limit=1；solver配置v2 | verified-full/runtime-contract.json |
| 最终上游逐次格式/结束状态 | 42次合法、2次格式错误均恢复，无未决 | verified-full/transport-results.json |
| 23题结果/每题失败原因 | 19 REVIEW、4 FAIL | verified-full/per-question.json / summary.json |
| 实际Chrome命题教师桌面、390×844窄屏、刷新 | 正常显示本轮进度与原因，第9题待复核，视口已恢复 | verified-full/desktop.png / mobile.png / page.txt |
| 最终回归期间浏览器error | 0 | verified-full/console-errors.json |

## 保持与未做

JSON语法可靠性、业务Schema合规和数学正确性分别判断。数学正确性仍需复核，同模型盲解不能代替证明；4道业务失败未自动重生成。学生投影不增加私有诊断或答案，未修改发布、版本、鉴权和隔离边界。没有修改第三方Hermes源码或新增依赖。

本次不实现一般性的失败题多次生成；仅实现最多一次已完成坏JSON的协议级恢复。不宣称未来所有供应商调用永不失败：连续两次坏格式仍明确失败，不无穷重试。未发布、未导出PDF/Word、未提交推送、未做业务数据库迁移。当前工作台保留最后一轮真实测试结果。

决策、迁移和回归范围：docs/decisions/DEV-016-json-solver-output.md。官方依据：https://api-docs.deepseek.com/zh-cn/guides/json_mode/ 与 https://api-docs.deepseek.com/zh-cn/guides/tool_calls/ 。
