# 变更影响

M2-03检查器为主，涉及M1-05规格及M2-02盲解隔离。用户批准修复评分档位误相加和答案说明冲突。

直接影响候选/规格schema、SpecService/spec_validation、QuestionService骨架与question-author Skill、检查器scoring模块；前端配置字段、API canonical白名单、共享答案/评分渲染与诊断；盲解拒绝字段名单；对应测试。调用方包括FoolproofSetup/ExamSetup、成卷、编辑器和导出预览。

JSON新增可选字段，旧规格/答案默认旧累加语义；新版规格明确选择题互斥。无SQL迁移。模型权限/框架/provider未变；新增私有字段不进public投影。checker_version=6，评分/答案变化绑定不同content_hash，不重用旧审批。

不把0分开放到累加rubric；仅互斥档位允许0且错选/空答固定0。教师确定少选分，模型不能增减或换模式。显式声明冲突FAIL，无法完整理解的自然语言不冒充数学证明。

实际分支/HEAD/已有修改见handoff。验证命令与结果见report.md。回退须保留新格式记录，用兼容读取器解释exclusive，不能直接让旧检查器相加；历史两题只做独立v2草稿，无旧记录覆盖或审批。未执行的PDF/Word输出、旧编辑入口及完整权限验收如实标注。
