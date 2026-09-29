# 变更影响

M1-03 / FEAT-ADAPTER；用户明确要求原始API抓取（含reasoning_content）及独立页，运行由用户控制。main上保留所有既有未提交修改。

调用链：DeepSeek响应 → raw_api_capture旁路 → 既有strict转换 → Hermes；文件 → 既有FastAPI raw_api_routes → Vite代理 → raw-api独立页。Hermes结果额外采集保留但来源单独标记。

修改工具、前端静态页、raw API路由与既有http_runner采集来源；保留端口8000/3000集成。没有新依赖/Agent框架/数据库迁移。默认诊断与thinking关闭，用户start选项开启；只读GET不发起模型，归档不删除数据。受信校验与盲解权限不变。

回归命令和实际结果见report.md。权限/模型/协议边界及用户明确授权记在DEV-020。恢复方式为任务结束后用户执行raw_api_console stop，保留抓取文件与费用账本；未经用户启动不修改运行态。
