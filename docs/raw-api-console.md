# DeepSeek 原始响应查看与启动

本次用户要求：调研官方协议，保留并打印原始返回（含 reasoning_content），独立页面展示；后台由用户启动。这里记录2026-09-25调研、2026-09-28收尾结果。

## 协议与当前实现

项目到Hermes用 `/v1/runs`；Hermes经本地预算代理调用DeepSeek的 OpenAI-compatible Chat Completions。当前严格函数封装走 `https://api.deepseek.com/beta/chat/completions`。OpenAI兼容描述的是HTTP/JSON协议，并非调用OpenAI模型。

- 流式字段分别是 `choices[].delta.reasoning_content`、`content`、`tool_calls`；非流式位于 `choices[].message`。本页原样保留响应体，解析区只作并排阅读。[官方流式样例](https://api-docs.deepseek.com/zh-cn/api_samples/thinking_mode_api_example_streaming/)
- thinking通过 `thinking.type=enabled` 开启，effort用high。SDK的extra_body只是参数传递方式，HTTP请求体直接放thinking。[思考模式](https://api-docs.deepseek.com/zh-cn/guides/thinking_mode/)
- 思考模式支持工具调用，但不能用required或指定函数强制调用；因此诊断开启thinking时使用tool_choice=auto。[Chat Completions参数](https://api-docs.deepseek.com/zh-cn/api/create-chat-completion/)
- Chat Completions无状态，调用方要维护messages；带tools的后续请求须保留历史assistant消息中的reasoning_content以及tool_calls/tool结果关联。现有知卷并未实现通用工具循环，return_exam_json仅是输出序列化封装，不会执行外部工具。[多轮对话](https://api-docs.deepseek.com/zh-cn/guides/multi_round_chat/) [工具调用](https://api-docs.deepseek.com/zh-cn/guides/tool_calls/)

## 抓取位置与页面

`raw_api_capture.py` 在DeepSeek返回进入转换器前保存SSE行，包括注释、换行、[DONE]及原始JSON，不把reasoning_content删掉。普通命题页面继续显示经过转换的业务结果；本页区分deepseek-upstream与hermes-adapter，后者不冒充供应商原始响应。现有Hermes结果采集也保留，但独立标记来源。

页面：<http://localhost:3000/raw-api.html>。沿用Vite `/v1` → FastAPI `8000`，无需另起8768服务。数据落在`.runtime/raw-api/responses.ndjson`，单文件64MiB上限会明确记录停止采集；归档并清空保留旧文件。请求Authorization/密钥不采集，响应体按本次明确授权保留。仅环回本机请求可读。

## 用户启动

先等待当前命题结束。项目已有Docker服务与.env是前提；脚本复用已有容器凭据，不打印或写出凭据，不发起模型调用。

```bash
cd /Users/fangzengxing/zhijuan_spec_v1_4
.venv/bin/python tools/raw_api_console.py start --thinking enabled
```

该命令只重载budget-proxy，开启原始抓取及thinking；网页继续通过8000读取文件。若8000 API未运行，另开终端：

```bash
cd /Users/fangzengxing/zhijuan_spec_v1_4
.venv/bin/uvicorn services.api.main:app --host 127.0.0.1 --port 8000 --reload
```

随后在知卷手动发起一次生成。实时终端打印位于代理容器的stdout，可另开终端查看：

```bash
docker logs -f --since 0s zhijuan-workflow-20260922-live-budget-proxy-1
```

不启用思考、只观察原有协议时，将start参数换成`--thinking disabled`。停止日志跟随用Ctrl-C；等任务结束后关闭抓取并恢复非思考配置：

```bash
cd /Users/fangzengxing/zhijuan_spec_v1_4
.venv/bin/python tools/raw_api_console.py stop
```

若另有正在运行的题槽或结果待对账，脚本拒绝重载。不会重新创建费用账本或自动重发请求。思考模式仍使用当前输出上限；若出现length/错误，查看实际结束原因，不代表已得到合格题目。

## 验证边界

测试使用隔离环境和临时文件。已验证SSE原文/换行保留、reasoning与工具参数拼接、来源分离、断线游标、归档、访问边界以及页面布局。未执行本轮start/stop或真实思考模式调用；启动命令由用户执行。浏览器读取到已有历史上游记录，其thinking=disabled；这不是本轮新发模型调用。
