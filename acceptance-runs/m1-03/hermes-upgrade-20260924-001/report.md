# Hermes v0.21.5升级与验证

2026-09-24，用户明确要求升级并验证。执行者Codex。主范围M0-04/M1-03，涉及M2-02隔离运行环境。

## 生效版本

- 官方稳定标签：v2026.9.24 / 0.21.5。
- 锁定源码：f97608f178d1ffeca59860195ab7da295f7c8e5f；vendor干净、detached HEAD。
- 最终镜像：sha256:25f3374666b543fa94810427215c04b1fd7d570d5216dc61d7574fe39a495bc6。
- 作者和盲解实际运行均为该镜像/0.21.5，独立状态卷，uid10001，api_server工具集为空。
- Python3.12运行Hermes，业务Python环境保持独立。MIT许可及来源、依赖文件哈希更新到install/hermes-source.lock.json。

## 升级中的兼容处理

1. 新interrupted状态不当普通FAILED继续出题，而映射UNKNOWN进入对账。单测确认不重复受理。
2. 初次真实探针暴露自动标题额外调用：两次业务阶段产生四次上游请求。关闭auxiliary.title_generation.enabled及model_upgrade_enabled后，整卷实际计数与业务阶段/已知格式恢复吻合。
3. 关闭框架api_max_retries及auto_recovery_cycles，避免新自动恢复循环叠加已批准的格式恢复。未改变数学、分值、审批判定。
4. 保留DEV-016的严格结构化出口和最多一次已完成坏格式恢复；没有借升级移除现有保护。

## 检查结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 官方标签/提交、镜像构建 | 通过；构建上下文只含跟踪的Hermes源码及3个构建输入，无业务数据或.env | source-lock-before.json / build-context.json / build-final.log |
| Python依赖一致性 | pip check通过 | dependency-check.log / hermes-dependencies.json |
| 新版原生修复冒烟 | 在无网络、无密钥容器中验证嵌套JSON修复、字符串截断不猜补、运行中断状态 | native-smoke.py / native-smoke.log |
| 项目全量离线 | 432项通过，零跳过 | offline-final.json / offline-final.log |
| 兼容与隔离重点回归 | 19项通过 | compatibility-final.log |
| 源码200行门禁 | 通过 | lines.log |
| 实际HTTP负向隔离 | skills接口404；作者会话/答案字段400；付费调用增量0 | isolation-http.json |
| 实际版本、身份、工具及自动调用配置 | 双服务0.21.5、uid10001、工具集为空、自动标题/恢复关闭 | runtime-final.json / runtime-version-tools.json |
| 真实整卷 | 23/23处理，21 REVIEW_REQUIRED、2业务FAIL | live-full/summary.json / per-question.json |
| 实际模型与运行状态 | 44个Hermes阶段均completed，44个runtime均deepseek/deepseek-flash | live-full/runtime-attribution.json |
| 上游请求与格式 | 45次：44个有效结果、1次坏格式被一次恢复；未决0 | live-full/transport-results.json |
| 实际浏览器桌面/390×844窄屏/刷新 | 展示本轮21待复核、2失败，恢复原视口；本轮console error为0 | live-full/page.txt / desktop.png / mobile.png / console-errors.json |

第一题盲解状态查询发生一次读取超时；同一run只读轮询恢复，未重复POST，随后整卷完成。不能把最初就绪200等同于完成验收，故继续核对了全部44个运行结果。

## 两道业务失败

- 第11题：评分项为400、200、0（score_x100）；0分不符合当前正整数评分项约束，且按当前加和规则合计600不等于题槽400。见live-full/q11-detail.json。业务规则尚未支持把这些评分项解释为互斥计分分支。
- 第13题：多选题只有1个正确选项；评分项合计600、题分400，不符合当前规则。与JSON语法或框架升级失败分开记录。

其余21题仍为REVIEW，不表示数学正确性或教师审批通过。

## 数据与回退

旧镜像sha256:3c0a3ff6194200c92346a11a633588c997db071a11e27002d0a61b3296cd7654已保留并增加rollback-20260924标签；旧author-state/solver-state卷保留。新版用author-state-v20260924/solver-state-v20260924卷，未读取或打包旧私有会话，无业务库迁移或清理，费用账本继续沿用。

旧run记录留在旧卷，不迁入新网关；知卷候选/检查等业务记录未删除。回退时空闲停止Worker，在原Compose恢复旧image和旧卷引用，恢复source-lock-before.json对应源码，再启动验证；见compose-before.yaml和runtime-before.json。

## 限制

升级和技术链路通过不等于题目质量通过。未公开发布、导出PDF/Word、提交推送；未执行真实在途付费任务的破坏性中断测试，采用原生无网络模拟及适配器回归。

底层SQLite 3.46.1触发Hermes安全检测，框架自动使用DELETE journal而不启用受影响WAL；未放宽该保护，也未升级系统SQLite。警告保留在native-smoke.log，不隐瞒或当成测试失败。业务PostgreSQL不受该配置改变。

决策：docs/decisions/DEV-017-hermes-v0215-upgrade.md。

记录门禁补充：M0-04全目录自动快照超过工具文件上限，改用显式变更文件哈希及干净vendor的Git提交/tree身份记录；M0-04、M1-03、M2-02的finish门禁均通过。此门禁仅验证记录闭环，不代签产品验收。
