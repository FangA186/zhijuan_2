任务 ID / 功能 ID：M2-01 / FEAT-PLAN
实际分支、HEAD、未提交修改：main / 1a89b534185055055d23697f1a61b307efa56253；工作区已有大量用户及并行代理修改，未覆盖非职责文件。
本次要改变的用户行为：仅从通过 canonical ExamSpec 校验的规格生成整卷叶子题槽；计划冻结规格与修订并提供内容哈希，题槽不可静默改写。
本次明确不改变的行为：不调用模型、不执行真实命题、不确认或发布计划。

## 实际影响
- 直接修改的模块与文件：services/blueprint/allocator.py、generator.py、rules.py，services/exam/blueprint_service.py，tests/test_blueprint_engine.py。
- 调用方、共享 schema、依赖和依赖方：BlueprintService 通过 store 读取 canonical spec/revision、保存计划和按 plan_id 确认；主代理负责 store 与 routes 集成。
- 新增/删除/重命名路径，脚本未映射内容：新增本证据目录和独立交接。
- 数据迁移、兼容、模型/Skill/工具权限、成本影响：无迁移、无计费；旧的非 canonical 模板解析结果不能直接作为蓝图输入。
- 应保持的回归行为及编号：MIN-02、MIN-03、FULL-03、FULL-10。

## 验证计划与执行结果
| 组/用例 | 为什么要跑 | 实际命令/版本 | 结果 | 证据 |
| --- | --- | --- | --- | --- |
| 蓝图离线测试 | 题槽数/分值/范围/哈希 | .venv/bin/python -m unittest tests.test_blueprint_engine | PASS, 4 tests | 当前终端输出 |
| 模板解析兼容 | 旧调用方验证 | .venv/bin/python -m unittest tests.test_template_parser | FAIL, 1 test：非 canonical 输入缺 curriculum_system | 当前终端输出 |
| diff 规范 | 空白检查 | git diff --check -- services/blueprint services/exam/blueprint_service.py tests/test_blueprint_engine.py | PASS | 当前终端输出 |

## 决策与恢复
批准变更记录：按 M2-01 已批准范围；模板解析非 canonical 输入不放宽。
失败后的恢复步骤/不可逆影响：本地可恢复；无外部副作用。
尚未确认的风险和下一动作：主代理集成 store 的 plan_id/spec_revision/plan_hash 确认门禁并跑端到端离线回归；模板解析旧测试由其职责方修复。
