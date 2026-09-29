# 知卷

本仓库包含知卷网页应用、服务、开发记录与验收材料。产品与接口以 v1.3 基线为准，当前实现和未完成项以源码及 `progress/` 为准。

## 从这里开始

- 编程助手先读 [AGENTS.md](AGENTS.md)，再读 [当前摘要](progress/current.md) 和本次任务卡。
- 本机查看功能、迭代、文件用途：[项目资料看板](docs/project-overview.md)。
- 本地启动和环境说明：[开发运行指南](docs/local-development.md)。

## 目录

- `apps/web/`：React 教师工作台与本地项目资料页。
- `services/`：FastAPI、任务、蓝图、检查及 Hermes 适配。
- `contracts/`、`database/`、`configs/`：接口、数据与配置基线。
- `skills/`：生产命题角色资源，不是开发 Agent 指令。
- `progress/`：功能、实际任务与跨会话交接账本。
- `acceptance/`、`acceptance-runs/`、`quality/`、`tests/`：验收规程、实际报告与测试。
- `tools/`：本地开发、检查和教材处理工具。

构建、离线检查、实际应用验收和产品签收是不同证据。报告只能证明当次范围；不要用旧交付文档或 Notion 快照代替当前验证。

原 v1.4 ZIP 交付说明、版本记录、验证说明及哈希清单归档在 [docs/archive/v1.4-bundle/](docs/archive/v1.4-bundle/)。这些是历史包记录，不是当前源码的完整性或产品验收结论。
