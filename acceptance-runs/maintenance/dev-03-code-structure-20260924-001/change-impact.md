# DEV-03 变更影响

任务 ID / 功能 ID：DEV-03 / FEAT-DEV-STRUCTURE。分支：本地 `main`；仓库原先已有大量未提交/未跟踪文件，本次保留并在原工作区继续编辑。用户批准全仓代码拆分、目录整理与可再生缓存清理；确认 200 行规则覆盖自有可维护前后端、工具和测试，排除 vendor、生成物与已执行迁移。

## 实际影响

- 前端页面、组件、API 辅助层与服务端路由、领域服务、工具及测试按职责拆分，旧入口尽量保留；活跃模块路径由 `docs/project-map.md` 导航。
- `AGENTS.md` 增加持续适用的 200 物理行规则；`tools/check_code_lines.py` 经 `quality/suites.yaml` 纳入离线检查。
- 根部旧 ZIP 说明/哈希归档至 `docs/archive/v1.4-bundle/`；当前 README 改为导航。保留根部验收脚本、依赖锁定与爬虫兼容入口；静态教材预览移到 `tools/crawler/`，用户上传 DOCX 移至 `uploads/source-docx/` 且不读取内容。`.zcode` 是未跟踪的工作流草稿与运行脚本，保留。
- 删除 16 个仓库自有 `__pycache__` 目录、`apps/web/dist/` 和 `apps/web/tsconfig.tsbuildinfo`，共 18 个可再生缓存/构建项；最终验证后再次清掉新生成的 9 个 `__pycache__` 目录。未动 `.venv`、`node_modules`、`vendor`、`.runtime`、用户图片、上传文件或验收报告。
- 不修改 v1.3 产品/接口基线；不执行数据库迁移、付费模型调用或发布。`database/001_schema_draft.sql` 是冻结设计资料，不是当前维护/执行的迁移，按参考资料排除行数检查。
- 拆分过程中发现并修复教材弹窗入口丢失、Python 跨文件漏导入、词汇图片路径越界、逐题分值汇总误显等问题；独立 Sol 代理继续验收最终页面目录与功能。
- DEV-03 初次 `finish` 发现交接工具无法表示有意删除的源码文件（ScoreBadge.tsx），已增加 `DELETED` 墓碑和“删除后恢复即过期”的定向回归；旧失败预检保留，不将其改写成通过。
- 验证爬虫入口时误用 `--help`（旧脚本不解析帮助参数）触发一次目录抓取并重写忽略跟踪的 `smartedu_data/`；无法凭 Git 证明这些本地数据字节与之前相同。本轮之后只做纯函数导入检查，未再运行爬虫。

## 验证与边界

| 检查 | 当前结果 | 证据 |
| --- | --- | --- |
| 自有可维护代码 200 行门禁 | 最终 0 个超限 | `offline-final-6/report.json` 的 `code-line-limit` 组 |
| Python 离线检查 | 8/8 检查组通过；基线单测 412 项通过、0 跳过 | `offline-final-6/report.json`、`offline-final-6/baseline-unit.json` |
| 前端构建与静态回归 | `npm run build` 通过；Node 前端 16/16 通过 | 本次命令输出；静态测试不代替浏览器行为 |
| 本地浏览器页面操作 | `/project` 四入口及教师配置/教材弹窗/题目页、窄屏、刷新、控制台已按当前状态实测 | [browser-check.md](browser-check.md) |
| 当前历史试卷的题目正确性、真实用户 DOCX、付费生成与生产发布 | NOT_RUN / NOT_ACCEPTED | 当前已有部分失败任务及缺图提示；未获授权执行相关副作用 |

恢复方式：可用 Git 将本轮文件逐项对照恢复，但仓库已有未提交资料，不能直接 reset 清空工作区。归档的旧根资料保持字节不变；用户资源只移动不删除。独立验收及任务收尾记录完成前，DEV-03 保持 IN_PROGRESS。

保留风险：词汇图片查看工具的删除接口原本允许操作 `BASE_DIR` 内任意文件，本轮修复了目录越界和空列表误触发全量恢复；未把该工具扩展为生产权限系统。
