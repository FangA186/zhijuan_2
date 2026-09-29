# 评分模式与答案一致性修复验收

开始于2026-09-24，完成于2026-09-25。用户明确授权修复。主任务M2-03，涉及M1-05规格与M2-02盲解私有字段隔离。执行者Codex。

## 改变

- Answer新增exclusive/additive模式。新版选择/判断题使用互斥档位，rubric为空；全对按题分、少选按教师配置、错选或空答0分。不把4/2/0相加。
- 解答题及兼容旧答案仍使用累加采分点，正数及合计约束不放宽。新规格不能用additive绕过教师少选政策。
- 配置页面新增“多选题少选且无错选得分”，默认0，须小于所有多选题满分。前端canonical字段白名单、后端schema/验证/冻结快照都保留该值；修改后旧计划失效。
- 教师卷、旧编辑页和导出预览共用评分组件。答案与评分描述从结构化正确选项派生；移除页面写死的5分。学生预览只显示公开计分规则。
- 明确的选项答案声明冲突新增ANSWER_TEXT_CONSISTENCY FAIL，不能从说明里擅自覆盖答案。解析仅处理边界明确的选项列表，不宣称能证明任意自然语言的一致性。数学正确性仍REVIEW。
- 检查器版本6；评分变化进入content_hash。新私有评分字段不能进入盲解public输入。

## 历史两题

独立v2修订草稿见repairs.md、q11-repair-draft.json、q13-repair-draft.json。历史第11题题面/答案保持，改4/2/0互斥；历史第13题依据集合包含关系复算补A成为A、C并统一解析。结构、评分、显式答案一致性检查通过，两次真实隔离盲解均一致，最终仍REVIEW。

草稿标记DRAFT_NOT_APPLIED，未覆盖原历史FAIL、未写回旧generation_job_results或审批。现有持久化版本化编辑API尚未接通，不能绕过它；本轮交付代码修复、可复核草稿和真实新生成结果，不冒充旧卷已原位替换。

## 验证结果

| 项目 | 实际结果 | 证据 |
|---|---|---|
| 后端全量离线 | 438通过，零skip | offline-final.json / offline-final.log |
| 评分/完整性定向用例 | 14通过，含4/2/0、零分累加拒绝、teacher policy、明确声明冲突、歧义不猜、hash变化、私有字段隔离 | scoring-tests.log |
| 前端全部Node用例 | 23通过，含实际saveExamSpec方法往返和公开投影 | frontend-tests.log |
| 前端构建、200行门禁 | 通过 | build.log / lines.log |
| 实际盲解入口负向检查 | 两个新增私有字段均400，上游调用增量0 | private-field-rejection.json |
| 历史修订草稿再检查与盲解 | 两题结构/评分/一致性PASS，盲解一致，整体REVIEW | repair-checks.json / repair-blind-checks.json |
| 最终4/2/0真实整卷 | 23槽处理完成，19 REVIEW、4 FAIL；新多选答案均exclusive/partial=200/rubric为空 | latest-job.json / scoring-results.json |
| 最终源代码重查当前已保存结果 | 20个候选状态与content_hash均与已存记录相同，未写数据库 | recheck-current.json |

## 实际浏览器

Google Chrome，localhost:3000 → localhost:8000，命题教师。桌面和390×844窄屏：

1. 新建试卷进入配置；输入少选4分（等于题分），页面与预览动作明确阻止；改2分重新确认范围，保存/预览计划正常。
2. 首次发现canonicalKeys遗漏：界面2分被后端默认0。200断言失败后修白名单，新增真实方法mock-fetch往返回归。zero-policy保留首次0分试验；未把它称为4/2/0通过。
3. 修复后先GET核对保存值200，再通过“确认计划并开始命题”真实启动。完成后教师卷三个多选区域均显示4/2/0，且明确“只计一档，不累加”；错误答案数据仍有警告。
4. 学生预览没有私有评分区域，公开少选规则为2分；公开投影单测确认不携带private/correct_option_ids/新私有字段。这不是独立学生身份API安全全量验收。
5. 教师导出预览与教师卷共用相同档位；本轮未实际打印或导出PDF/Word。
6. 刷新恢复任务后返回配置，input值仍为2，API值仍为200。config-desktop/mobile与teacher-scoring-desktop/mobile为最终截图。浏览器本轮error为0。

网络缓存部分早期事件已淘汰，network.json明确truncated=true，仅作为部分请求证据；字段真实持久化另由input-spec.json与浏览器刷新值佐证。

成卷页滚动时固定打印工具栏会覆盖顶栏按钮坐标；自动化回到页顶后正常进入配置，未将定位超时当作评分功能失败。旧编辑页共享组件仅编译/单测覆盖，未独立浏览器走入口。

## 本轮仍失败的题

以下是新生成一轮的题，与历史修订草稿的同编号题不同：
- 新第2题：题面有空文本块，STRUCTURE/minLength失败。
- 新第11题：多选答案只给了一个正确选项，仍被ANSWER_AND_RUBRIC拦截。4/2/0模式本身合法。
- 新第19、23题：答案对象含未声明额外字段，STRUCTURE/additionalProperties失败。

这些问题未通过放宽规则、自动修改模型答案或重复抽样掩盖。23槽处理完成不等于整卷合格。当前工作台保留少选2分配置与这轮真实结果。

## 边界

未公开发布、审批签收、原位覆盖历史结果、提交推送或清理数据库。未实现通用失败题多次重生成。配置修改形成新规格/计划，旧证据仅在原版本有效；本次不代签MIN-06/FULL-06等完整教学验收。决策见DEV-018。
