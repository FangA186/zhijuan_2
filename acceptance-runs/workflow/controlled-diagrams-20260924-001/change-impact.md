# 受控算筹图：变更影响

任务 ID：M2-03（资产完整性）；关联 M2-07（页面与导出预检）。功能：FEAT-CHECK、FEAT-EXPORT。

实际分支、HEAD：`main` / `1a89b53`。已有大量用户未提交修改；本轮仅增量修改关联文件，不提交或清理。

本次改变的用户行为：1～5 算筹图由受信服务按结构参数生成 SVG，题目引用真实内容哈希资产；缺图或伪造图引用不再被当作完整题面，页面明确报错。

## 实际影响

- 后端：作者候选契约、绘图与本地资产、盲解前归一化、确定性检查、当前试卷资产读取。
- 前端：题面/选项图形显示，浏览器打印和旧 Word 导出的缺图保护。
- 存储：新增 `.runtime/assets/` 本地内容寻址 SVG，无数据库迁移。worker/API 必须共享该目录；生产对象存储与租户权限仍未实现。
- 模型/费用：继续使用 DeepSeek/Hermes；无 GPT 路由，离线验证不调用模型或增加预算。
- 旧数据：昨天的试卷及其 `slot_022` 不静默改写；旧伪资产引用将显式显示缺图。

## 验证计划与执行结果

| 组/用例 | 为什么要跑 | 实际命令/版本 | 结果 | 证据 |
| --- | --- | --- | --- | --- |
| 算筹图与资产门禁 | 验证根数、非法参数、伪造/损坏引用与当前试卷读取范围 | `.venv/bin/python -m unittest tests.test_diagram_assets tests.test_diagram_asset_gate tests.test_validators tests.test_candidate_integrity tests.test_generation_pipeline -v` | OFFLINE_PASS，23 项 | [report.json](report.json) |
| 后端相关回归 | 验证契约、隔离、盲解前拦截与旧安全边界 | `env -u DATABASE_URL ZHIJUAN_SKIP_DOTENV=1 .venv/bin/python -m unittest tests.test_contracts tests.test_blind_isolation tests.test_workflow_safety_closeout -v` | OFFLINE_PASS，18 项 | [report.json](report.json) |
| 前端构建与图形显示 | 验证合法 ID、缺图提示、含图导出阻断与编译 | `node --test tests/frontend_diagram_asset.test.mjs`；`cd apps/web && npm run build` | OFFLINE_PASS，3 项且构建成功 | [report.json](report.json) |

## 决策与恢复

批准变更：[DEV-012 决策](../../../docs/decisions/DEV-012-controlled-diagram-assets.md)。用户选择受控绘图，排除 GPT 生图。

恢复：停用新 diagram 输出并回退本轮代码；保留已有候选与资产，不能通过删除文件伪造回滚成功。

尚待确认：真实 Hermes 产出该 spec 的比例、教师对图形内容的审核、生产存储/鉴权、正式 PDF/DOCX 产物检查。这些均不能由本轮离线结果代签。首次扩大回归因本地 `.env` 指向不可达 PostgreSQL 而在导入时失败；禁用 dotenv 且移除 `DATABASE_URL` 后，同一组测试 18 项通过，未写数据库。
