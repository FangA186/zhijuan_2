# 原始API返回页：调研、实现与验证

日期2026-09-28，延续09-25未交付的原始流请求。范围M1-03受控Adapter/协议诊断；不代表整个M1阶段完成。

## 交付

- 已有独立raw-api.html页面继续沿用，当前接现有8000 API与Vite /v1代理；保留并适配其他会话的http_runner拆分、raw_api_routes集成和Hermes结果采集，没有回退这些修改。
- DeepSeek响应体在strict输出转换之前逐行记录，思考字段、content、tool_calls、未知字段与原始换行保留。请求仅记非秘密配置，Authorization不写入记录。打印在预算代理stdout。
- 来源独立：DeepSeek原始响应为deepseek-upstream；Hermes封装结果为hermes-adapter，旧hermes_output也能纠正显示来源；不会冒充未捕获的原始provider数据。
- 用户启动脚本复用现有部署凭据，仅用户执行时重载budget-proxy，不自动出题。thinking=enabled时按官方要求使用tool_choice=auto；保留普通content及函数封装两种输出的后续业务校验。开启诊断不等于实现通用工具执行循环。
- 本机读取限制、Last-Event-ID恢复、归档式清空与启动回执均已核对。未找到启动回执时标未知，以具体请求元信息为准。

## 验证

命令：

```bash
ZHIJUAN_SKIP_DOTENV=1 ZHIJUAN_RAW_API_DIR='' .venv/bin/python -m unittest tests.test_raw_api_capture tests.test_raw_api_routes tests.test_live_budget_proxy tests.test_strict_json_output tests.test_activity_stream tests.test_native_stream_transport tests.test_hermes_runs_transport
node --test tests/frontend_raw_api.test.mjs
npm run build --prefix apps/web
.venv/bin/python tools/check_code_lines.py
```

65项Python通过，3项Node通过，构建通过，200物理行门禁通过。测试覆盖逐字节UTF-8/SSE换行保留、reasoning/正文/工具参数独立累计、未知字段保留、工具多个index、来源纠正、游标恢复、本机访问、跨站拒绝和可恢复归档。单元测试ASGI客户端不启动生产后台，不发模型请求。

浏览器：现有Codex右侧IAB，localhost:3000/raw-api.html；刷新已读取现有历史记录629条、原始文本103804字符，所选metadata为thinking disabled。检查重新连接、请求选择、数据区、来源标签及复制可用性。未点击归档/清空实际数据。desktop.png与mobile.png保存当前页面；窄侧栏实际宽582（IAB最小布局），无横向溢出；09-25同页390测试为历史证据，未冒充本轮390复测。读到既有记录不代表本轮新发API调用。

首次测试运行被现有.env开启了采集，若干mock响应进入诊断文件。已按本次时间窗口及已知fixture标识，将16个确认属于本次离线测试的请求移到独立responses-offline-test-20260928T091458.ndjson，保留原始文件内容和其他上游记录；没有删数据。最终重测关闭dotenv与实际采集，日志不含模拟流伪装成实际调用的证据。

## 未执行与证据边界

遵照用户要求，本轮没有运行raw_api_console start/stop、没有主动重启生成服务、没有新发计费调用。thinking实际生成、线上工具调用多轮回传、启用后的完整端到端需用户启动后验证。目录64MiB上限停止采集时有显式记录；无全量无限留存承诺。生产多租户鉴权不是本机诊断页面范围。

调研及启动命令：docs/raw-api-console.md。官方文档明示thinking下强制tool_choice不支持；原先thinking disabled和函数封装转换解释了普通面板看不到供应商思考字段的原因。
