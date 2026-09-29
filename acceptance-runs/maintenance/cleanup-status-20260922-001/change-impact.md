# 变更影响记录

任务 ID：M1-07（本轮为目录清理与任务账本校正，不计为产品交付）
分支：main；HEAD：1a89b534185055055d23697f1a61b307efa56253。开始时存在用户未提交修改，全部保留。
用户授权：清理不用的目录文件，并更新任务状态。

## 实际影响
- 删除零代码引用且无工作区修改的 ScoreBadge.tsx；清理 Python 缓存、Finder 元数据及旧 dist/tsbuildinfo。
- scratch_test_img 为临时图片目录；移至项目外恢复目录，清单记录每个文件的哈希和原路径。
- 更新 progress/features.yaml、work.yaml；由工具生成 current.md；增加独立交接。
- tests/test_project_memory.py 的旧测试依赖全产品 NOT_STARTED 快照，已有本轮失败复现；替换为分别传入 NOT_STARTED/IN_PROGRESS 后，验证工具不更改账本且证据仍为 NOT_RUN。保留原无自动完成约束，增加进行中分支。
- 保留旧页面未提交修改、教材与备份、上传资源、Hermes、虚拟环境、依赖、原基线和既有验收报告。
- 无数据库迁移、模型调用、接口或权限变更；不修改生产行为与原 32 项任务基线。
- 产品功能仅按源码标 IN_PROGRESS，不因离线测试而标完成；更正过早 DONE 保留原声明供追溯。

## 验证计划
- 前端构建：验证删除未用组件不影响现有入口。
- memory-tests、memory-check、bundle-contract、acceptance-assets、execution-plan：验证记录与基线。
- 不运行可能读取 .env 并调用模型的全量应用单测；本轮无真实模型、数据库、浏览器、排版验收。
- 实际命令、退出码与报告见 verification.json 和独立 quality 运行目录。

## 决策与恢复
- 未提交源码不删除；ScoreBadge 可从当前 HEAD 恢复，缓存可再生。
- 临时图片可从 cleanup-manifest.json 的 recovery_directory 恢复。
- 下一动作：M0-05 验证 Hermes 能力与隔离，再推进 M1-03 接入修正。

## 检查点
- 首轮前端构建退出码 0；清理的是旧 dist，构建已产生新 dist。
- 首轮质量报告退出码 1：48 项测试中仅旧状态快照断言失败，其余四组检查通过。失败报告保留于 acceptance-runs/devtools/cleanup-status-20260922-001/。
- M0-04 原 DONE 也改为 IN_PROGRESS：锁文件与源码不等于独立环境安装及原生运行验收；原完成声明保留。

- 第二轮 48 项记录工具测试通过，记录检查、契约、验收资产、任务基线检查均通过；退出码 0。详见 verification.json。
- 仅更新 FEAT-DEV-MEMORY 的 last_evidence；产品验证仍 NOT_RUN。
