# 34 命令、原生 API 与业务 API 的执行边界

## 34.1 三类命令必须分开

| 类别 | 当前是否能执行 | 用途 |
| --- | --- | --- |
| LOCAL_OFFLINE | 本包确有脚本，可在安装测试依赖后执行 | 检查文档、契约、任务依赖和参考代码；不启动产品 |
| UPSTREAM_SETUP / UPSTREAM_LIVE | 安装工具/密钥/固定上游版本后由开发者执行；本轮未运行 | 获取 Hermes，检查原生 API 与实际模型调用 |
| APP_REQUIRED | 当前目标文件不存在，必须按任务实现后补齐并复测 | 应用启动、迁移、真实生成、导出、E2E；不得现在声称一键运行 |

本包根目录可执行的离线命令如下；保存退出码和真实日志，不能把输出解释为 MVP 已完成。

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python verify_bundle.py
python verify_acceptance_assets.py
python tools/verify_execution_plan.py
```

## 34.2 Hermes 源码获取与安装的具体顺序

以下在专用开发目录执行，要求 Git、Python 与经审查的依赖安装工具已存在。本轮只提供步骤，没有执行克隆/安装。先由技术负责人选择并填写真实 40 位提交，不以文档日期冒充版本。

```bash
# UPSTREAM_SETUP；在开发者新建的应用仓库目录，不在本材料 ZIP 中执行
export HERMES_COMMIT='REPLACE_WITH_REVIEWED_40_CHAR_COMMIT'
# 开始前校验变量已替换，未替换必须退出
printf '%s' "$HERMES_COMMIT" | grep -Eq '^[0-9a-f]{40}$' || exit 2
mkdir -p vendor
git clone --no-checkout https://github.com/NousResearch/hermes-agent.git vendor/hermes-agent
git -C vendor/hermes-agent checkout --detach "$HERMES_COMMIT"
git -C vendor/hermes-agent rev-parse HEAD
git -C vendor/hermes-agent status --porcelain
```

git clone 会联网下载，上述目录必须不存在；已有目录先核查来源与工作区，不用 rm -rf 覆盖。提交来自批准锁定记录，克隆成功只说明源码存在。然后在源码外建立 venv，按该提交文档和锁文件安装，检查安装输出。官方开发说明有独立 venv 和源码安装路径；本项目不要求照搬 all/dev 全量可选依赖。[S30][S31]

业务依赖与 Hermes 使用不同 venv/镜像。安装命令必须由开发负责人根据固定提交实际验证，并写入 install/hermes-install.sh 及运行报告；不能凭当前在线文档保证一个未测依赖组合。若使用 uv.lock，使用与提交匹配的冻结安装方式；若缺可重复锁，则先生成审定 lock 再交付，不只保存 pip freeze 当完整可重复构建保证。

## 34.3 配置和启动原生服务

在独立的受控测试 HOME/runtime 内配置 provider=deepseek 和已验证 model_id；DEEPSEEK_API_KEY 从服务端秘密配置注入。原生 API 另需 API_SERVER_KEY，不能使用模型密钥替代。[S27][S29]

```text
# UPSTREAM_SETUP；变量名称已核查，真实值不写入本文件
API_SERVER_ENABLED=true
API_SERVER_HOST=127.0.0.1
API_SERVER_PORT=8642
API_SERVER_KEY=<server-only-secret-reference>
DEEPSEEK_API_KEY=<server-only-secret-reference>
```

在已激活的正确 Hermes 环境执行 `hermes model` 配置 DeepSeek，再执行 `hermes gateway` 启动 API。[S29] 对容器部署，容器内监听地址与宿主暴露策略分别控制，默认只在受控网络可达；不要为方便把管理端口公开。

服务端调用原生 `/health` 看存活，`/health/detailed` 读取状态字段而不只看 HTTP 200；它不能证明模型已可用。`/v1/capabilities`、`/v1/skills`、`/v1/toolsets` 按固定版本支持情况探测。API 原生默认能力较宽，业务必须在接收不可信教师输入前落实工具白名单；“提示里说禁止”不是权限控制。[S29]

## 34.4 原生 Runs 映射：这是开发契约，不是 SDK 包装已实现

| 原生操作（Hermes 内部服务） | Adapter 应执行什么 | 明确禁止 |
| --- | --- | --- |
| POST /v1/runs | 使用批准的 model/provider、单次 input 和指定 Skill 指令；保存 run_id；仅在实测支持时使用幂等键 | 复用作者 previous_response_id 给盲解；信任客户端 provider |
| GET /v1/runs/{id} | 检查实际终态与 completed/partial/error；结构校验后才保存成功 | HTTP 200 就算命题成功 |
| GET /v1/runs/{id}/events | 消费事件、脱敏并持久化必要业务事件；接受重复/重连 | 全量转发答案、工具 preview、私有推理 |
| POST /v1/runs/{id}/stop | 请求合作停止，业务先禁止派发/写回，查最终退出 | stop 返回即宣称所有在途费用取消 |

API 具备这些表面能力并不自动提供知卷的权限、题目版本、成本账本和发布流程。`/v1/runs` 的保留/幂等机制与候选提交绑定，不能把在线文档的缓存时限当永久保证；结果不明先对账。[S28][S29]

## 34.5 业务 API 联调的真实顺序

业务地址与 Hermes 地址分开。下面路径来自本包 `contracts/openapi.yaml`；全部是待实现业务 API。身份 cookie/CSRF 从实际身份流程取得，不在文档硬编码凭证。

```text
GET   /v1/session                         读取受信身份/权限
POST  /v1/exams                           创建已确认范围的草稿
GET   /v1/exams/{id}/spec                  恢复完整规格与 ETag
POST  /v1/exams/{id}/plan-jobs             获得 job_id
GET   /v1/jobs/{job_id}                    等规划完成
GET   /v1/exams/{id}/plans/current         获得 plan_id/hash/slots
POST  /v1/exams/{id}/plans/{plan_id}/confirm 确认指定计划
POST  /v1/exams/{id}/generation-jobs       执行真实命题
GET   /v1/jobs/{job_id}/events             读取业务进度
GET   /v1/exams/{id}?view=teacher          授权读取候选
POST  /v1/exams/{id}/validation-jobs       检查/盲解
PATCH /v1/exams/{id}/slots/{slot}/content  编辑并使旧证据失效
POST  /v1/exams/{id}/review-decisions      当前版本人工审核
POST  /v1/exams/{id}/export-jobs           M2 草稿；M3 待审最终文件
GET   /v1/exports/{export_id}              查询实际渲染与文件哈希
POST  /v1/exams/{id}/publish               仅 M3 满足全部条件
POST  /v1/exams/{id}/publications/{snapshot_id}/revoke
```

每个写请求携带契约要求的 CSRF/If-Match/幂等键，具体 body 以 OpenAPI 为准。新增读取接口返回确定形状，前端不用猜 Job 的任意 result 字段。鉴权系统登录/回调/退出为 M3-02 的身份集成工作，不把 `GET /v1/session` 当登录接口。

## 34.6 未来应用必须提供的启动入口

| 工作目录 | 待实现入口 | 通过判定 |
| --- | --- | --- |
| 应用根目录 | infra/compose.app.yaml，完整服务启动 | 服务全部 ready；不只是 Postgres/RabbitMQ |
| 应用根目录 | migrations/ + 迁移入口 | 空库与升级路径都在实际数据库跑过 |
| apps/web | package.json 中 build/dev/test 脚本 | 真网页接业务 API，不导入 mock 生成器 |
| Worker 模块 | 队列进程、outbox 和恢复巡检 | 重投/重启无重复领域写入 |
| 验收目录 | 自动化 E2E 或明确人工脚本 | 对应证据保存，NOT_RUN 不自动改 PASS |

这些路径是 M1—M3 的产出要求，当前材料 ZIP 没有相应运行实现。不要现在执行不存在的 `make mvp` 或 `docker compose -f infra/compose.app.yaml up`，也不要让 README 把“需开发”步骤写成“已完成”。
