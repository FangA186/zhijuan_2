# Bug 修复记忆

本目录是 Bug 的事实来源；`http://localhost:3000/project?tab=bugs` 直接读取，Notion 保存展示副本。任务进度仍归 `progress/work.yaml`，完整测试日志归 `acceptance-runs/`，Bug 文件只记录可复用结论和证据路径。不要写入密钥、题干、用户上传文件正文或原始日志。

## 每次修复的顺序

1. 先读取 AGENTS 与任务上下文；运行 `.venv/bin/python tools/bug_memory.py search --task <任务ID> --query '<症状 报错 模块>'`。它会保存 `progress/generated/bug-search/<任务ID>.json`；无匹配也记录。普通 `context` 会自动列出最多五条相关 Bug 索引。
2. 打开命中记录，核对当前代码、适用条件和失败复现。相同根因复发时把原记录改为 REOPENED、追加 events 和任务 ID；根因不同则用新的 BUG 日期序号，写明相关旧 ID。不要删除旧的失败尝试和验证历史。
3. 复制 `progress/templates/bug-record.yaml` 为 `progress/bugs/BUG-YYYYMMDD-NNN.yaml`。修复后填根因、修复方法、直接代码路径、回归命令、验证日期与证据路径，再将状态设 FIXED。指纹只辅助识别代码变化，不代替验收。
4. 运行 `bug_memory.py check`，交接填写 `bug_ids: [BUG-...]`。也可在 work 条目声明 `work_type: BUGFIX`。`finish` 对这些已声明任务检查修前检索和 Bug 记录，上一检查点前的查询不能替代本轮查询；工具无法识别所有自然语言意图，AGENTS 是各开发代理执行入口。
5. 运行 `bug_memory.py notion-export`，使用当前连接的 Notion MCP 按 BUG ID 更新已登记 URL；没有 URL 才创建，未知写入结果先按 ID 查找，不盲目重建。写入后 fetch 回读核对标题、状态和正文，再 `mark-synced --bug <ID> --url <页面URL> --hash <导出指纹>`。这只是本地同步回执，不能认证操作者。
6. 运行任务 `finish`。Bug 修复任务 DONE 要求关联记录 FIXED 且当前内容已登记 Notion 回读同步。连接不可用就保留待同步，不改绿灯。不要声称后台自动双向同步；后续编码代理在每次交付时执行上述动作。

## 文件布局

- `BUG-*.yaml`：一条缺陷一个文件，便于小范围读取和 Git 比较。
- `notion-sync.json`：Bug ID → Notion URL/内容指纹/回读时间；不是凭据。
- `../generated/bug-search/`：任务级检索回执，可重新生成，不作为历史根因记录。
- `../templates/bug-record.yaml`：新 Bug 模板。

首批记录从 DEV-03 的实际报告回填，标注历史验证日期；缺图问题仍待处理。旧 Notion 任务卡保留，修复记忆通过任务 ID 与其对应。
