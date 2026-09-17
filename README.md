# 知卷 · 长期开发与跨会话交接包 v1.4

**网页版、三个学段、DeepSeek + Hermes、第一版无题库。** 在 v1.3.1 底包上增加真实可执行的开发记录工具；不是新增出卷应用，不含 Hermes 源码/安装或真实模型调用。

## 直接从这里开始

阅读 [START_HERE.md](START_HERE.md)，让编程助手先读根目录 [AGENTS.md](AGENTS.md)，再按任务生成上下文，不需要每次重新灌入 70 页方案。

```bash
# 依赖尚未具备时，先按环境授权安装 requirements-test.txt
python tools/project_memory.py context --task M0-01
python tools/project_memory.py check
```

`M0-01` 是初始建议任务，不表示已经开工；继续已有任务时替换 ID。没有 Git 的解压目录会报告 NO_GIT，不伪造提交历史。

## 本次新交付

| 文件/目录 | 实际用途与范围 |
| --- | --- |
| AGENTS.md | 精简的稳定入口；原有细则移到 docs/agent-workflow-detail.md 按需读 |
| progress/features.yaml | 15 项功能登记：14 项待开发产品功能、1 项已实现开发工具；实现和验证分开 |
| progress/work.yaml | 实际任务覆盖层；不改原始 32 项计划和 47 类验收模板 |
| progress/current.md | 脚本生成的摘要，只引用账本与证据，不重复手写事实 |
| progress/handoffs/ | 独立任务/会话交接；记录当前版本、文件指纹、待办、失败方案和下一步 |
| tools/project_memory.py | 记录检查、上下文整理、路径影响分析、交接创建和摘要刷新 |
| tools/run_quality_checks.py | 运行实际离线检查并保存报告；不默默把应用测试占位符当通过 |
| quality/ | 可执行离线测试目录 + 10 项待落实到应用的关键回归行为映射 |
| .github/workflows/ci.yml | 仓库根使用的离线 CI 配置；尚未在远程执行或开启分支保护 |
| docs/09_长期开发与跨会话手册.md | 长期开发、多人/多会话、证据失效、CI 接入和每日操作流程 |
| deliverables/long_term_development_v1_4.html | 上述新增手册的独立阅读版 |

## 保留的原交付

原 `docs/01—08`、`execution/`、`acceptance/`、`contracts/`、`configs/`、`skills/`、SQL 草案和参考代码继续保留。`deliverables/zhijuan_product_development_v1_3.docx`、HTML 和 Markdown **按字节保留原 v1.3**，没有宣称更新到 1.4 或改变技术与阶段方案。

包版本 1.4 指新增开发机制；产品/接口/实施正文仍为 1.3。新手册描述怎样维护正在开发的工程，不把原静态方案改造成虚假的运行状态。

## 有哪些东西尚未完成

没有可启动前后端、真实 Adapter、Hermes 源码、数据库迁移实机执行、真实模型或试卷导出流水线。14 项产品功能仍 NOT_STARTED。现有参考规则测试 + 新工具测试不证明应用、课程质量或完整验收通过。APP-* / LIVE-QUALITY 测试组仍 PLANNED；10 项产品回归行为映射仍 NOT_IMPLEMENTED，后续写真实测试后才能启用。

不需要为该开发机制增加另一个 Agent、向量数据库或模型记忆服务。关键限制与验证结果见 [VALIDATION.md](VALIDATION.md)。ZIP 字节一致性以 MANIFEST.sha256 为准；它不是签名，也不证明安全或业务正确。
# zhijuan_2
