# 变更影响

任务 M1-05 / FEAT-SPEC；授权：用户报告“无法切换学段与教材，点击没有反应”，修复对应交互。

修改 FoolproofSetupActions、FoolproofSetupModals、FoolproofSetupModel，新增 ScopeSwitchDialog 与 frontend_scope_switch.test.mjs。调用方 FoolproofSetupForm；共用学段/教材 pending 确认流程。确认 UI 从页底迁至原生模态弹窗，增加取消与Escape。无 schema、API、数据迁移、模型调用或新依赖。

仓库已有大量未提交修改，本次保留。现场由本次handoff记录分支、HEAD和快照；未提交或推送。

回归范围 MIN-02 三学段输入的局部前端交互，不宣称完整用例通过。实际命令与浏览器步骤、边界见 report.md。恢复时仅撤销上述本轮编辑，不能整体恢复已有用户修改。
