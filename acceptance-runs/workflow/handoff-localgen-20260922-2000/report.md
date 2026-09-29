# 知卷日常工作台真实命题链路：交付报告（handoff-localgen-20260922-2000）

时间：2026-09-22 晚 — 2026-09-23 凌晨。执行者：主代理 glm-5.3-flash + 两批 deepseek-v4-flash-0731 编码子代理（8 并发工作流）。

## 0. 一句话结论

日常入口（localhost:3000 → 8000 → zhijuan_local）的真实命题链路已完整接线并通过全部无费用验收（离线 361 项、PG 集成 17 项、真实队列 4 项、浏览器只读核验）；生成服务当前因"预算状态不可达 + 网关容器未启动"按设计 fail-closed，按钮给出精确原因而非虚假可用；完整 23 题真实验收按预算门控保持 NOT_RUN，账本 16 次/16 元分毫未动。

## 1. 交付内容（W0—W6 对应）

| 工作包 | 交付 |
| --- | --- |
| W0 现场保护 | 库身份核实（zhijuan_local）、pg_dump 备份 84KB（sha256 8cb46351…）、账本快照、草稿只读核对（23题/15000/版本12）、范围澄清遵守（zygf 仅记录最少归属） |
| W1 本地运行接线 | tools/local_runtime.py（doctor/start/stop，fail-closed）、configs/local-runtime.env.example、tools/offline_gate.sh、.env 运行键静默补齐（模型三方一致 deepseek-flash）、.runtime/ 加入 .gitignore |
| W2 真实就绪与预算 | /readyz 升级为 C1 契约（7 组件、原因码、TTL 缓存、fail-closed）；runtime_heartbeats 表（005，测试库先验证后上日常库）；Worker/调度器心跳线程；/internal/budget（C3，内部鉴权、min_requests、旧账延续） |
| W3 受理幂等 | C5 错误契约（428/412/409/503/202）、幂等重放零副作用、预算快照随 job 持久化、advisory 锁内二次核对、HTTP 线程不触模型 |
| W4 前端闭环 | 类型化运行状态 fail-closed、草稿单一状态源（页头修复）、精确禁用原因中文文案、预设卡计数从数据计算（小测 6题）、范围来源标记与跨学段处理、SSE 先 GET 再重连、终态页、受信 usage、中文题型名 |
| W5 隔离复核 | 7 项约束逐条核验：6 项已有实现满足（补测试），1 项修复（shared materials 在计费前最早期拒绝 material_id 槽位） |
| W6 验收 | 见下表 |

## 2. 验收矩阵执行结果

| 层级 | 结果 | 证据 |
| --- | --- | --- |
| T0 离线单测 | **PASS 361 项**（0 失败/0 错误/0 跳过） | gates/unit-final.json |
| 前端逻辑+构建 | **PASS**（node 12 项、vite build exit 0） | w6-gates/report.json |
| T1 PG 集成 | **PASS 17 项**（专属库 zhijuan_accept_w6，003/004/005 先行迁移；含并发创建去重、版本围栏、find_by_plan 真实 SQL、心跳 8 用例） | w6-pg-integration/report.json |
| T2 队列集成 | **PASS 4 项**（真实 Celery Worker + 专用 vhost zhijuan-accept-w6 + 假 Hermes；受理计数断言） | w6-queue/report.json |
| T3 浏览器 | **PASS（只读核验 8 项）**：3000→8000 直连、页头同步修复、五组件精确原因、只读重检无副作用、小测 6题、89 项范围+来源标记、23题/150分草稿完整、浏览后任务表全 0 | w6-browser/report.json |
| T4 真实模型 | **NOT_RUN**（见 §4 预算门控） | w6-budget/report.json |

## 3. 测试计划交付问题逐项回答

- **常用 3000→8000 是否真的接通？** 是。api.ts 直接以 `http://localhost:8000/v1` 为基址，浏览器加载出用户 23题/150分草稿即为活体证明；未用 3002/8001 冒充。
- **配置齐全但 Worker 死亡时，按钮与服务端是否都能阻止？** 是。浏览器显示 WORKER_UNAVAILABLE 等精确原因且按钮禁用；服务端 start_generation_job 返回 503 GENERATION_NOT_READY（含 reason_codes），离线单测覆盖。
- **23题/150分与不等分解答题是否保持？** 是。草稿 version 12、spec_revision 4 全程未变；17×400+1200+1400×5=15000 经 PG 集成与浏览器分值核对双重确认。
- **旧课程范围？** 草稿范围为高一教材 89 项 + 4 个手动补充考点（教师本人添加，带来源标记，可单独移除）；未发现九年级遗留考点混入。跨学段切换的处理逻辑已实现（提示失效项→教师选择→强制重新确认）。
- **双击/断网/重复消息/Worker 重启的上游受理次数？** 队列集成实测：正常完成=author 1+solver 1；重复派发=0 新增；先取消=0；受理 5xx=恰好 1 次尝试无重发。离线单测覆盖幂等重放 202 零副作用。
- **费用余量能否支持整个计划？** 不能：46 次最低请求 vs 剩余 4 次；B05 预检在任何上游调用前以 409 BUDGET_INSUFFICIENT 拒绝。**预检失败不产生任何收费**（预算门禁先于 job+outbox 事务）。
- **取消语义？** 本地取消+已受理上游尽力 stop（F15 语义保留：stop 失败不伪造已停止）；本会话无未决账单（账本 16 条全部 SUCCEEDED）。
- **REVIEW/FAIL 展示与未完成边界？** 盲解一致仍判 REVIEW（无可信数学证明），队列集成实测断言；发布/未版本化重生成入口保持禁用。
- **关闭闲置生成服务后草稿是否可用？** start-generation 的回收过程实测 PG/Vite/API 未受影响，草稿读写正常；未运行 stop-generation（无活动任务场景，拒绝路径有单测）。**其他项目（zygf-*）完全未动。**
- **未跑用例？** 见 §4。
- **本会话代码变更 vs 旧真实验收**：本轮全部代码变更（两批次）均发生在既有 6823-token 单题真实验收之后，该旧证据不覆盖本源码——因此本轮不做任何真实模型声明。

## 4. 未完成项（如实列出）

1. **L01–L04 真实模型验收全部 NOT_RUN**。阻塞链：预算状态端点 /internal/budget 仅在 docker 网络内可达（代理容器未发布宿主端口）→ 就绪与受理预算门禁按设计 fail-closed → 任何收费受理无法通过。解除需要你的决定：为 /internal/budget 增加仅 127.0.0.1 发布（需重建代理容器，安全边界变更，应先写 decision）。
2. **完整 23 题真实验收 NOT_RUN**（你的明确门控）：最低 46 次请求 vs 剩余 4 次；需新增预算授权或先审查通过 §7.3 严格上界预留方案。
3. 浏览器交互类用例（模板导入/确认/断网恢复/终态页/SSE 掉线重连的真实 DOM 操作）未在日常入口执行——保护用户草稿，相关逻辑由离线单测+PG/队列集成覆盖；U11 模板上传 NOT_RUN。
4. F 组故障注入覆盖了受理丢失/取消/重复投递/分值围栏；状态轮询超时、错 run_id 等窗口由离线 transport 测试覆盖（test_hermes_runs_transport），未在真实 Worker 进程内复跑。
5. `ETAG_MISMATCH`（412 的 code）不在 C5 枚举内、兜底 readiness dict 缺 checked_at——两处为 T10 登记的观察项，均不误绿，维持现状待你裁定。
6. API 进程会话中途曾死亡（原因未查明；本会话无杀进程操作），已用原方式分离重启；Vite 同样处理。两进程现由本会话托管（日志在 .runtime/logs/），你下次自行重启后将回到你自己的终端管理。

## 5. 需要你的三个决定

1. 预算状态端点的宿主可达方案（批准后我方实施并写 decision）。
2. 完整 23 题验收的新增预算授权（或 §7.3 上界预留设计评审）。
3. 是否将本轮未提交的 181 项变更提交（本会话未做任何 git 提交）。

## 6. 运行中的服务（当前状态）

- PG 容器：运行（你的草稿安全）。MQ 容器：运行，vhost zhijuan-local（日常）/ zhijuan-accept-w6（验收残留可随时删除）。
- API 8000：运行（本会话恢复）。Vite 3000：运行（本会话恢复）。
- Worker/调度器：未运行（start-generation 因预算 fail-closed 按设计回滚）。
- author/solver-entry/budget-proxy 容器：未启动。
- 费用账本：16 次/16 元，0 未决，本会话 0 次模型调用、0 元成本。
