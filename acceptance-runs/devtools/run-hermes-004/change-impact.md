# 变更影响记录 (M1-03 / M1-07)

任务 ID / 功能 ID：M1-03 (实现受控 Hermes HTTP Adapter 与状态映射), M1-07 (实现真正的网页配置、任务和结果页面)
实际分支、HEAD、未提交修改：分支 main，HEAD 7cc58b93c95906ca142ee6e598468830bb9b45ca，未提交代码已在工作区保护。
本次要改变的用户行为：
- 用户可在网页端顶部一键切换【Mock演示环境】与【后端联调环境】；
- 教师在三栏工作台点击【重新生成该题】时，后端调用 Hermes + DeepSeek 官方 API 进行实时原创命题与独立隔离盲解核验，并在界面同步展示 5 步推理过程与绿色 PASS 标签。
本次明确不改变的行为：
- 学生视图公开投影彻底剥离私有答案与评分标准，分值保持 score_x100 整数；
- 绝不引入 LangChain、LangGraph 或未经锁定的第三方 Agent 框架；
- 绝不在前端网络传输或日志中泄露 DEEPSEEK_API_KEY。

## 实际影响
- 直接修改的模块与文件：
  - `services/api/` (main.py, settings.py, health.py, store.py, routes/exams.py)
  - `services/hermes_adapter/` (adapter.py, http_adapter.py, runtime_factory.py, status_map.py, blind_runtime.py, comparator.py, schema_validator.py, skills_loader.py)
  - `apps/web/` (ExamEditor.tsx, Header.tsx, api.ts)
- 调用方、共享 schema、依赖和依赖方：
  - 依赖 contracts/candidate.schema.json, reference_code/adapter_contract.py
  - FastAPI 暴露 /v1/exams 接口供 Vite 前端调用
- 新增/删除/重命名路径，脚本未映射内容：
  - 新增 services/api/, services/hermes_adapter/, apps/web/
- 数据迁移、兼容、模型/Skill/工具权限、成本影响：
  - 接入 DeepSeek 官方 API，单次出题+盲解实测消耗 ~1500 tokens，每次操作记录耗时与模型 ID (deepseek-flash / deepseek-chat)
- 应保持的回归行为及编号：
  - FEAT-DEV-MEMORY (OFFLINE_PASS)
  - FEAT-BLIND (盲解绝对隔离私有字段)

## 验证计划与执行结果
| 组/用例 | 为什么要跑 | 实际命令/版本 | 结果 | 证据 |
| --- | --- | --- | --- | --- |
| 适配器单元测试 | 确保适配器契约与隔离 | `.venv/bin/python -m unittest tests/test_hermes_adapter.py` | PASS | 11 tests in 0.028s |
| 记忆库与回归测试 | 确保防篡改账本与规则 | `.venv/bin/python -m unittest discover -s tests` | PASS | 124 tests in 5.6s |
| 全套离线门禁 | 6 大离线 Suite 统一验收 | `.venv/bin/python tools/run_quality_checks.py --suite all-offline` | PASS | run-hermes-002/report.json |
| 记忆自检 | 校验依赖图与文件存在性 | `.venv/bin/python tools/project_memory.py check` | PASS | 0 warnings |
| 真机命题与盲解 | 端到端 API 真实调用 | `POST /v1/exams/current/questions/slot_01/regenerate` | PASS | 返回二次方程及 5 步盲解 (2283ms) |
| 前端构建 | 确保 TypeScript 与分包正常 | `npm run build` (apps/web) | PASS | 0 TS errors, 962ms |

## 决策与恢复
批准变更记录：
- 按照方案线路 B，锁定 Hermes 官方源码至 commit f5d1926，实现精简 Adapter 与角色隔离工厂。
失败后的恢复步骤/不可逆影响：
- 若后端服务异常，前端可通过顶部切换按钮瞬间退回 Mock 演示模式，不影响界面操作。
尚未确认的风险和下一动作：
- 下一动作：推进 M1-04（任务投递持久化与 Celery 异步队列）与 M1-02（PostgreSQL 事务仓储）。
