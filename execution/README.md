# 阶段执行入口 · v1.3

先读 `../docs/08_阶段开发执行手册.md` 的第 29 章，再读对应 M0/M1/M2/M3 手册。32 张卡片的单一索引为 task-index.yaml；source_files 是本包已有材料，target_files 是应用待开发文件。

`api-task-map.yaml` 对应 25 个业务操作；`traceability.yaml` 对应原 47 类验收。runbooks 包含 M1 独立启动检查、命令与 API 顺序、故障注入。templates 为待填写能力探测、质量口径、任务记录与阶段签收。

所有任务 NOT_STARTED，运行验收 NOT_RUN。离线校验在包根目录执行 `python tools/verify_execution_plan.py`，只检查任务依赖/引用/覆盖，不启动 Hermes、模型或应用。不得将本文件夹目录当作已经存在的工程框架。
