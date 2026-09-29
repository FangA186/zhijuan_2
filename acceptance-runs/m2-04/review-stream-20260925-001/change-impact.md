# 变更影响

任务M2-04 / FEAT-REPAIR；同时影响FEAT-ADAPTER、FEAT-JOBS与教师进度界面。main，HEAD 1a89b534185055055d23697f1a61b307efa56253，工作区原有大量未提交修改，全部保留。本次文件见changed-files.txt。

直接调用链：provider严格输出代理→Hermes Runs/SSE→adapter→QuestionService审核修订→Worker record_run_event→PostgreSQL JSONB→本机activity GET/SSE→两个进度页面共用控制台。

新增：审核schema、generation_context/question_generation/question_review、run_stream、job_run_events、activity路由、代理流转换、共享UI及针对性测试。保留QuestionService/GenerationFailure公开导入入口、Hermes adapter元信息API。

无DB迁移；新增快照字段只在私有记录/本机路由使用。旧任务没有流数据不补造。生成成本可能从每题2个角色调用增至最多9次；每轮使用相同模型与原预算出口，未知结果不重试，不增加批准预算。solver仍在独立网关运行且不能读取作者答案。审核无法修改检查规则或发布。

MIN-07/MIN-N03/MIN-N04及FULL-07/FULL-17中修订上限、版本复检、预算/未知结果边界由离线回归覆盖；真实应用与教学质量尚未验收。测试环境与命令/结果见report.md。

批准依据：本次用户明确请求接入审核与实际输出流。决策：docs/decisions/DEV-019-review-stream.md。无新框架/依赖、无提交推送、无计费生成。

恢复：保留数据库与账本，只恢复本次列明的文件变更并按原配置重启相关服务；不可覆盖用户已有修改。部署因缺原凭据来源未完成，等待原启动配置路径。
