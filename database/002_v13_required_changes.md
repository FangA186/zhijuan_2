# v1.3 数据迁移实施要求（不是已执行迁移）

M1-02 把 001 SQL 草案转为 Alembic 迁移；旧草案不能在生产直接重跑。更新后的 API 多了读取当前规格、蓝图、历史、身份及撤回。当前没有应用数据库，不存在已经完成的数据升级。

## 必须实现

当前计划读取：以 exams.current_plan_id 联接 exam_plans，并同时核验 tenant_id、exam_id 和 spec_revision；陈旧计划不能确认。历史列表仅元数据，用创建时间与 ID 做稳定游标，不检索题目。

身份查询：从受信会话映射 user/tenant/membership，不能接受请求头自行指定角色；返回 no-store 的权限投影与 CSRF 令牌。

运行对账：jobs 状态增加 RECONCILING，表示外部调用结果不确定且在查询确认。迁移检查约束、API enum、Worker 映射和页面一起修改；未知计费不能算零。

发布撤回：新增 publication_revocations（tenant_id、exam_id、snapshot_id、actor_id、reason、created_at）；以 tenant+snapshot 唯一约束保证重复撤回幂等，外键必须限定同一 exam。授权后才能创建；下载查询必须同时验证未撤回。

原 SQL 中 job_steps 等表已经包含部分租约/去重字段；实现前逐字段核对，不重复另建互不一致状态。审批只追加、不可变快照不就地覆盖。读路径、写路径、权限和索引均必须用真实 PostgreSQL 验证。

## 回归与恢复

空库迁移、旧版结构前向迁移、跨租户外键、过期蓝图、撤回幂等、旧下载权限、Worker 重入和恢复各有测试。已发布文件保留原哈希；数据库回滚必须考虑新写入字段兼容，不只执行 down revision。迁移前备份，失败停止依赖服务上线。

## 材料计划的分值约束

PlanSlot 新增 parent_slot_id；材料父槽位为 material_group、score_x100=0，子槽位引用父槽位。规划确认前检查无环、父节点存在且类型正确、叶子题数量与分值和；父题不能再次累计。当前 SQL JSON 字段不会自动保证这些约束，须在 M2-01/M3-01 服务和测试中实现。
