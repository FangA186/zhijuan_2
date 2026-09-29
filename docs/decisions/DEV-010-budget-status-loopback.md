# DEV-010：预算状态端点的仅环回发布

日期：2026-09-23。状态：已实施（用户于会话中明确要求"继续完成未完成的项"，该项为此前提到的第一号决定）。

## 背景与问题

实施计划 §6.1 将 budget-proxy 定义为"专属 Docker 网络中 8650，唯一官方模型出口；不可暴露无鉴权通用代理"；§7.2/W2-B 要求 API 在受理前读取只读预算状态 `/internal/budget`，不可达时 fail-closed。日常拓扑中 API 是宿主进程，而代理容器未发布宿主端口，导致：

1. 日常就绪的 budget 组件永远 BUDGET_UNAVAILABLE（fail-closed 但功能不可用）；
2. 受理链路的预算门禁永远 503，任何真实命题无法通过受理——包括授权额度内的 L01 单题冒烟。

## 决定

为 `zhijuan-workflow-20260922-live` compose 项目的 `budget-proxy` 服务增加**仅环回**端口发布 `127.0.0.1:8650:8650`（新增 `infra/workflow-acceptance/compose.local-override.yaml`，原 compose.yaml 未改动），并以相同凭据值重建该容器。

## 安全边界分析

- 发布仅绑定 127.0.0.1：宿主上其他机器不可达；容器网络内其他容器（author/solver）的既有访问路径不变。
- 代理所有路由（含 /v1 透传与 /internal/budget）均要求 `Authorization: Bearer ZHIJUAN_BUDGET_PROXY_TOKEN`——不是"无鉴权通用代理"；令牌仅存在于宿主 .env、compose 运行时环境与容器内，不入日志/报告/Git。
- 只读端点 `/internal/budget` 不产生预留、不触上游；透传路径仍是唯一官方模型出口，且每次上游 I/O 前在 SQLite 事务中原子预留（限额 20 次/30 元/1 元每次，未改）。
- 重建时凭据从原容器 Env 原值提取、经 0600 临时 env 文件传给 compose、用后即删；未打印、未入库。

## 影响与验证

- 账本为宿主 bind（/tmp/zhijuan-workflow-20260922/budget → /ledger），重建后验证延续：run zhijuan-workflow-20260922，calls=16、reserved_cny=16、pending=0、min_requests=2 时 sufficient=true。
- 重建后日常 /readyz budget 组件 ok，start-generation 报告真就绪（w1-runtime 与 l01-live 证据引用本决策）。
- 完整 23 题真实验收的预算门控不受本决定影响：46 次最低请求仍超过剩余 4 次，受理门禁将按 B05 语义拒绝。

## 回滚

删除 `compose.local-override.yaml` 并按原 compose.yaml 重建 budget-proxy 容器（凭据同源提取）即可恢复"仅网络内"拓扑；账本文件不受回滚影响。停用日常生成时可用 `tools/local_runtime.py stop-generation`（不影响代理容器）。

## 与既有决策的关系

延续 DEV-008（/internal/budget 端点契约）与 DEV-005（本地运行工具）；不改变 DEV-004 的代理限额提案边界。本决定仅解决"宿主只读可达性"，不批准任何限额上调。
