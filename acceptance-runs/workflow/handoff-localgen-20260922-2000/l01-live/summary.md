# L01 单题真实链路运行摘要

- 第一次运行在受理链路中止（plans/generate 响应无 ETag 的工具缺陷），未消耗任何额度（账本仍 16/16）。
- 修复后第二次运行成功：作业 COMPLETED；真实 author run `run_c0160ba73ee8494a84c416e7a322a089`（5535 tokens）与真实 solver run `run_d514037dfe3543b4ba3bfbb2592ff95f`（1271 tokens）均 completed；validation=REVIEW（无可信数学证明，待教师复核）；slot single_choice/100 分/整数四则运算。
- 账本：16 → 18 次调用、16 → 18 元保守预留（+2/+2），0 未决；实际官方账单仍未核对（未知）。
- 环境：专属验收库 zhijuan_accept_w6 + 8020 临时 API + 验收 vhost；日常草稿库零接触（version 12、jobs=0 不变）。
- 工具缺陷修正两处（ETag 取用、ok 写入顺序），证据 JSON 附说明；run_id/结果行保留在测试库可复核。
- 边界：单题真实链路不构成教学质量验收，不代表完整 23 题；REVIEW 不得自动转 PASS。
