# 规划 Agent 接入验证

任务M2-01 / FEAT-PLAN；2026-09-28至29。状态：实现已接入，OFFLINE_PASS / 隔离数据库与浏览器流程通过；LIVE-QUALITY未验收，M2-01仍IN_PROGRESS。

## 实现
通过已有Hermes planner角色与exam-planner Skill设计整卷；程序只提供结构骨架和难度配额。模型输出契约包括summary、conflicts和逐题knowledge_ids/cognitive_target/difficulty/design_brief/rationale。程序检查槽位完整、范围、难度配额、栏目误用、重复任务及冲突，再保存未确认蓝图。出题任务冻结并传递设计说明，原命题/盲解/审核链路保留。
规划使用PostgreSQL已有jobs/outbox，但键为planning:current，不覆盖current旧作业；独立Worker路径执行。模型与数据库异常不会用规则计划替代，不自动重试未知计费请求。前端显式启动、持续读取实际活动、刷新恢复、停止、设计说明预览和教师确认。旧配置页的自动重算改为仅失效计划，不因改范围调用模型。

## 检查证据
- tests.log：81项Python隔离回归通过，覆盖模型契约、规划输出拒绝、角色路由、盲解隔离、原生成审核、幂等/取消、HTTP本机边界与旧结果失效。
- postgres.log：3项真实PostgreSQL事务用例通过。在新建一次性postgres:18容器的planner_test库运行，绝不连接zhijuan_local；包括并发入队只一次outbox、Worker保存蓝图且旧卷不变、迟到版本/活动命题阻断、崩溃隔离。已停止该临时容器。
- node-tests.log：7项前端配置/评分回归通过。build.log：生产构建通过。code-lines.log：200行检查。
- 没有真实DeepSeek/Hermes计费调用，没有重载用户已有后台、没有写入用户草稿库。

## 浏览器实测
环境macOS、Codex内置Chromium、命题教师流程；独立Vite3001与真实FastAPI8001、真实PostgreSQL测试库。browser-fixture.html复用生产hook与Actions/Activity组件，前端没有替换API方法。browser_server.py仅替换Hermes为带显著“离线合成”标记的响应、就绪为合成就绪；测试调度线程消费真实outbox并调用生产Worker函数，未使用真实RabbitMQ/Celery投递。因此本次不是完整生产APP-E2E或模型质量验收。

操作与结果：
1. 点击“让规划Agent设计蓝图”，POST返回202；按钮禁用，显示QUEUED/RUNNING，逐段活动可见。
2. 执行中刷新，GET恢复同一任务和输出；没有新POST，planning_outbox_rows=1。
3. 完成后显示23题设计说明、难度和理由；选择“规划”角色筛选。
4. 点击“确认计划并开始命题”，确认接口和生成任务接口通过；数据库回读生成队列QUEUED，23槽、15000分值整数、全部design_brief保留，source=hermes_planner。见browser-db-readback.json。
5. 桌面和390×844窄屏截图desktop.png、narrow.png，窄屏内容宽度384不溢出390；console error为空(browser-errors.json)。
6. 独立重置测试库后再次提交并立即停止排队规划，终态CANCELLED，无蓝图确认入口；见cancel.png。
7. 临时页面与服务已移出应用并停止；用户原始API页面保留。

网络证据见browser-api.log；截图是明确标记的夹具，不可当作真实模型设计截图。

## 不变量/限制
符合：模型框架仍Hermes；教师题量、分值、范围不可被模型更改；单次调用与现有预算代理；成功后仍需教师确认；未知外部结果隔离；命题按冻结设计；盲解仍只接本题公开投影；不访问历史试卷。
保持既有缺口：本机教师授权不是生产多租户权限；共享材料生成未接通，规划前拒绝；题目语义质量、章节权重合理性及真实23题token预算未验收。失败不会冒充成功。当前4096输出token上限不自动提高，较大蓝图可能失败。
用户需按docs/planner-agent.md重载代理契约、Worker及API；重载后第一次真实规划需验收。旧卷与已确认历史计划未重写。
