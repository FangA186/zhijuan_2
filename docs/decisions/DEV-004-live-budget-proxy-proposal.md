# DEV-004：本轮验收本地费用闸门建议

状态：ACCEPTED（仅本轮受控验收）
提出人/日期：Codex / 2026-09-22
批准依据：用户于本会话明确回复“允许本地限额代理，仍限 30 元”（2026-09-22）。不代表生产变更或阶段签收。
关联任务/功能：FEAT-ADAPTER，M1-03；仅 zhijuan-workflow-20260922 验收

## 背景和约束

固定 Hermes 源码的 HTTP Runs 没有可证明的整轮 token/费用硬限，输出截断还可触发自动续写。用户本轮允许新增独立的本地硬限额代理，总预算上限 30 元人民币，不授权修改 vendor 或生产接入规则。

## 可选方案与证据

- 仅设 Hermes `agent.max_turns` / `api_max_retries`：不限制单次输出，也不阻断截断恢复，不能证明 30 元硬限。
- 在 Hermes 与官方 DeepSeek 之间放本地代理：每个受理请求先持久预留 1 元，最多 20 次；只允许 `deepseek-flash` 纯文本、非流式、无工具的 Chat Completions。选择此方案用于本次有限验收。

官方 [DeepSeek Chat Completions 文档](https://api-docs.deepseek.com/api/create-chat-completion/) 支持 `max_tokens`、`thinking: {type: disabled}` 与 `reasoning_effort: none`。按本轮核验的峰值单价 $0.3/M 输入、$1.2/M 输出，并用保守汇率 1 USD = 10 CNY，200,000 输入 token 与 4,096 输出 token 的理论上界约 0.65 元。代理把请求体限制在 200,000 UTF-8 bytes，且只接收纯文本消息；按每次 1 元预留，而非按实际账单扣费。若 API 另计未纳入该单价的费用，此界不适用，须停止验收并重算。

## 数据、接口、权限、成本与兼容影响

代理只监听指定本地地址或专属 Docker 网络，默认 127.0.0.1:8650；上游目的地固定为 `https://api.deepseek.com/chat/completions`。认证后的 GET `/v1/models` 仅返回本地 `deepseek-flash` 元数据，不访问上游或预留额度。入站 `ZHIJUAN_BUDGET_PROXY_TOKEN` 与上游 `DEEPSEEK_UPSTREAM_API_KEY` 仅来自运行环境；代理不在响应或日志中输出密钥。SQLite 账本由 `--ledger` 指向持久卷，`BEGIN IMMEDIATE` 在上游 I/O 前原子预留；失败、超时和未知响应均不释放额度。最多 20 个计费请求和 20 元预留，低于用户的 30 元上限；剩余 10 元是额外余量，不表示已消费金额。

固定 Hermes 的 `hermes_cli/providers.py` 为 deepseek 注册 `DEEPSEEK_BASE_URL`，`hermes_cli/runtime_provider.py` 的显式 provider 解析读取该环境变量。验收容器将 `DEEPSEEK_BASE_URL` 设为 `http://<代理地址>:8650/v1`，将其 `DEEPSEEK_API_KEY` 设为内部 token；真实官方 key 只给代理。Hermes Runs 请求仍指定 `provider: deepseek`、`model: deepseek-flash`。代理拒绝工具请求；如 Hermes 主 Agent 发出带 `tools` 的调用，验收应停止并记录阻断，不移除职责后悄悄放行。不同容器中的 `127.0.0.1` 不是同一网络地址，必须用仅验收网络可达的代理服务名。

固定 Hermes 在 `agent/agent_init.py` 读取 `config.yaml` 的 `model.streaming: false`，并在 `agent/turn_api_call.py` 禁用流式底层请求。Runs 的状态轮询和增量回调不改变此决策。本轮验收 profile 必须设置 `model.streaming: false`；代理仍拒绝 `stream: true`，使配置偏离时在上游收费前失败。该项是验收专用运行配置，不改生产主 Agent 的职责。

## 实施/迁移/回滚

运行 `tools/live_budget_proxy.py --ledger <持久卷路径> --bind <专属网络地址> --port 8650`。同一账本不得重置或换路径以恢复额度；停止本轮验收时关闭代理、撤销内部 token，并把 Hermes 的 DeepSeek 路由恢复为原配置。不得让代理成为通用生产出口。

## 必须重跑的测试

`tests/test_live_budget_proxy.py` 的 Mock 测试覆盖收费请求前预留、并发 20 次上限、模型与工具路由、大请求、未知结果不退款、秘密不回显和仅入账用量摘要。启动后还需只读核对 Hermes 对代理的路由和实机外部账单；未授权真实请求前不声称模型验收通过。

## 关联文件及被替代决定

`tools/live_budget_proxy.py`、`tests/test_live_budget_proxy.py`。此建议不替代正式架构与模型接入决策。
