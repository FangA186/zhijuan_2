# DEV-011：完整整卷真实验收的预算上限放宽（用户授权）

日期：2026-09-23。状态：已实施。

2026-09-24 更新：当前本地请求/金额上限已由 [DEV-013](DEV-013-local-uncapped-generation.md) 取代；以下保留当时的批准与实施记录。

## 授权来源

用户在会话中明确表示："没事啊你直接真实请求api测试啊，我放宽要求了"，并要求"你直接完整的生产一整套试卷我看看"。本决定将该授权落为受控的参数变更，属实施计划 §7.1 所述"获得明确新增预算"路径；不是接手 AI 私自绕过限额。

## 变更内容

1. `tools/live_budget_proxy.py` 的 `MAX_REQUESTS` / `MAX_RESERVED_CNY` 改为环境可覆盖（`ZHIJUAN_BUDGET_MAX_REQUESTS` / `ZHIJUAN_BUDGET_MAX_RESERVED_CNY`），**代码默认值保持 20 次 / 30 元不变**；非法/缺失环境值回退默认。
2. 运行环境（compose.local-override.yaml，仅 budget-proxy 服务）注入新上限 **80 次 / 80 元**。依据：23 题 × 每题最低 2 次上游请求 = 46 次，已用 18 次，46 + 18 = 64 ≤ 80，另留约 16 次余量吸收 Hermes 续写/重试；预留按每请求 1 元保守计，上限 80 元。
3. 未改动：`RUN_NAME`、`RESERVE_CNY`、`MAX_BODY_BYTES`、`MAX_OUTPUT_TOKENS`、账本路径、既有 18 条账本记录（重建后验证 calls=18 延续）。

## 验证

- 单测：默认值不变、环境上调生效、非法值回退、旧账延续且 80 上限足以容纳整卷（tests/test_live_budget_proxy.py::EnvOverrideLimitTests）。
- 重建后 `/internal/budget?min_requests=46`：calls=18、max_requests=80、remaining=62、BUDGET_OK。

## 边界与回滚

- 本决定只提高计数/预留上限，不改变"每次上游 I/O 前 SQLite 事务内原子预留"、UNKNOWN 不退款、缺 usage 不记零等既有语义。
- 作业若中途出现 RECONCILING/UNKNOWN，仍按既有语义如实停止、绝不自动重发。
- 回滚：从 override 文件移除两个环境变量并重建容器即回到 20/30；账本不受影响。
- 实际官方账单以 DeepSeek 账单为准，保守预留（每请求 1 元）不等于实际费用；整卷跑完后实际费用仍需对账，未知就写未知。
