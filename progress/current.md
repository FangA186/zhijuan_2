# 当前工程摘要（自动生成）

> 由 progress/features.yaml、progress/work.yaml 及登记证据生成，不手改本文件。
> 当前 Git 现场请运行 context；本摘要不是新的事实来源或阶段签收。

记录摘要指纹：`165b0bcef9adff37fd1692780ffe1ed43de98cfb60655d6f789b063d8a64eb45`
当前阶段提示：**M1**；建议下一任务：**M0-05**。

| 功能 | 类别 | 实现 | 登记范围的验证 |
| --- | --- | --- | --- |
| FEAT-SPEC · 三学段配置与规格 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-AUTH · 身份、租户与权限 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-PERSIST · 持久化与版本存储 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-ADAPTER · Hermes 与 DeepSeek 真实接入 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-JOBS · 异步任务、取消与恢复 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-PLAN · 蓝图与多题原创生成 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-BLIND · 独立盲解与输入隔离 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-CHECK · 检查器与可信证据 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-REPAIR · 有限修订 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-REGEN · 编辑与单题重新生成 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-REVIEW · 保存、复核与历史 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-EXPORT · 学生卷 PDF 与 JSON | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-PUBLISH · 审核发布与撤回 | PRODUCT | IN_PROGRESS | NOT_RUN |
| FEAT-DOCX · 可编辑 Word 导出 | PRODUCT | NOT_STARTED | NOT_RUN |
| FEAT-DEV-STRUCTURE · 可维护代码结构与 200 行离线门禁 | DEVTOOL | IMPLEMENTED | STALE |
| FEAT-DEV-MEMORY · 跨会话记录、项目看板与离线质量工具 | DEVTOOL | IMPLEMENTED | STALE |

## 实际任务覆盖层

- DEV-01: DONE；证据条数 5
- DEV-02: DONE；证据条数 3
- DEV-03: DONE；证据条数 3
- DEV-04: DONE；证据条数 3
- M0-04: IN_PROGRESS；证据条数 7
- M0-05: IN_PROGRESS；证据条数 5
- M1-01: IN_PROGRESS；证据条数 2
- M1-02: IN_PROGRESS；证据条数 9
- M1-03: IN_PROGRESS；证据条数 13
- M1-04: IN_PROGRESS；证据条数 19
- M1-05: IN_PROGRESS；证据条数 15
- M1-06: IN_PROGRESS；证据条数 6
- M1-07: IN_PROGRESS；证据条数 10
- M1-08: IN_PROGRESS；证据条数 7
- M2-01: IN_PROGRESS；证据条数 11
- M2-02: IN_PROGRESS；证据条数 7
- M2-03: IN_PROGRESS；证据条数 10
- M2-04: IN_PROGRESS；证据条数 4
- M2-05: IN_PROGRESS；证据条数 6
- M2-06: IN_PROGRESS；证据条数 2
- M2-07: IN_PROGRESS；证据条数 2
- M3-03: IN_PROGRESS；证据条数 6

## 接手入口

先运行 `python tools/project_memory.py context --task M0-01`（替换为实际任务编号）。
跨会话交接见 `progress/handoffs/`；阶段验收仍查看 `acceptance-runs/` 的真实结果。
OFFLINE_PASS 不表示真实 Hermes、DeepSeek、数据库、渲染或教学质量已通过。
