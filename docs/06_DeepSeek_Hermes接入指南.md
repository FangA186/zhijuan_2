> v1.3 执行入口补充：先按 execution/M0_实施手册.md 完成真实能力核查，再按 execution/runbooks/commands-and-api.md 接入。本文配置片段不是可启动工程，也不是保证所有候选版本兼容。

# DeepSeek + Hermes 接入指南 · v1.3

## 已确定的选择

DeepSeek 官方 API 为模型服务，Hermes 为唯一 Agent 执行框架。LangChain、LangGraph 不属于本项目依赖。Celery/RabbitMQ 是任务基础设施；Adapter 是我们编写的薄 Python 接口，不是新的 Agent 框架。小学、初中、高中全部纳入验收，第一版不引入题库。

## 1. 固定运行基线

在经审定的 Hermes Git 提交与容器镜像上安装和做冒烟，不默认追踪 main 或使用未冻结的 latest。Python 版本、Hermes commit、镜像 digest、Skills bundle hash 与模型 ID 都进入部署记录。官方来源见主文档 [S02][S06][S27]。

## 2. 配置直连

在隔离的测试运行环境执行官方入口 `hermes model`，选择 DeepSeek，配置服务端密钥及账户中可用的模型。也可采用 `configs/hermes-reviewed-fragment.yaml` 的已核查字段，但占位符必须先替换。

```yaml
model:
  provider: deepseek
  default: REPLACE_WITH_VERIFIED_DEEPSEEK_MODEL_ID
skills:
  write_approval: true
```

密钥通过 `DEEPSEEK_API_KEY` 注入，不提交到代码仓库。`ZHIJUAN_DEEPSEEK_MODEL_ID` 是本项目启动层的建议变量名，不能假定 Hermes 原生读取它；启动层需显式写入审定配置。示例未设置任何真实密钥或未经验证的具体模型 ID。

## 3. 分开业务配置与原生配置

`business-policy.example.yaml` 由业务后端读取，保存角色映射、预算、版本、修订次数和权限策略；不能作为 Hermes 原生 config.yaml。五角色均为 deepseek，默认使用同一个已验收 model_id。盲解创建独立输入、目录、身份和会话，不读取作者答案；报告标记 SAME_MODEL。

首版不设置第二供应商或自动 fallback。辅助任务也必须使用同一经批准模型或禁用；不得因为主模型不支持图像就静默改走另一家服务。图像解释未获验收时标记待复核；结构化图形生成可继续使用确定性工具。

## 4. Adapter 只做边界工作

实现 `reference_code/adapter_contract.py` 中的自有协议：验证批准的 provider/model_id；创建受控实例；传入最小上下文和 Skills；接收工具事件；校验输出；终止取消任务；返回实际调用标识和费用记录。不要把这份 Protocol 当作现成 Hermes SDK 实现。

任务状态与预算归后端；Agent 循环归 Hermes；工具授权归网关；投递和进程恢复归 Celery。内容修订只使用一份由后端原子记账的 repair_attempt。请求重试选定一层负责，并关闭或计入底层 SDK 重试，不能在 Adapter、Celery 再叠乘。

## 5. 必须执行的真实联调

使用三个学段各至少一份小型配置跑通规划、命题、盲解、检查、修改、人工审批、导出。测试工具参数无效、模型空输出、429/超时、取消后迟到、相同任务重投、预算耗尽和盲解读取答案被拒绝。确认实际模型与辅助调用没有离开批准路由。

契约样例不是质量评测：还需学科教师评估答案、条件、年级适配和评分；数学/规则工具通过不代表所有学科自动正确。不得将本地单元测试通过标注为“已接通 DeepSeek”或“出题准确率通过”。

## 6. 本包可实际运行的测试

```bash
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python verify_bundle.py
```

`runtime_policy.py` 的测试使用假 model_id，仅验证配置拦截逻辑，不连接 DeepSeek。部署时该函数拒绝未替换的示例 ID，但不验证账户可用性，真实连接测试仍必须执行。

## 配置迁移

从旧版复制已有业务数据和 /v1 API 客户端无需改路径；文档与 API 元数据更新到 1.1。将旧 models 下的 SET_AFTER_EVALUATION 全部改为 deepseek 与验收后的 ID，补齐 exam_reviewer。不要合并、继承旧作者会话到盲解环境。保留旧试卷快照，不把此次配置变更追写到已发布文件。


## v1.3 新增验收约束

本文仍为接入指南，不含 Hermes 官方源码和实际 Adapter 实现。未来 M1 必须提供固定提交的可复现获取／安装方式与真实健康检查。M2 通过 G-MIN，M3 通过 G-FULL 后才可分别宣称最小闭环与完整受控试用。见 `07_MVP阶段_验收链路_交付效果.md` 及包根目录 `acceptance/README.md`。
