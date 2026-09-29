# 变更影响

任务M1-04，用户授权“每道题生成不成功的原因需要展示”。保留已有未提交修改；本次未提交或推送。

直接修改ExamPaperWorkbench及exam-paper进度视图、题槽、摘要、活动区、订阅Hook；新增slotDiagnostics、useSlotDiagnostics、jobSnapshotSummary和Node回归测试。复用现有GET validation/questions/current job；没有接口、schema、数据模型、模型/Skill、权限、成本变化。

保持：FAIL不伪装为成功，REVIEW不伪装为失败或PASS；终态重连只GET；用量未知仍未知；诊断绑定任务版本；不展示原始模型私有推理。学生打印投影不增加原因字段。

测试命令与实际结果见report.md、tests.log、build.log、lines.log；实际分支HEAD和文件快照见本轮handoff。失败恢复仅撤销本轮上述前端改动，不整体覆盖用户已有修改。不用本次局部证据替代MIN-05/APP-E2E完整验收。
