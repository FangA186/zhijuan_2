# 当前工程摘要（自动生成）

> 由 progress/features.yaml、progress/work.yaml 及登记证据生成，不手改本文件。
> 当前 Git 现场请运行 context；本摘要不是新的事实来源或阶段签收。

记录摘要指纹：`7e45a0d282886cfc649410b4bdd305c520e59806f7d0941a9f6a9c3b148073bc`
当前阶段提示：**M0**；建议下一任务：**M0-01**。

| 功能 | 类别 | 实现 | 登记范围的验证 |
| --- | --- | --- | --- |
| FEAT-SPEC · 三学段配置与规格 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-AUTH · 身份、租户与权限 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-PERSIST · 持久化与版本存储 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-ADAPTER · Hermes 与 DeepSeek 真实接入 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-JOBS · 异步任务、取消与恢复 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-PLAN · 蓝图与多题原创生成 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-BLIND · 独立盲解与输入隔离 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-CHECK · 检查器与可信证据 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-REPAIR · 有限修订 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-REGEN · 编辑与单题重新生成 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-REVIEW · 保存、复核与历史 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-EXPORT · 学生卷 PDF 与 JSON | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-PUBLISH · 审核发布与撤回 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-DOCX · 可编辑 Word 导出 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-DEV-MEMORY · 跨会话记录与离线质量工具 | DEVTOOL | IMPLEMENTED | OFFLINE_PASS |

## 实际任务覆盖层

尚未登记产品实施任务完成。原始 32 项任务与 47 类验收仍是未执行基线。

## 接手入口

先运行 `python tools/project_memory.py context --task M0-01`（替换为实际任务编号）。
跨会话交接见 `progress/handoffs/`；阶段验收仍查看 `acceptance-runs/` 的真实结果。
OFFLINE_PASS 不表示真实 Hermes、DeepSeek、数据库、渲染或教学质量已通过。
