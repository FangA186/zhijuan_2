# 按任务和会话分别交接

当前无已执行产品任务交接。通过 `project_memory.py handoff` 创建 `<task>--<session>.yaml`；每次检查点取新 session 名，默认不覆盖。不要手写一个全局 HANDOFF.md 让所有并行会话共同抢写。

命令记录创建时间、Git HEAD/分支、暂存/未暂存/未跟踪路径并计算本任务输入/目标/变化文件指纹。不读取 diff 或源码正文。然后据实补充 completed、pending、decisions、failed_approaches、evidence_refs。不记录私有推理、密钥和完整题目。

context 会显示同任务最近三条交接并标出 HEAD/分支或登记文件变化。不同分支都可能有效，不能把最新时间戳当成唯一真相；人工选择本工作区相关记录。会话时间可编辑，工具不是可信审计时钟。更早记录按需读取，不默认灌入上下文。
