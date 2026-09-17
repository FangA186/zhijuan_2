# MVP 与验收材料入口 · v1.3

**本目录是待执行验收规程，不是应用代码、E2E 自动化实现或通过报告。全部 47 类用例默认 NOT_RUN。**

## 阅读与执行顺序

1. 阅读 `../docs/07_MVP阶段_验收链路_交付效果.md`：M0 准备、M1 可运行骨架、M2 最小闭环、M3 完整受控试用。
2. 填写并批准 `capability-matrix.template.yaml` 中的首发能力、质量阈值、环境和预算。三个数学条目只是 M2 冒烟基线，不是最终学科清单。
3. M1 先完成真实前后端、固定 Hermes 接入和 DeepSeek 调用；不能用当前 Protocol 接口声明代替运行实现。
4. 执行 `minimum-cases.yaml`：12 类成功检查点在三学段各跑一遍，7 类失败用例留证；MIN-N05、MIN-N07 三学段复测。
5. 执行 `full-cases.yaml`：28 类检查加首发能力分层扩展；用 `demo-runbook.md` 组织现场演示。
6. 按 `evidence-manifest.template.json` 登记受限证据，填写 `acceptance-report.template.md` 与 `delivery-checklist.md`。

## 文件说明

- `mvp-plan.yaml`：阶段、依赖、退出门槛与建议目标，不是当前实现进度。
- `minimum-cases.yaml` / `full-cases.yaml`：前置条件、操作、预期、证据、责任与状态。
- `fixtures/minimum-*.json`：小学、初中、高中的 5 题 20 分命题输入；没有生成题和参考答案。`scope_confirmed=false`，需教师确认后才可提交真实任务。
- `capability-matrix.template.yaml`：能力登记和阈值签署模板，初始未批准且无 READY 能力。
- `acceptance-report.template.md` / `evidence-manifest.template.json`：报告及证据模板，不得编造通过率、费用或签名。
- `delivery-checklist.md`：未来可运行工程应交付的内容，所有完成项由实际交付后勾选。
- `demo-runbook.md`：现场演示步骤，需使用已经实现的应用，不提供不存在的启动命令。
- `current-delivery-status.json`：本次设计包的真实边界；Hermes 源码和运行应用未交付。

## 离线材料检查

在包根目录运行 `python verify_acceptance_assets.py` 可检查用例 ID、状态、三学段配置、参考路径与模板空值。这仅验证材料一致性，不执行 Hermes、DeepSeek、浏览器出卷、安全测试或 MVP 验收。

真实验收结果应另存 `acceptance-runs/<run-id>/`，保持模板不变；受限答案和证据不要混入公开 ZIP，禁止携带 API Key。
