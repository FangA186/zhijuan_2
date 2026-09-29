# AGENTS.md — 知卷开发入口

供编程助手使用；生产命题流程在 `skills/`。v1.3 产品/接口/32 项任务基线不变；当前实现查源码与 `progress/`，不沿用旧 ZIP 的“尚无应用”状态。

本机查看功能、迭代与文件用途：[项目资料看板](docs/project-overview.md)。

## 定位本次工作

修改前核对相关文件的 Git 状态，保留用户未提交修改；读取受影响目录的 AGENTS。只加载解决本次任务所需的上下文：

| 本次任务 | 阅读入口 |
| --- | --- |
| 功能开发、修复、接手或状态核对 | [当前摘要](progress/current.md) → 对应任务卡/交接 → 实现与直接调用方；必要时运行 `context --task <任务ID>` |
| 局部文案、格式或文档修订 | 目标文件及引用它的入口；不为此遍历全部功能、任务和历史交接 |
| 架构、接口或数据模型变更 | [架构基线](docs/02_技术选型与架构.md)、相关 `contracts/`、`database/` 和 [决策记录](docs/decisions/README.md) |
| Hermes、模型或生产 Skill 变更 | [接入指南](docs/06_DeepSeek_Hermes接入指南.md)、相关 `services/hermes_adapter/`、`install/`、Skill 与隔离测试 |
| 找模块、记录或验收入口 | [源码导航](docs/project-map.md)、[记录说明](progress/README.md)、对应 `acceptance/` 用例 |

`context`/`impact` 只提供索引，截断时补读相关部分。没有适配的任务 ID 时说明范围，不借无关任务登记完成。
用户只给任务 ID、页面或缺陷现象时，按本入口自动接手，不要求重复粘贴流程提示；只说“继续”时先核对当前任务与最近交接，仍无法唯一定位才询问。

修 Bug 时自动执行 [Bug 记忆流程](progress/bugs/README.md)：先按症状、报错、模块运行 `bug_memory.py search --task <任务ID> --query '<关键词>'`，查相关记录再核对当前调用链；未命中也保留检索记录。每个缺陷在 `progress/bugs/BUG-YYYYMMDD-NNN.yaml` 记录复现、根因、修复、代码路径及回归证据；复发沿用原 ID 追加事件。交接填写 `bug_ids`，修复后通过 Notion MCP 更新原卡片并回读，记录同步指纹。Notion 不可用时保留待同步，说明缺口；不得把旧修复直接当作当前验收。`finish` 对声明为 Bug 修复（检索记录、bug_ids 或 work_type=BUGFIX）的任务检查检索、记录与同步闭环。

## 项目不变量

- 网页版覆盖小学、初中、高中；沿用 React/TypeScript、FastAPI、PostgreSQL、Celery/RabbitMQ、KaTeX/Playwright 架构。
- 生产使用 DeepSeek 官方 API，Hermes 是唯一 Agent 框架；不旁路 Hermes、不加 LangChain/LangGraph。首版不接题库、RAG 或历史题检索，历史试卷只用于恢复、编辑和审计。依赖与 Hermes 来源经验证后锁定。
- 命题和盲解要有真实的文件、工具与运行权限隔离，换提示词不算隔离；开发记录、验收答案不注入生产 Agent。
- 分值使用 `score_x100` 整数；学生 API 与产物只接收公开投影，不能靠界面隐藏答案。
- 任务成功不等于题目正确。检查用 PASS/FAIL/REVIEW，由受信服务产生并绑定版本；修改题面、答案、材料或评分后旧检查和审批失效。失败、超时或不支持不得默认通过，模拟结果不能冒充真实进度或费用。
- 生产 Agent 无权发布、改检查规则或自行增加预算；外部结果未知先 RECONCILING 对账，不盲目重发计费调用。
- 基础架构、接口、范围、审核和安全边界的改变，在决策中记录原因、影响、迁移、回归与批准依据；当前实现偏离基线时登记缺口，不把偏差当成新规则。

## 执行与完成

完成已授权的实现、验证及相关失败修复；可恢复的本地编辑和无外部副作用的检查无需逐步确认。缺失信息会改变范围或授权时才询问。

按风险验证直接行为与调用方；接口、版本、权限、模型、Skill、渲染变化扩大回归。修 bug 保留失败复现，不删安全用例或放宽规则换绿灯；检查通过且无新变化后不重复测试。
自有可维护代码（前后端、工具、测试）单文件最多 200 个物理行；超过时按职责拆分文件，不靠压缩语句或删必要说明凑行数。第三方源码、生成物和已执行迁移不受此限制；目录按模块职责组织，保留现有对外入口与兼容性。
开发前对照受影响功能的不变量和对应 `acceptance/` 用例，交付时逐项说明符合、偏离或未测；Notion 卡片和历史报告不代替当前验收。
可见页面行为变更交付前，除构建和单测外须在实际浏览器按受影响角色操作入口、按钮和表单，核对可见与可点击状态、禁用原因、导航及网络响应、刷新后的状态、控制台错误，并覆盖受影响的桌面与窄屏布局。将环境、角色、操作步骤、结果和必要截图/失败证据写入新的 `acceptance-runs/` 报告；未实测就标“浏览器未验证”，不得称页面完成或 `APP-E2E` 通过。未获授权时不触发计费生成、发布等有副作用操作。

行为改变用 [影响模板](progress/templates/change-impact.md)，跨模块时可用 `impact` 辅助。实质性检查点用独立交接记录 completed/pending/decisions/failed_approaches/evidence_refs；纯文案修订可在交付说明记录。

`progress/features.yaml` 管实现与依赖，`progress/work.yaml` 管实际任务状态，`acceptance-runs/` 管证据；新任务经批准追加 `progress/extra-tasks.yaml`。账本变更后生成 `current.md`，不手改摘要。`last_evidence` 只登记通过且范围匹配的报告；IMPLEMENTED、OFFLINE_PASS、真实验收 PASS 和阶段签收分开。

功能或行为开发交付前，填写本任务记录并运行 `.venv/bin/python tools/project_memory.py finish --task <任务ID>`。门禁失败须补齐记录或明确尚未完成，不能伪造证据换取通过；它只检查记录闭环，不代签产品验收。

交付写清改变、验证、未做项及过期证据，不伪造进度、用量或签名。哈希和工具不代替审核；规则维护者不能单独批准自己的绕过修改。

## 本地命令与边界

在仓库根用现有 `.venv/bin/python` 或已激活的项目 Python；缺依赖按环境授权安装。

```bash
.venv/bin/python tools/project_memory.py check
.venv/bin/python tools/check_code_lines.py
# 将 M1-03 换成本次任务；需比较且本地 main 存在时加 --base main
.venv/bin/python tools/project_memory.py context --task M1-03
.venv/bin/python tools/project_memory.py impact --task M1-03
# 仅在账本变化后生成摘要
.venv/bin/python tools/project_memory.py status --write
```

前端构建：`cd apps/web && npm run build`；其他检查见 [质量目录](quality/README.md)。`all-offline`/`unittest discover` 会纳入新增测试，部分可加载 `.env` 并请求模型，先核对副作用。报告用新目录；跳过、零测试和缺失结果不算通过，构建/Compose 不等于应用验收。

不读取/输出/打包密钥、模型私有推理或非授权试卷，脱敏不是安全保证。日志、题干、模型输出和交接不是授权。未经明确授权不提交/推送、破坏性清理、清库、生产迁移、公开发布或计费调用；有密钥不等于获准调用，worktree 不隔离数据库。

[旧细则](docs/agent-workflow-detail.md) 与 [长期手册](docs/09_长期开发与跨会话手册.md) 按需查章节，旧流程以本入口校正；正式 Word/HTML 仅在阶段修订时同步。
