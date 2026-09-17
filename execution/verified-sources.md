
### [S28] Hermes · Programmatic Integration

核查日期 2026-09-16。确认 HTTP/SSE Runs、原生终态与直接 Python 接入的文档入口；实际以固定提交联调为准，不从终端 HTTP 200 推断任务完成。

来源：https://hermes-agent.nousresearch.com/docs/developer-guide/programmatic-integration

### [S29] Hermes · API Server（本轮复核）

核查日期 2026-09-16。确认服务端 API 启用、认证、模型路由、Runs 状态/事件/stop 与能力发现。健康检查与真实模型就绪分开；原生工具权限和历史需业务限制。

来源：https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server

### [S30] Hermes · Installation

核查日期 2026-09-16。确认开发安装入口；本文没有执行安装，不将在线安装器当作冻结生产版本。

来源：https://hermes-agent.nousresearch.com/docs/getting-started/installation

### [S31] Hermes · Contributing / Development Setup

核查日期 2026-09-16。确认开发者可源码安装，并建议运行环境与工作源码分离；本项目仍须生成实际安装/锁定记录。

来源：https://hermes-agent.nousresearch.com/docs/developer-guide/contributing

### [S32] Hermes · Skills System（本轮复核）

核查日期 2026-09-16。确认技能目录、发现/加载和项目技能信任等边界；技能存在不等于本次实际执行，文字规则不替代访问权限。

来源：https://hermes-agent.nousresearch.com/docs/user-guide/features/skills

### [S33] Celery · Tasks

核查日期 2026-09-16。确认任务重试、幂等与消息确认需要应用选择；不能把 acks_late 等单一配置解释成端到端恰好一次。

来源：https://docs.celeryq.dev/en/stable/userguide/tasks.html

### [S34] Playwright Python · Page PDF

核查日期 2026-09-16。确认 page.pdf 使用打印 CSS。字体、图片、公式完成与审批版本由应用自行检查；不是自动正确排版承诺。

来源：https://playwright.dev/python/docs/api/class-page
