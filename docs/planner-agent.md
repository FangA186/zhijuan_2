# 规划 Agent 使用与重载

现在点击“让规划 Agent 设计蓝图”会提交一次真实模型任务：规划 → 结构/范围校验 → 教师核对并确认 → 现有命题/盲解/审核修订链路。点击将计入模型用量；编辑范围与刷新页面不会调用模型。

蓝图含整卷设计说明、每题考点组合、能力目标、难度、设计任务和理由。结构由教师配置决定，Agent不能变更题量、分值和范围。计划失败展示错误；UNKNOWN/停止结果未确认会保留RECONCILING，不自动重发。不支持的共享材料规划会在调用前拒绝。

## 重载（由用户执行）
先确保已有命题/规划任务结束；下面工具会检查活动任务，拒绝在状态不明时重载。不要清账本或删除旧作业。

```bash
cd /Users/fangzengxing/zhijuan_spec_v1_4
.venv/bin/python tools/local_runtime.py stop-generation
# 新增 planner 结构化输出契约挂载，需要重建代理进程加载代码。
# 以下同时保持用户要求的原始返回与深度思考开关：
.venv/bin/python tools/raw_api_console.py start --thinking enabled
.venv/bin/python tools/local_runtime.py start-generation
.venv/bin/python tools/local_runtime.py doctor
```

每条命令成功后再执行下一条。API默认以uvicorn --reload运行，应自动加载代码；若8000由非reload进程管理，正常停止并用原有方式重启（不要同时启动第二个实例）。手工API命令为 `.venv/bin/uvicorn services.api.main:app --host 127.0.0.1 --port 8000 --reload`。前端刷新页面；新的按钮应为“让规划 Agent 设计蓝图”。

命题前先核对教材/范围和分值，再点击规划。规划输出在当前页“Agent实时输出”可回看；完整供应商返回沿用原始API页及其用户配置。已有旧卷不会被自动重写。

## 验收边界
本次完成代码与隔离HTTP/PostgreSQL/浏览器验证。验收中的模型响应为明确标注的合成数据；没有替用户进行真实DeepSeek计费规划。上线第一次23题规划仍需核对输出预算、教学设计质量及实际耗时。

API见 contracts/planning-api.yaml；模型输出契约见 contracts/blueprint-design.schema.json；本次证据见 acceptance-runs/m2-01/planner-agent-20260929-001/report.md。
