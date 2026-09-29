# 本次影响

M2-04 / FEAT-REPAIR，兼及FEAT-ADAPTER与FEAT-JOBS。main上的已有未提交修改保留。

用户授权：要求修复没有实际输出的复发、参考对话式UI，并直接实际调用验证。本次将已有Docker配置在子进程内复用（不进入模型上下文、文件或日志），重载已部署本机生成通路；最多三个独立单题样本，未动当前23题。

变化：activityPresentation流式可读正文与终态去重；本机activity路由旧结果带来源回显；stream provider完成与JSON校验职责分开；strict reviewer enum补type；隔离solver题型说明；未知provider结果保持对账；错误诊断只记录类型和协议枚举。新增live_review_probe只在显式start命令创建独立题槽/实际排队，GET/serve不触发模型。models元信息沿原入口移至现有BudgetStatusMixin以遵守200行上限。

公共学生进度仍无私有activity；本机教师路由仍限环回访问；没有添加隐式模型重试、放宽候选校验或增加批准预算。前两条UNKNOWN费用保留；未知结果不得重发同一任务。

验证证据和失败尝试见report.md。回退只恢复本次文件/原profile并在任务终态后重载服务，保留实际试卷、测试任务、审计与账本；不清库。
