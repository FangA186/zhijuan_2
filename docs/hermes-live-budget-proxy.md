# 本轮 Hermes 真实验收的预算代理运行说明

仅供 `zhijuan-workflow-20260922`。代理在发往官方 DeepSeek 前先写 SQLite 预留账本；最多 20 次、每次预留 1 元，预留总额最多 20 元，低于获准的 30 元。预留不等于实际账单，失败和未知结果也不退款。未经再次核对价格、模型与隔离配置，不复用于生产或下次验收。

## 代理

- 程序：`tools/live_budget_proxy.py`。
- 默认监听：`127.0.0.1:8650`；Docker 专属网络可用 `--bind 0.0.0.0 --port 8650`，不发布宿主机端口。
- 必须传 `--ledger <持久卷路径>`。重启沿用同一文件，不复制空账本重置次数。
- 账本的 `budget` 表保存调用次数与预留总额；`reservations` 表逐次保存编号、UTC 时间、状态、HTTP 状态，以及成功响应中的 `prompt_tokens`、`completion_tokens`、`total_tokens`、模型和提供商请求 ID。响应正文、题目、答案、推理及密钥不入账。`RESERVED` 或 `UNKNOWN` 都按可能计费处理，不释放额度。
- `SUCCEEDED_USAGE_UNKNOWN` 表示 HTTP 成功但未返回完整用量；仍保留 1 元预留。报告可查询 `SELECT id, created_at, status, reserved_cny, prompt_tokens, completion_tokens, total_tokens, provider_model, provider_request_id FROM reservations ORDER BY id`，并将预留额、按用量估算和最终平台账单分开。
- 代理运行环境：`ZHIJUAN_BUDGET_PROXY_TOKEN` 为内部入站 token，`DEEPSEEK_UPSTREAM_API_KEY` 为官方 key。仅代理持有官方 key，不打印二者。
- POST `/v1/chat/completions` 或 `/chat/completions` 固定转发至 `https://api.deepseek.com/chat/completions`。GET `/v1/models` 或 `/models` 本地只返回 `deepseek-flash`，不访问上游或预留额度。
- 本轮只允许纯文本 `messages`、`deepseek-flash`、非流式、无工具；请求体最多 200,000 UTF-8 bytes，`max_tokens` 限到 4,096，并强制 `thinking: {type: disabled}` / `reasoning_effort: none`。代理固定 response_format 为 json_object，供本轮命题/盲解结构化输出；拒绝不支持的字段或路径。

## Hermes 专属运行配置

固定 Hermes 源码在 `hermes_cli/providers.py:56` 为 `deepseek` 注册 `DEEPSEEK_BASE_URL`；`hermes_cli/runtime_provider.py:608-626` 的 provider 解析读取它。每个验收用 Hermes 容器设置：

```text
DEEPSEEK_BASE_URL=http://budget-proxy:8650/v1
DEEPSEEK_API_KEY=<同 ZHIJUAN_BUDGET_PROXY_TOKEN 的内部 token>
```

两个容器必须在同一专属网络；容器内的 `127.0.0.1` 指向各自容器，不能用于互连。Runs body 继续指定 `provider: deepseek`、`model: deepseek-flash`。现有 profile 若设置了 `model.base_url`，它可能优先于 `DEEPSEEK_BASE_URL`；必须删除旧直连值或明确改成代理地址，并检查实际 provider runtime 解析的 base URL 后才可发付费请求。

各 Hermes profile 的 `config.yaml` 必须设置：

```yaml
model:
  streaming: false
agent:
  max_turns: 1
  api_max_retries: 1
```

源证：`agent/agent_init.py:1192-1200` 把 `model.streaming: false` 变成 `_disable_streaming`，`agent/turn_api_call.py:47-54` 在此情况下走非流式 API；`gateway/platforms/api_server_runs.py:666` 虽传入增量回调，也不覆盖这个传输开关。`max_turns` 和 `api_max_retries` 只是额外收敛参数，费用硬限来自代理持久预留，不能把它们当成硬预算。若仍出现 `stream: true` 或 `tools`，代理会在预留前拒绝；应停下来修正验收 profile，而不是取消代理校验。

## 核验与回滚

离线验证：`.venv/bin/python -m unittest tests.test_live_budget_proxy -q`。真正启动后先用只读 `/v1/models` 核对认证与路由，再核对账本初始次数和两个隔离容器的运行配置；只有主验收负责人可发授权的付费请求。结束时停止代理、撤销内部 token，保留账本和本轮证据。
