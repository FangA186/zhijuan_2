任务 ID / 功能 ID：M1-05 / FEAT-SPEC
实际分支、HEAD、未提交修改：main / 1a89b534185055055d23697f1a61b307efa56253；工作区另有他人未提交改动。
本次改变的行为：无效规格在保存前拒绝；范围修改后要求重新确认；前端保存 HTTP 错误停止后续生成。
实际影响：规格服务、校验器、两个配置页面、api.ts 的 saveExamSpec、离线测试。受批准 schema 未变。UI sidecar 由 store 单独保存待集成。
验证：spec-tests.log 4 项通过；frontend-build.log 构建通过；diff-check.log 无错误。
未覆盖：真实三学段页面/数据库/权限/模型、能力注册表接线、版本和失效原子性。
