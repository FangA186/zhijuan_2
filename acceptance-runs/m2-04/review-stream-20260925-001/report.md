# M2-04 审核修订与真实输出流：局部验证记录

日期：2026-09-25。范围：审核/两轮修订、provider/Hermes/任务API事件传输、教师输出面板。

## 结果与限制

代码实现、104项离线回归、2项前端回归、前端生产构建、200行门禁通过。本机历史任务页面/API和独立模拟SSE页面完成桌面及390px窄屏操作验证。**不是LIVE-QUALITY、完整APP-E2E或阶段签收。**

现有生成容器和Worker尚未更新：Compose重载在配置阶段失败，当前启动环境缺少上游凭据；没有替换现有容器、没有新发模型调用。用户已被询问原有安全配置文件或启动脚本路径，禁止要求粘贴密钥。首个Notion连接返回Authentication required；改用现有可用Notion连接，已创建并回读两条Bug记录，登记同步指纹。

## 行为

- 每个新题槽先命题/规则检查，合格候选进入隔离盲解，再由reviewer审查；不合格候选先审核再修订。
- 修订前持久事务登记额度，最多2轮，新版本重新检查/盲解；不改既定题型、分值、课程范围。外部结果UNKNOWN不重发；审核不能把确定性FAIL变PASS。无数学证明仍REVIEW。
- 修复输出结构失败时允许受控审核取得失败候选/拒绝的最终输出；失败内容不被当作合格结果。不合格结果在原题槽保留，格式持续错误保留私有检查点后失败。
- 原生strict-provider SSE转为Hermes message.delta；适配器订阅events并经主线程版本围栏持久化，供本机教师activity SSE读取。无真实事件不模拟打字；终态输出单独标记。
- 面板显示角色、题槽、修订轮次、正文、JSON详情；支持角色筛选、复制、自动跟随、回看。旧任务无历史输出明确提示，不回填伪造内容。
- 公开进度API仍排除activity/run_refs；带答案流仅在环回地址本机教师路由。私有推理不采集，工具参数/凭据不转发。尚无生产身份鉴权验收。

## 验证命令

```sh
.venv/bin/python -m unittest tests.test_review_workflow tests.test_activity_stream tests.test_native_stream_transport tests.test_hermes_runs_transport tests.test_generation_pipeline tests.test_workflow_safety_closeout tests.test_hermes_adapter tests.test_diagram_assets tests.test_live_budget_proxy tests.test_strict_json_output tests.test_slot_failure_diagnostics
node --experimental-strip-types --test tests/frontend_slot_diagnostics.test.mjs
npm run build --prefix apps/web
.venv/bin/python tools/check_code_lines.py
```

- tests.log：104 tests，OK，无skip。覆盖多选修订、格式错误、两轮上限、版本绑定、新盲解不含答案、原子额度重放拒绝、未知调用不重试、真实SSE分块先于终态、隐藏推理排除、本机权限、私有进度隔离、刷新快照重放。
- frontend-tests.log：2项通过，逐题诊断与终态汇总。
- build.log：tsc与Vite成功。
- lines.log：0 maintained files exceed 200 lines。
- regression-initial.log：保留首次旧测试失败记录；旧2角色mock补充reviewer契约，非法结构由返回FAIL改成三轮后抛明确失败；没有放宽安全断言。

## 浏览器实测

环境：用户Chrome，本机localhost:3000/与8000 API；当前本机命题教师工作台（角色按钮不是生产鉴权）。

1. 刷新现有23题PARTIAL_FAILED任务。Agent实时输出面板出现，明确显示历史缺片段提示，保留原5题失败与18题待复核。
2. 选择审核角色→只显示相应记录；恢复全部。关闭自动跟随→出现回到最新输出；点击后恢复。点击复制记录→显示已复制。
3. 浏览器网络核对spec、current、activity、questions、validation均HTTP200；见network.json。console.json无错误。
4. 桌面与390×844窄屏查看实际页面；曾发现提示条shrink-0导致8px溢出，修改为窄屏纵向排列后复核scrollWidth≤innerWidth，无输出面板横向溢出。截图desktop.png、mobile.png。
5. 启动tests/browser/review_activity_fixture.py（明确标注模拟事件/无模型调用），浏览器打开临时review-activity-test.html。初始仅第一段命题JSON，随后出现审核建议、修订及新盲解，终态可回看；展开事件JSON、审核筛选、刷新重放；桌面及390窄屏通过。fixture-desktop.png、fixture-mobile.png。该夹具不是实际模型进度，不写用户数据库；验收后服务与临时HTML已移除。

## 不变量逐项

| 不变量 | 当前证据 |
| --- | --- |
| Hermes唯一框架；不旁路provider | 保留Runs入口，底层代理仍为固定DeepSeek出口；离线调用路径通过，真实调用未测 |
| 命题与盲解隔离 | 公开输入回归通过；隔离网关只新增认证GET events，禁止额外路径/私有输入；运行容器新版本未验证 |
| score_x100与题槽约束 | 原检查器保持；不合格审核不能豁免，回归通过 |
| 新版本旧证据失效 | 每轮revision/hash变化，修订后新盲解；单元通过，真实PostgreSQL并发未测 |
| Agent无权审批/预算扩张 | 审核只返回意见；原子额度最多2，UNKNOWN不重发；预算账本仍保留 |
| 学生投影无答案 | 公共进度排除活动/检查点；新增本机教师路由，离线权限测试通过；生产身份未完成 |
| 真实用量与进度 | 不回填旧流、不伪造成本，总量未知继续保留未知 |

## 第一题历史诊断

只读查询现有run状态得到failed、completed=false、partial=false、error为空。见first-slot-diagnostic.json；未读取/输出私有推理。历史记录缺失具体原因，不能推断成特定HTTP错误。

## 尚未验证

- 使用原部署凭据重载budget-proxy、两台Hermes、solver-entry和Worker；目前页面/API更新不代表生成进程已更新。
- 授权后的小样本真实DeepSeek流式/审核修订、端到端取消和费用记账。
- 实际PostgreSQL并发/崩溃恢复与生产权限。
- Notion同步已完成：BUG-20260925-001/002；生产模型与运行态限制不受此状态影响。

## Notion回读

- BUG-20260925-001：https://app.notion.com/p/3e5a7a41f60a812d8f61e80d1e90ddf6
- BUG-20260925-002：https://app.notion.com/p/3e5a7a41f60a8145b6a8d5bc230b3f68

标题、状态、根因、修复、代码路径和未部署/未实测边界均已回读。
