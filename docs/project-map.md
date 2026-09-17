# 项目地图：先辨别真实代码与待实现目录

| 层 | 当前事实 | 主要入口 | 影响范围 |
| --- | --- | --- | --- |
| 产品与阶段方案 | 已有文档与契约，不是应用 | docs/01—08；execution/task-index.yaml | 需求、接口、阶段验收 |
| 业务后端 | 待开发 | 未来 services/api/ | 身份、规格、版本、审核、发布 |
| 后台任务 | 待开发 | 未来 services/worker/ | 生成、重试、对账、预算、取消 |
| Hermes 接入 | 仅 Protocol 与模板 | reference_code/adapter_contract.py；未来 services/hermes_adapter/ | 模型/工具调用及运行隔离 |
| 检查/导出 | 已有少量参考规则；应用管线待开发 | reference_code/publish_gate.py；未来 validators/renderer | 答案、分值、公开投影、产物 |
| 网页工作台 | 当前包无源码 | 未来 apps/web/ | 配置、计划、进度、编辑、审核 |
| 开发记录工具 | v1.4 已实现，可离线运行 | tools/project_memory.py；tools/run_quality_checks.py | 功能账本、交接、影响提示、证据 |

## 修改前沿依赖追踪

业务任务链：配置 → 计划 → 真实命题 → 盲解/检查 → 修订 → 编辑/复核 → 导出 → 发布。实际功能登记与依赖以 progress/features.yaml 为唯一维护处；本文是阅读地图，不再手写一份状态表。

编辑/版本变动通常影响检查、复核、导出和发布；公开题面变动通常影响盲解及学生产物；Worker 变动可能影响取消、迟到结果、费用和重试；共享 schema/配置/锁文件的改动扩大检查范围。脚本按已登记 watch_paths 与 requires 求闭包，不解析每个动态调用。新增模块时必须登记并审查未知路径。

## 三种边界不要混淆

AGENTS.md 给编程助手开发规则；skills/*/SKILL.md 给生产 Hermes 命题规则；progress/ 和验收控制样例不向生产命题运行开放。开发工具可以读 Git 路径元数据，不因此给 Hermes 任意终端或整个项目目录。

现有的基线测试只检查材料与参考规则；quality/regression-map.yaml 列出的应用行为保护还需要真实应用代码与测试实现。
