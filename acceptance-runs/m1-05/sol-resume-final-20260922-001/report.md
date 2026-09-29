# M1-05 前端 / SPEC 收尾复核

- 年级：FoolproofSetup 与 ExamSetup 均用原生 select；小学1-6、初高中1-3。无 njName 的高中教材沿用同学段已选年级，切学段显示该学段一年级并使范围确认失效。
- 学科：选教材按学科名同步 canonical 小写 subject_code；未选教材不注入默认 material_id。
- 任务：唯一正式 POST 启动入口是 FoolproofSetup 教师确认蓝图之后；App 刷新 GET 当前任务。POST 结果未知时 GET 对账，GET 也失败则阻断重发并提示刷新。
- 状态：PARTIAL_FAILED、FAILED、RECONCILING 不进入完成试卷视图；JobProgress 的末尾日志只在 QUEUED/RUNNING 显示流动状态。未知用量保持未知。
- 检查：node tests/frontend_stage_year.test.mjs 2/2通过，npm run build退出0，目标tracked文件 git diff --check退出0。
- 未覆盖：真实浏览器教材列表与年级选择、真实 SSE 断线/重连、POST 网络结果未知的端到端验收；本轮未进行模型调用。
