# 开始使用：已有项目与新项目两条路径

## A. 本包作为知卷新工程起点

解压后进入包含 AGENTS.md 的目录。它尚不是应用仓库，先从 M0-01 做范围与准备，不执行不存在的 npm/应用启动命令。首次可按环境授权创建虚拟环境并安装 `requirements-test.txt`；本次精确离线版本另有 `requirements-ci.lock`。

```bash
python tools/project_memory.py context --task M0-01
python tools/project_memory.py check
python tools/project_memory.py status
```

这三个命令只查看/计算记录，不改源码，不运行模型。context 只读取当前任务卡和账本、交接摘要，不自动展开完整方案。第一次没有 Git 正常，不能据此声称可核对历史。建立 Git、安装 Hermes、配置密钥分别按 M0 实施任务授权执行。

## B. 已有正在开发的项目

不要把这个 ZIP 覆盖到原项目并把功能重新标为未开始。先做可恢复备份/工作分支，保留真实源码、AGENTS、CI 与未提交修改。技术负责人逐模块盘点已有代码与测试，合并新工具及模板，并将 progress/features.yaml 的 14 项初始产品状态替换为实际状态。项目命名不同就映射任务/功能 ID，不假设这些路径已经存在。

保留当前 CI 测试，不要用本包的“离线材料 CI”替换已有应用 CI。将本工作流作为新增检查，并审查所运行的代码/依赖。若基线放进 `baseline/`，修改工具的读取位置/相对引用；当前工具要求记录根就是 Git 根，不能悄悄借用父仓库。原始验收模板只读不等于真实账本只读。

## 新会话的固定动作

```bash
# 在本地已有 main 分支时比较已提交差异；不存在会失败，不自动拉取
python tools/project_memory.py context --task M2-05 --base main
python tools/project_memory.py impact --task M2-05 --base main
```

阅读摘要后，补读本任务相关源码、契约和测试。`--max-chars 12000` 是字符预算，不是 token 数；截断会明确标注。只想基于工作区变化时省略 --base，但不要把这理解为已比较整条分支。

## 本轮结束前

运行适用测试；把输出保存在独立目录，再据实更新功能与实际任务状态。创建交接：

```bash
python tools/project_memory.py handoff --task M2-05 --session dev-a-001 --summary "填写实际已做和未做" --next "填写下一项具体动作"
python tools/project_memory.py status --write
python tools/project_memory.py check
```

该命令不会自动填写 completed 或标 DONE；按实际结果补全生成 YAML。后续检查点使用新 session 名，避免覆盖证据。并行任务使用不同分支/工作区/会话文件，合并时人工协调 features/work 账本。

## 运行本包已有离线回归

```bash
python tools/run_quality_checks.py --suite all-offline --feature FEAT-DEV-MEMORY --out acceptance-runs/devtools/my-run-001
```

它执行 6 个已有离线组；全量单元组与专项组有重复用例，不能把两组数量相加宣传。每次用新目录，报告与脱敏日志不会覆盖。APP-* / LIVE-QUALITY 的真实应用测试尚未实现，不包含在 all-offline 内；显式要求执行 PLANNED 组会 NOT_RUN 且非零退出，不假装跳过成功。

报告符合范围后，人工将功能的 last_evidence 指向实际 `report.json`；再次 `status --write`。OFFLINE_PASS 不等于正式验收。完整日常操作和 CI 设置读 docs/09_长期开发与跨会话手册.md。
