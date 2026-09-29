# Git干净检出CI失败修复

日期2026-09-29；任务DEV-04；BUG-20260929-001。
原失败：GitHub Actions run36511691353，提交80dd988，offline阶段在运行测试前因缺少本地历史verification.json退出2，上传阶段也因无输出目录失败。punycode警告不是根因。

## 复现与根因
使用git archive HEAD导出仅受跟踪文件并初始化独立Git测试目录，确切复现Missing required file: acceptance-runs/maintenance/project-overview-20260922-001/verification.json（退出2）。原本机验收读到了未入库文件，不能代表干净检出。

第一层修复后完整运行揭示7项教材测试依赖smartedu_data与本机图片；同时CI锁文件仅包含旧开发记录工具依赖，没有新应用测试的FastAPI/httpx等依赖。

## 修复
普通记录结构检查对acceptance-runs下明确被Git忽略且未跟踪的历史证据缺失返回LOCAL_EVIDENCE_UNAVAILABLE警告；严格证据检查、当前finish门禁、日志哈希核验不放宽。受跟踪文件、源码、必要报告缺失仍报错，不伪造历史验证。
运行器启动/配置检查失败也生成overall=FAIL报告并继续以非零退出，不覆盖旧运行目录。离线子进程设置ZHIJUAN_SKIP_DOTENV，移除数据库/队列测试连接与密钥变量，避免加载本机配置。
CI依赖复用requirements-runtime.lock。教材单测使用临时合成分类/教材/目录和图片服务字节夹具，不再绑定本地抓取库；7个版本、隐藏过滤、非空章节、接口及路径越界断言保留；静态已提交词汇索引的367册/2005张元数据校验保留。自定义data_dir发现workspace_root未定义，一并修复构造函数初始化。

## 验证
- 干净Git文件副本：原失败已复现，证据reproduce.log。
- 本机Python3.14：完整9组all-offline通过（补充最后一项严格跟踪文件回归前为494项基础测试）。
- 独立python:3.12-slim容器，Linux aarch64 / Python3.12.14：安装最终requirements-ci.lock成功；执行与CI相同的all-offline命令，9组全部PASS，基础测试495项、0失败/错误/跳过；memory55、project-overview9、bug-memory9项另行通过。
- 新增3项回归：缺失忽略证据只警告但严格模式失败；已跟踪证据即使匹配ignore也必须存在；启动失败生成FAIL报告且旧目录不覆盖。
- code-line-limit通过，git diff --check通过。未调用真实模型、未改用户数据库、未重启产品服务。

Linux底层输出保留在本地linux312/与linux312-command.log，遵循用户不提交运行产物要求；本报告记载事实而不伪造远端执行结果。GitHub原run仍为失败，本次没有远端重跑或推送。Linux容器为aarch64，GitHububuntu默认x86_64，最终远端状态需推送后核对。
