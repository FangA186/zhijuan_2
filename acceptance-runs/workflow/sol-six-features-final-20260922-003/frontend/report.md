# 前端本地验证

- `node --test tests/frontend_stage_year.test.mjs`：退出码 0，2/2 通过。见 `stage-year-test.log` 和 `stage-year-test.exit`。
- `cd apps/web && npm run build`：退出码 0，TypeScript 与 Vite 构建通过。见 `web-build.log` 和 `web-build.exit`。

本轮只运行无模型本地命令；未修改源码或进度账本。结果仅证明对应单测及构建，浏览器与后端行为由主代理另行验收。
