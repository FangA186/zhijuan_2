# 本地 PostgreSQL 集成测试

这些测试会在显式指定的专属测试数据库/独立 schema 中创建和修改数据，不属于不带环境配置的 `all-offline`。

先在环境中设置指向可丢弃数据库的 `DATABASE_URL` 和相同的 `ZHIJUAN_TEST_DATABASE_URL`；应用测试需要先执行 `database/003_generation_jobs.sql`、`database/004_generation_exam_state.sql`。禁止使用共享或生产数据库。设置 `ZHIJUAN_SKIP_DOTENV=1`，不注入 Hermes 运行凭据，不启动消费该测试 schema 的 Worker。

```bash
.venv/bin/python -m unittest discover -s tests/integration -v
```

缺环境时测试会显式跳过；跳过不代表集成通过。本轮通过的命令、环境和结果见 `acceptance-runs/workflow/sol-six-features-resume-20260922-002/`。原有并发、取消、版本、持久化和 API 断言全部保留，目录分开只是使离线入口不会隐式访问数据库。
