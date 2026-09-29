# 知卷日常真实命题：详细测试与验收矩阵

配套 [实施计划](2026-09-22-local-generation-implementation-plan.md)。本文列的是接手AI必须执行的步骤和断言，**不表示这些新增测试已经实现或通过**。

**范围限制：只测试知卷。其他项目名称只用于排除误操作，不授权检查其配置、日志、数据库或健康状态。涉及“其他容器”的保护用例使用模拟容器清单/命令调用记录验证，不实际操作用户其他项目。**

## 1. 测试环境与不可混淆的证据

| 层级 | 环境 | 可证明的内容 | 不能宣称的内容 |
| --- | --- | --- | --- |
| T0 单元 | 无真实DSN、无模型密钥、无外部网络 | 分支、转换、校验、状态机 | 队列真实运行/官方模型通过 |
| T1 PG集成 | 明确命名的专属新库/schema | 事务、并发、持久化、版本围栏 | Worker活着、真实模型正确 |
| T2 队列集成 | 专用RabbitMQ vhost、真实Worker、受控假Hermes | 真正派发、消费、重启、SSE/落库闭环 | DeepSeek接入或教学质量 |
| T3 浏览器 | 测试草稿与可追踪服务，最后核对正常3000→8000 | 用户实际操作与恢复 | 学生权限隔离/正式发布 |
| T4 LIVE | 受限费用出口、固定Hermes、已核对官方模型 | 授权样本真实运行 | 完整23题/全学科验收，除非确实测完 |

T0–T3不得持有真实上游key。静态配置完整的fixture只测试配置逻辑；真实就绪用例必须让相应进程实际断开/恢复，不能全部patch成True。

## 2. 接手先跑的已有测试

### 2.1 Python离线主集合

先审查 `tests/` 是否新增了外部副作用，再在仓库根运行。下面的RUN_ID必须改成新名字，不覆盖旧证据：

```bash
ZHIJUAN_TEST_RUN=handoff-YYYYMMDD-HHMMSS
mkdir -p "acceptance-runs/workflow/$ZHIJUAN_TEST_RUN"
ZHIJUAN_SKIP_DOTENV=1 DATABASE_URL= ZHIJUAN_TEST_DATABASE_URL= CELERY_BROKER_URL= \
DEEPSEEK_API_KEY= DEEPSEEK_UPSTREAM_API_KEY= HERMES_API_BASE_URL= HERMES_API_KEY= \
HERMES_SOLVER_API_BASE_URL= HERMES_SOLVER_API_KEY= HERMES_SOLVER_UPSTREAM_KEY= \
ZHIJUAN_BUDGET_PROXY_TOKEN= API_SERVER_KEY= \
.venv/bin/python tools/run_unittests.py \
  --report "acceptance-runs/workflow/$ZHIJUAN_TEST_RUN/unit.json"
```

读取报告确认 `tests_run>0`、failures/errors/skipped/expected_failures均为0。旧记录中的219是当时计数，新增测试后应增加，不要为了匹配219删除用例。

### 2.2 既有前端纯逻辑与构建

```bash
node --test tests/frontend_stage_year.test.mjs \
  tests/frontend_section_scope.test.mjs tests/frontend_scoring.test.mjs
cd apps/web
npm run build
```

当前这三个Node文件合计6个顶层用例。构建成功不替代浏览器。保留输出和各自退出码，不用一个最后命令的退出码掩盖前面失败。

### 2.3 PG现有集成

现有 `tests/integration/test_generation_job_postgres.py` 与 `test_workflow_integration.py` 合计8项；后者会代替生成配置为“已齐备”，所以不能用它证明真实依赖已运行。

运行前要求：

1. 创建并记录一个新的专属测试数据库/schema；确认不是 `zhijuan_local` 和其他项目库。
2. 内部注入 `DATABASE_URL` 与相同的 `ZHIJUAN_TEST_DATABASE_URL`；不打印DSN。设置 `ZHIJUAN_SKIP_DOTENV=1`，清空模型凭据。
3. 对该专属范围执行003/004，以及本轮新增迁移。先断言current_database/current_schema和表归属。
4. 不启动消费该测试DB的真实模型Worker；T2使用独立fake环境，不复用日常broker vhost。
5. 运行 `.venv/bin/python -m unittest discover -s tests/integration -v`，并用计数runner记录tests/failures/errors/skips。缺DB导致skip不能算通过。
6. 清理只允许本轮创建且已核对前缀/归属的测试数据；日常current、费用账本和用户上传不可清理。

## 3. 新增测试应放在哪里

| 建议文件（待创建/扩展） | 职责 | 不能做的事 |
| --- | --- | --- |
| `tests/test_generation_configuration.py` | 继续检查配置状态与错误原因 | 不把配置True替代实际心跳 |
| `tests/test_runtime_readiness.py` | 只读探测、超时、缓存、错误环境心跳 | 不访问真实模型 |
| `tests/test_live_budget_proxy.py` | 原子限额、旧账延续、预算状态只读 | 不重新定义旧账为零 |
| `tests/test_generation_pipeline.py` | Worker/状态机直接行为 | 不伪造端到端证据 |
| `tests/integration/test_runtime_readiness.py` | 新心跳表、DB/schema绑定、过期 | 不碰日常库 |
| `tests/integration/test_queue_runtime.py` | 真实broker/worker+fakeHermes、故障窗口 | 不带官方key |
| `tests/frontend_scoring.test.mjs` | 逐题分值、契约转换、上限、不变性 | 不用新算法“修正”原题分值 |
| `tests/frontend_runtime_state.test.mjs`（如抽出纯状态逻辑） | 按钮原因、未知结果恢复决策 | 不通过静态源码字符串断言假装行为测试 |
| 浏览器用例 | 教师实际操作、刷新、网络错误、最终题目状态 | 不把构建当E2E、不读React隐藏状态作为唯一证据 |

优先复用unittest、MockTransport、现有fixtures与直接调用参数。假Hermes只用于测试环境，不能成为生产默认fallback。为测试增加全新测试框架前先看现有依赖与必要性。

## 4. 假Hermes/假费用出口的最小协议

为T2准备一个测试HTTP服务，拥有和实际适配器一致的窄路由：

- POST `/v1/runs`：生成唯一run_id并记录受理次数、role、task_ref的测试映射；返回202。
- GET `/v1/runs/{id}`：按用例返回running/completed/failed；完成时必须包含真实适配器要求的run_id、完成标志、output字符串和usage结构。
- POST `/v1/runs/{id}/stop`：记录请求并返回停止状态；可配置为“停止失败”验证不伪造取消成功。
- 支持测试开关：受理前断开、已受理后丢响应、状态轮询超时、错run_id、非JSON、缺字段、进程退出、延迟完成。
- author fixture从项目样例构造，local_id、题型、score、rubric与冻结slot一致；solver fixture仅接public投影。fixture结果只代表管线行为。
- 每个用例计数 `POST runs`、`GET runs`、`stop`、上游付费桩调用次数；不要只断言HTTP状态。
- 同时保存PG job/outbox/results前后计数和revision。模型调用次数、数据库写入次数和页面事件数量应能对齐。

所有路由仅监听loopback/专属测试网络，测试结束后只停本轮服务。不把任意命令/数据写权限暴露成测试API。

## 5. R组：配置、真实就绪与日常入口

每项记录前置状态、实际操作、HTTP、组件状态、数据库/模型副作用。

| ID | 前置和步骤 | 必须断言 | 失败意味着 |
| --- | --- | --- | --- |
| R01 | 清空所有生成变量，只给假的DeepSeek Key；GET health和readyz | configured=false、ready=false；原因包含DB/队列/网关缺失；0模型请求 | 把Key存在当系统可用 |
| R02 | env全填合法fixture，但Worker未启动 | configured=true、ready=false、WORKER_UNAVAILABLE；按钮禁用；无收费调用 | 仍只检查字符串存在 |
| R03 | 正确DB可用，broker连接地址不存在 | 草稿GET200；生成预检失败且有BROKER_UNAVAILABLE；不能整页“草稿读取失败” | 错把局部依赖故障扩散至全部功能 |
| R04 | 专属测试DB断开，broker/Worker健康 | 不能用seed冒充原草稿；保存有明确错误；无新job/outbox | 数据丢失被掩盖 |
| R05 | Worker连测试库A，API连测试库B，broker相同 | API拒绝以A心跳宣称B就绪；没有向错误环境派发 | 配置错配会吞任务 |
| R06 | Worker心跳刚过期边界前/后各一次；模拟时间或DB时间 | 阈值内通过、超时失败；旧缓存不无限延续；恢复后重新通过 | stale绿色状态 |
| R07 | 只有调度器活着/只有Worker活着各一次 | 两种情况都不能完整就绪；原因精确区分 | outbox无人处理仍允许收费受理 |
| R08 | author URL401、solver URL401、solver上游断开分开测 | 各组件失败；不以403/404当健康；不回显内部key | 探测不真实或泄露 |
| R09 | author与solver配置为同一入口（含尾斜杠变化） | isolation失败，收费POST不执行 | 假隔离 |
| R10 | 预算接口超时/坏JSON/缺必要字段 | fail-closed，明确预算不可核对；不能按无限或0已花处理 | 预算绕过 |
| R11 | 连续100次只读health、当前job、SSE订阅/重连 | 上游调用数和budget.calls都不变，job/outbox/results不增加 | GET产生副作用 |
| R12 | 服务恢复后点击“重新检查”，保留23题编辑草稿 | readiness更新；不刷新覆盖草稿，不自动POST生成 | 状态检查丢用户输入/擅自收费 |
| R13 | 核对浏览器实际请求地址 | 日常3000请求8000；API/Worker/dispatcher指向同日常环境 | 验收另一套端口冒充交付 |
| R14 | Worker模型遗漏而回退默认值、Hermes模型与proxy名单不一致、baseURL多拼一层/v1分别测试 | 非就绪并指出模型/路由不匹配；不通过创建收费Run探活 | 错模型/错路径直到收费时才发现 |

探测时间验收：为每组件设明确超时；断开服务时API应在总预检时间预算内返回。记录实测耗时和阈值；不要求未知环境固定毫秒级性能，也不能无限等待。

## 6. B组：预算、计费和整卷预检

所有金额边界先对fake上游做，不用真实模型制造超支场景。

| ID | 操作 | 必须断言 |
| --- | --- | --- |
| B01 | 空临时账本受理一次有效请求，fake上游检查账本时点 | 上游函数运行前已存在RESERVED行且计数增加；失败也保留 |
| B02 | 两个线程/进程并发超过剩余额度请求 | 受理数不超MAX_REQUESTS或金额上限；拒绝请求上游计数0；不能重复扣同一幂等租约 |
| B03 | 受理后fake上游超时，重启proxy再查询 | RESERVED/UNKNOWN及预留仍在；不退款、不清零、不自动重发 |
| B04 | 旧账本16次/16元迁移到新路径或新金额单位 | 所有历史行和累计额度等值保留；旧文件有备份；新服务不能当空账本 |
| B05 | 旧限额20次已用16次，尝试23槽计划 | 在创建收费任务/上游请求之前拒绝，说明至少46次与余量4次不匹配 |
| B06 | 预算预检刚通过，另一请求消耗余量后再提交 | 最终受理重新检查；不能超限；无租约时不得承诺一定完成 |
| B07 | 缺usage/负数/布尔值usage、伪造模型自报费用 | 不将其作为可信消费0或结算退款依据；UI未知/部分已知 |
| B08 | 非允许模型、tools、流式、超大body、错误token | 在reserve前拒绝；累计计数不变；错误不回显敏感请求体 |
| B09 | 连续读取models/budget/health | 不预留、不调用官方Chat Completions；models静态返回不能作账本证明 |
| B10 | 新价格/上界算法无法验证，或配置币种错误 | 拒绝收费启动，不临时猜汇率/单价 |
| B11 | 如实现微元预留：极小金额、边界舍入、并发、溢出、旧元转换 | 向保守方向舍入；整数/Decimal；不能出现负余额、float累计误差或少预留 |
| B12 | 取消后仍收到上游usage/完成 | 保留实际费用与run_id；不能因为用户取消就把请求费用清掉 |

费用报告必须区分“上限、预留、已报告tokens、已核对账单费用”。旧16元只是保守预留。除非本轮确实读取并核对官方账单，实际费用仍未知。

## 7. J组：持久受理、重复消息和版本

| ID | 前置/操作 | 必须断言 |
| --- | --- | --- |
| J01 | 无plan或未确认plan，POST start | 拒绝；job/outbox/upstream计数均不增加 |
| J02 | 无If-Match、旧ETag分别POST | 分别428/412，0副作用；不把二者都包成泛化400 |
| J03 | 同plan并发8次start | 返回同一job_id；当前job1条，初始dispatch事件1条；只有一个Worker实际领取 |
| J04 | 同版本已经COMPLETED/CANCELLED/FAILED再重放原start | 返回既有任务身份/明确既有终态，不重新付费；合法新计划才产生新job |
| J05 | 活动job为RUNNING/PAUSED/RECONCILING时重拟同spec计划 | 事务内拒绝或按已审批协议处理；不能悄悄更换plan让旧结果入当前 |
| J06 | 请求先读旧confirmed plan，另一事务保存新plan，随后create | repository二次核对拒绝；不得只相信service层第一次读取 |
| J07 | spec在生成中修改 | 旧任务取消/失效；迟到结果被CAS和spec fence拒绝；旧数据保留为历史 |
| J08 | spec相同、plan不同，查询current job/candidates/validation | 不返回旧plan结果；底层历史仍存在 |
| J09 | current job被新终态后的新plan替换 | old run_refs及结果可按old job查询/审计；不丢外部运行身份 |
| J10 | API在写job与outbox之间模拟异常 | 两者同事务回滚，不能出现有job无outbox或反之 |
| J11 | broker已接收但mark_dispatched前杀调度器，再恢复 | 同job_id可重复投递；同slot付费受理总次数不增加 |
| J12 | 两个Worker同时处理同一消息 | 只有成功CAS者进入author；另一个退出；不得两个上游POST |
| J13 | QUEUED后、Worker执行前取消 | generate函数调用0、结果0；取消状态持久 |

每项用例结束核对PG结果，不只看HTTP返回。只对本轮专属测试数据执行清理。

## 8. F组：故障、取消、暂停和未知结果

| ID | 注入点/步骤 | 期望恢复路径与副作用 |
| --- | --- | --- |
| F01 | author POST发送前模拟取消 | 不构造/不发请求；费用计数0；任务取消 |
| F02 | author已受理但HTTP响应丢失 | UNKNOWN/RECONCILING；不自动发第二POST；保留本地task_ref和未知账本 |
| F03 | 已获run_id但落库事件抛异常 | 尽力stop，UNKNOWN；不能开始solver；不能重开author |
| F04 | GET状态第一次超时，第二次成功 | 继续轮询同run_id；POST受理次数仍1 |
| F05 | GET返回缺run_id或其他run_id | UNKNOWN并阻止结果采纳；不得“容错”当成功 |
| F06 | 完成响应途中取消，或完成事件回调触发取消 | 重新检查取消；不写迟到结果、不标COMPLETED |
| F07 | author JSON语法错/契约错/本地ID不匹配 | 明确失败；solver调用0；原失败计费记录保留 |
| F08 | author结构正确但题槽分值/rubric检查FAIL | 保存失败检查或明确失败状态；solver调用0；不改题目分值换通过 |
| F09 | author完成后、solver前停Worker | 恢复进入对账路径；不得重新author；只有有足够可信证据时执行尚未受理阶段 |
| F10 | solver已受理后杀Worker再重启 | 保留solver run_id；不重发solver；任务RECONCILING等待原运行核对 |
| F11 | 结果落库前取消/修改规格/修改任务version | complete_slot拒写；没有当前版本污染 |
| F12 | 结果落库成功后浏览器断网、重开页面 | 从GET恢复已保存结果；author/solver受理次数不增加 |
| F13 | 暂停发生在槽PENDING | 不启动新槽；恢复可以只执行未运行槽 |
| F14 | 暂停发生在AUTHORING，之后点恢复 | RECONCILING，不直接QUEUED；不能把暂停当无成本重新生成 |
| F15 | 上游stop请求失败 | 页面“已请求停止/待对账”；本地拒迟到写入；不宣称上游计费已立即停止 |
| F16 | Worker长时间无新状态，触发reconcile_stale | 改为RECONCILING且不自动重新派发收费阶段；长任务正常更新时间不被误判 |

上述异常用fake服务确定性注入；不要通过切断真实付费网络反复制造未知账单。

## 9. S组：隔离、候选完整性与检查证据

| ID | 操作 | 必须断言 |
| --- | --- | --- |
| S01 | 在public顶层、children、options/block嵌入private/answers/rubric等字段 | solver入口全部拒绝，上游solver调用0 |
| S02 | 请求其他session/任意路径/其他provider或model | 404/400/鉴权失败，无开放代理行为 |
| S03 | 在author专属临时目录创建无敏感内容canary，在solver尝试读 | 文件/挂载/权限隔离真实阻止读取；不只检查prompt没写答案 |
| S04 | 检查容器mounts、HOME、HERMES_HOME、工具集、网络与内部token归属 | author/solver无共享可写私有卷；solver不持author token/上游官方key |
| S05 | author省略答案或评分点、负分/小数score_x100、ID冲突 | 契约/规则失败；不自动补A、不截断/重写分值 |
| S06 | 修改题面/答案/评分/材料/版本后再用旧检查 | 旧content/evidence指纹不适用，必须重新检查或REVIEW |
| S07 | 只改变blind_evidence | content_hash不变，evidence_hash变化；不能事后追加未绑定证据 |
| S08 | 两个模型答案一致，但没有可信数学证明 | 允许REVIEW，不能据此直接PASS |
| S09 | 不支持共享材料或材料未解析 | 明确拒绝且尽早阻断；不把私有材料塞给solver |
| S10 | 学生视图/导出观察（若本轮涉及） | 公开投影无答案字段；仅界面隐藏不算学生API安全验收；未测则NOT_RUN |

## 10. U组：前端真实操作与用户本次问题回归

浏览器动作必须使用项目可用的浏览器工具。读取真实DOM/界面，不只通过修改React内部变量证明通过。用户当前草稿先保护；破坏性/写入性场景用独立测试环境。

### U01：当前23题150分模板完整链路

1. 经授权后使用 `uploads/source-docx/2023-2024学年人教A版（2019）高中数学必修第一册期末综合测试卷.docx` 做人工指定的真实规则解析；常规离线套件使用合成 fixture，不读取用户上传试卷。
2. 确认4类题：10单选×4=40、3多选×4=12、4填空×4=16、6解答12+14×5=82，共23题150分。
3. 页面分值核对应显示150/150，不显示140，也不把总分改成140。
4. 真正点预览；观察PUT规范spec→POST plans/generate均成功，DB中的题型分组合规；23个slot总和15000，最后6个仍1200、1400、1400、1400、1400、1400。
5. 刷新/回读验证分值和题数不丢；不能仅让前端临时显示150。
6. 计划仍未正式启动模型；没有生成job/outbox或费用增加。

### U02：错误分值仍被阻止

用24题配23条item_scores、item_scores总和与section_total不一致、负数/小数score_x100、全卷差1个score_x100单位分别测试。

必须有具体说明（哪种矛盾、实际/目标/差额），保存/计划请求不应静默改数据；不能以“0.5分容差”通过。导入失败不能清掉教材和89项选择。

### U03：全书范围与契约上限

全书选择89项，检查规范转换每组topics<=30且所有选中项仍能在规范组的并集中找到；item顺序/分值/题数不变；不超过30组。构造超过容量的输入时必须明确拒绝，不能取前30项冒充保留全部。

这只证明结构/范围保留，不证明89项都是合适知识点。章节标题和跨学段遗留需另过U04。

### U04：切教材/学段不能带入旧课程范围

先选九年级数学4个旧考点，再切高一人教A版必修第一册；应明确提示旧范围处理，并要求重新确认。用户选择清除旧学段范围后，23题计划里不得出现原九年级4个考点；选择保留某手动项时必须可追溯，不静默删除。无年级维度的高中“第一册”不能擅自把已选高二改高一。

### U05：草稿和页头同步

切高一、导入150分120分钟模板。页头、规格明细、底部汇总都应是同一份草稿，不得仍显示九年级100分90分钟。手动修改标题时不得被慢初始化请求、就绪轮询或热更新覆盖；校验失败后的所有输入保留。

### U06：预设与自定义模板

逐个选择小测/月考/期末，核对卡片声明题数、实际sections计数、时间、总分一致；现有小测3+2+1应是6题，不能仍显示5题。套用23题模板后标明自定义模板，不能冒充11题月考；再切预设有明确替换行为，相关范围/确认状态合理失效。

### U07：禁用原因与恢复

分别制造配置缺失、Worker过期、broker断开、预算不足、计划过期、范围未确认、启动结果未知。按钮附近必须有对应中文说明和可执行的下一步，屏幕阅读器能通过描述关联读取。只读重新检查恢复后使能，不要求用户重填模板；使能本身不得POST收费任务。

### U08：点击一次、双击、刷新和多标签

同plan快速双击、键盘连续确认、两个标签并发确认，计数必须是一个job、一份初始outbox和每阶段一次受理。POST期间按钮禁用；刷新或后退返回只读取该任务，不再次启动。

### U09：启动响应未知

模拟API已提交但浏览器没有收到202。页面先GET对账并恢复同job；若仍不能确认，显示启动结果待核实，禁止再POST。区分“明确拒绝没有创建任务”和“可能受理”两类错误。

### U10：SSE与终态

在QUEUED、RUNNING、REVIEW_REQUIRED各阶段断开SSE并恢复，确认事件可重取且无重复槽/费用。分别展示COMPLETED+REVIEW、PARTIAL_FAILED、FAILED、CANCELLED、RECONCILING；不永远转圈、不全部显示完成，不让REVIEW题变成自动发布。

### U11：模板上传工具限制

真实页面上传必须实际执行文件选择和解析。浏览器扩展若拒绝本地文件上传，不绕过权限或把API测试说成浏览器上传通过；记录NOT_RUN并使用用户手动上传完成该段。源Word不修改、不外发其他服务。内部解析若触发模型，必须受同样预算约束；离线验收显式关闭模型增强。

### U12：常用入口的最终核对

所有测试环境通过后，回到用户日常 `localhost:3000`。只读核对网络到8000、当前草稿、真实ready原因、正常已有计划。实际收费确认只能在已批准计划/额度内执行；不为了证明按钮可点擅自开始完整23题。

## 11. O组：资源和“不影响使用”

| ID | 步骤 | 必须断言 |
| --- | --- | --- |
| O01 | generation-only stop，PG/Vite/API保持运行 | 草稿GET/保存/预览依然成功；只有生成状态变为不可用 |
| O02 | 有RUNNING任务时请求停止生成服务 | 默认阻止粗暴停进程，走明确取消/等待/对账；不丢run_id |
| O03 | 重复运行start-generation两次 | 组件只一份，无重复beat/调度器/Worker消费导致重复费用 |
| O04 | 启动中某个新组件失败 | 仅回收本次启动资源，原PG、用户草稿、其他项目服务不受影响 |
| O05 | 原PID已结束、PID被其他进程复用 | 停止脚本拒绝误杀，核对归属失败有说明 |
| O06 | 用模拟Docker清单包含知卷和范围外容器，记录脚本将执行的命令 | 仅对归属已确认的知卷对象操作；不会inspect其他项目配置、读取日志、连接数据库或执行stop/down/prune；无需真的操作zygf |
| O07 | 只记录知卷容器实际内存及必要的Docker总体内存指标 | 实际值和上限分开；不深入分析其他项目进程；不能因牺牲功能满足数字 |
| O08 | PG重启但不删卷，API重新连接 | 原草稿、23题计划、版本和历史恢复；不得回到seed九年级100分 |

## 12. L组：真正调用官方模型的验收

执行前必须同时满足：T0–T3相关阻断项通过；网关隔离检查通过；用户费用授权仍适用；预算账本延续且足够；没有未决收费请求需要先对账。

建议按以下顺序，遇到问题立刻停止扩量：

1. **L01 单题真实链路**：选择一个范围明确、无需共享材料的已支持题型，在专属验收草稿运行。记录真实author/solver run_id、请求前后费用计数、job状态、候选检查、PG结果和页面读取。允许最终REVIEW；必须说明不是教学质量PASS。
2. **L02 小规模多题**：只有额度足够才做2–3题，验证不同题槽的持久化/顺序/分值、模型失败不会污染其他槽。不能通过无限重试筛选成功样本。
3. **L03 完整23题**：旧20次请求限制与当前16次计数不允许直接执行；满足新的明确预算与上界方案之后才能运行。整卷有任何失败就报告失败/部分失败及缺项，不能用单题记录代替。
4. **L04 日常入口验收**：最终真实验收从常用页面发起，确认请求确实走8000与日常批准运行配置。记录当时源码/镜像版本；另一端口的成功单独标注。

每项至少记录：测试规格摘要、题槽数/分值、批准范围、起止时间、job_id、角色run_id、usage已知/未知字段、检查状态、费用账本前后、不包含的验收范围。任何引用外部结果未知必须进入对账，不能靠重新收费“再试一次”。

## 13. 报告格式与完成门槛

建议每个case一行结构化结果：

```json
{
  "case_id": "J03",
  "status": "PASS",
  "environment": "dedicated test DB/schema and broker vhost",
  "command_or_actions": "8 concurrent starts for the same confirmed plan",
  "observations": {"unique_jobs": 1, "initial_outbox_rows": 1, "author_admissions": 1},
  "expected": {"unique_jobs": 1, "initial_outbox_rows": 1, "author_admissions": 1},
  "evidence_refs": ["case-J03.json"],
  "limitations": ["fake Hermes; no official model call"]
}
```

以上只是格式示例，不是现成PASS。status使用PASS/FAIL/NOT_RUN；缺前置、未执行、跳过必须NOT_RUN并说明原因。

### 交付必须逐项回答

- 常用3000→8000是否真的接通？有没有另起验收端口冒充？
- 配置齐全但Worker死亡时，按钮与服务端是否都能阻止新任务？
- 当前23题150分和不等分解答题是否经真实保存/回读仍保持？
- 旧课程范围是否已经清理/确认，还是仍把九年级内容带进高一卷？
- 双击/断网/重复消息/Worker重启各自产生几次上游受理？
- 费用余量能否支持整个计划？预检失败会不会仍产生收费？
- 取消是否仅表示本地取消，还是有真实上游终止证据？是否存在未决账单？
- REVIEW/FAIL是否被准确展示？是否保留未完成发布/重生成边界？
- 关闭闲置生成服务后，用户草稿和预览是否仍可用？其他项目是否完全未动？
- 哪些用例未跑、哪些代码变更发生在旧真实验收之后？
- `progress`与新handoff是否准确，`finish --task`是否通过？

只有这些问题有范围匹配的证据，才可宣称本地真实生成链路交付。未得到完整教学质量、角色权限和发布证据，仍不能宣称整个知卷产品完成。
