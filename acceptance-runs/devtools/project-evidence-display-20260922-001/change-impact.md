# DEV-01：项目看板的阶段验证展示修复

问题：功能卡只读取 features.last_evidence；该字段为完整功能验收门禁，任务及交接内已有的阶段报告被遗漏，因此显示“尚未验证 / 没有登记运行报告”。用户截图已读取新功能说明，问题属于证据展示遗漏。

改变：聚合同任务 work/handoff 中确实存在、位于 acceptance-runs 内的 JSON/YAML/Markdown 记录路径；去重并拒绝越界、缺失文件及仅按路径相关的其他任务证据。卡片显示“已有阶段验证记录”；详情直接显示同任务最新交接的时间、已做、待办，以及阶段资料入口。未读原始日志/模型内容，也未改变产品实现或完整验收状态。

影响文件：tools/project_overview.py、apps/web/src/pages/ProjectOverview.tsx、tests/test_project_overview.py。没有数据迁移、API计费、生产行为或安全授权变更。旧 last_evidence 不借用局部报告冒充完整验收。

验证：新增回归断言阶段记录可见而 implementation=IN_PROGRESS、verification=NOT_RUN 和 last_evidence=null 均保持；看板9项通过。TypeScript/Vite构建退出0。Chrome现有 localhost:3000/project 刷新后 SPEC 显示“已有阶段验证记录”，最近M1-05检查点、已做与待办均可见，并列出7份阶段资料；AUTH保持“尚无验收记录”。三组正式离线证据另见同目录report.json。

未做：此次没有重新运行产品模型/数据库验收，没有将六项产品功能改成已完成，没有开放报告原始正文。回滚可撤销上述三处局部修改，保留所有历史报告与用户其他修改。
