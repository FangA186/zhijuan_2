# 项目源码导航

本页只负责定位。实现状态、依赖和限制查 [功能账本](../progress/features.yaml)，运行结果查其登记证据；文件存在不等于已验收。

| 要改什么 | 从哪里进入 |
| --- | --- |
| 教师向导、试卷工作台 | `apps/web/src/App.tsx` → `app/useAppState.ts` → `pages/FoolproofSetup.tsx`、`pages/ExamPaperWorkbench.tsx`；具体页面模块在 `pages/foolproof-setup/`、`pages/exam-paper/`，接口封装在 `lib/api.ts` 与同目录分段模块 |
| 试卷规格、蓝图、题目、任务接口 | `services/api/main.py` → `routes/exams.py`（路由入口）→ `routes/exam_*_routes.py` → `services/exam/`；状态容器入口在 `services/api/store.py`，具体职责拆在同目录模块 |
| 教材、章节、词汇图片 | `services/api/routes/curriculum.py` → `services/curriculum/`；前端教材选择与学科配置在 `apps/web/src/components/` |
| 分值、考点与题槽分配 | `services/blueprint/generator.py`、`allocator.py`、`slot_builder.py` |
| 模型接入、盲解与答案比较 | `services/hermes_adapter/`；运行来源在 `install/`。对照接入基线核验实际调用，名称带 Hermes 不证明运行经过 Hermes |
| 导出与公开投影 | `apps/web/src/components/ExportModal.tsx`、`apps/web/src/lib/projection.ts`；目标排版管线见架构基线 |
| 数据库与队列实现 | `database/001_schema_draft.sql`、`infra/compose.yaml` 是起点；正式迁移、仓储与 Worker 的实际入口以功能账本为准 |
| 产品契约、任务与验收要求 | `contracts/`、`execution/task-index.yaml`、`acceptance/`；`reference_code/` 仅为参考实现 |
| 开发记录与质量工具 | `tools/project_memory.py`、`tools/memory_lib.py`、`tools/run_quality_checks.py`；`tools/check_code_lines.py` 检查单文件 200 行上限，检查组登记在 `quality/` |

## 影响关系

修复缺陷先查 [Bug 记忆流程](../progress/bugs/README.md)；事实记录在 `progress/bugs/`，通过 `tools/bug_memory.py search` 检索。本机 `/project?tab=bugs` 提供搜索、状态筛选、根因详情与 Notion 链接。

业务链路：配置 → 蓝图 → 命题 → 盲解/检查 → 修订 → 编辑/复核 → 导出 → 发布。

改题或版本影响后续检查与审批；公开投影影响盲解和学生产物；任务执行影响取消、迟到结果、费用与恢复。`impact` 按登记路径和依赖映射，不替代调用链分析。

## 开发与生产的边界

`AGENTS.md` 指导开发；`skills/*/SKILL.md` 指导生产 Hermes 角色。开发记录和验收控制答案不向生产命题运行开放。`quality/regression-map.yaml` 中的预期行为、参考测试和真实应用回归分别看待。
