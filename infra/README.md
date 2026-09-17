# 本地基础设施示例
仅启动 PostgreSQL 和 RabbitMQ；不会启动业务 API 或 Hermes，也不会自动执行数据库草案。

先在本地环境设置 `POSTGRES_PASSWORD`、`RABBITMQ_PASSWORD`，然后运行：
```bash
docker compose -f infra/compose.yaml up -d
```
生产禁止使用开发 owner 账号，禁止公开暴露数据库和管理端口；必须固定镜像摘要、配置备份和最小权限。Agent 沙箱不得获得 Docker socket。完整应用需按文档另行实现与验收。
