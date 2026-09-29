# Workbench CHECK/JOBS 真实状态收口

仅修改 `apps/web/src/pages/ExamPaperWorkbench.tsx`。

- 四类题型的“换一题”按钮均永久 disabled，显示“版本化换题尚未启用”；移除已不可达的单题重生成 handler 和同步状态。未实现 REGEN。
- 试卷视图在屏幕上按每题 local_id 读取并展示服务端检查状态：FAIL、REVIEW、未知；收到可信服务端 PASS 记录时仍提示教师复核。提示和每题状态不打印。
- 删除“严格对齐教育部课程标准规范 · 原创版权保护”的无验收依据声明，替换为教师使用前复核提示。
- `cd apps/web && npm run build` 退出码 0，TypeScript 与 Vite 构建通过；见 `web-build.log` 与 `web-build.exit`。
- 本轮未触发模型调用；未做浏览器交互验收。页面展示仍以服务端检查接口实际返回为准，接口失败时按未知显示。
