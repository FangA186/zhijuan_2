# Hermes 原生运行时基线与环境锁定报告 (M0-04)

> 依照《知卷实施手册》M0-04 任务规范生成，用于固定上游 Hermes Agent 执行框架的源码来源、提交指纹与隔离安装基线。

---

## 1. 上游源码来源与版本锁定

| 属性 | 锁定值 / 规范状态 |
| :--- | :--- |
| **官方仓库** | `https://github.com/NousResearch/hermes-agent.git` |
| **本地路径** | `vendor/hermes-agent` |
| **锁定 Commit (40位)** | `f5d192611032025d2757b07ad838921872126182` |
| **检出模式** | `detached HEAD` (无未跟踪更改，工作区 clean) |
| **开源许可证** | MIT License (Copyright 2025 Nous Research) |
| **许可证 SHA256** | `821556e6336796450ab852d375117b48a4887e71d255794fd6318d99982a5ab6` |
| **uv.lock SHA256** | `811a21647251a3fd024a3e2f49c90ac0600c678e500cc08ed51db38c452a6c65` |
| **pyproject.toml SHA256** | `eb0b8daac75c0c0e655282a1a836cb4c8a0bdc266e435a4d77e3295544ccf488` |

---

## 2. 环境分离与隔离策略

根据知卷架构规范（`docs/06_DeepSeek_Hermes接入指南.md`）：
1. **双环境强隔离**：
   - **知卷业务环境 (`.venv/`)**：运行 FastAPI 后端、PostgreSQL 驱动、Celery Worker、KaTeX 渲染与薄 Adapter 接口（`services/hermes_adapter/`）；
   - **Hermes 原生环境 (`.venv-hermes/` 或独立容器)**：运行 Nous Research 官方 Hermes 核心、CLI 与 Gateway 服务，避免上游庞大依赖树（如 LangChain 第三方插件、各类 MCP 等）侵入业务进程。
2. **凭据隔离**：
   - `DEEPSEEK_API_KEY`：官方模型访问凭证，仅供出题与盲解调用；
   - `API_SERVER_KEY`：Hermes Gateway 内部通信凭据，严禁与模型 Key 混用。

---

## 3. 安装与验证指引

### 3.1 离线/受控安装
运行交付的安装脚本：
```bash
bash install/hermes-install.sh
```

### 3.2 验证基线
在激活的环境中核验：
```bash
source .venv-hermes/bin/activate
hermes --version
hermes --help
```

---

## 4. 与知卷薄 Adapter 的协同关系

知卷系统不直接修改 `vendor/hermes-agent` 内部代码，而是通过 `services/hermes_adapter` 进行受控桥接：
- **Prompt 与 Skills 映射**：挂载 `skills/question-author` 与 `skills/blind-solver`；
- **契约校验门禁**：通过 `services/hermes_adapter/schema_validator.py` 强制校验符合 `contracts/candidate.schema.json`；
- **盲解隔离保障**：通过 `services/hermes_adapter/blind_runtime.py` 剥离任何参考答案字段，确保解题独立性；
- **同模型审计标记**：通过 `services/hermes_adapter/comparator.py` 严格打标 `[SAME_MODEL]`。
