# 当前工程摘要（自动生成）

> 由 progress/features.yaml、progress/work.yaml 及登记证据生成，不手改本文件。
> 当前 Git 现场请运行 context；本摘要不是新的事实来源或阶段签收。

记录摘要指纹：`02615b77b9b1231f64666c85010e34a3b033eb6d11e782c26fd96104fce18bf2`
当前阶段提示：**M1**；建议下一任务：**M1-04**。

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

- M0-04: DONE；证据条数 3
- M1-03: DONE；证据条数 1
- M1-07: DONE；证据条数 1

## 接手入口

先运行 `python tools/project_memory.py context --task M0-01`（替换为实际任务编号）。
跨会话交接见 `progress/handoffs/`；阶段验收仍查看 `acceptance-runs/` 的真实结果。
OFFLINE_PASS 不表示真实 Hermes、DeepSeek、数据库、渲染或教学质量已通过。
