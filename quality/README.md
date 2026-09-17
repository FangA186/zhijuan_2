# 质量检查：先看范围，不能只看绿灯

suites.yaml 登记 6 个当前可运行离线组和 6 个尚未实现的应用/真实调用组。`all-offline` 明确只运行前者。测试目录的 10 项应用回归保护是行为要求，不是已有 E2E 实现。把应用功能写出来时，需要逐项补 actual_test_paths、实际命令与环境，并接入独立应用 CI；不能只改一个状态标签。

run_quality_checks.py 只执行 catalog 中明确登记的离线 Python 命令，禁止 shell 插值；这不是 Python 代码沙箱，必须审查所运行的仓库代码。它检查非零退出、超时、单元报告缺失、零测试/skip/expected failure；这些均不计 PASS。

报告记录输入范围文件 SHA256、功能依赖和范围元数据哈希、Python/依赖版本、Git HEAD/变化路径、命令、结果和脱敏日志。执行中范围变化，整轮结果失败。手工编辑报告仍可能造假：哈希不是签名，真实信任依赖受保护 CI 与审查。

## 启用 GitHub CI

把本包内容合并至 Git 仓库根，使 `.github/workflows/ci.yml` 位于真实仓库根。用独立测试 PR 执行，确认 `offline` 的报告中真实运行了 6 个组，并下载证据。Actions 和依赖安装需要网络；本次没有在远程执行。

在仓库保护规则中，将 **知卷离线检查 / required-checks** 设为必需检查（以首次运行实际显示名为准），要求 PR 审查，并对新增提交使旧审查失效。配置实际 CODEOWNERS，不能把示例里的空人名当已启用。限制修改 workflow、quality、契约与权限代码的自审权限。

工作流不配置 paths 过滤，不使用 pull_request_target、不传模型密钥、不部署应用。汇总 job 使用 always() 并要求 offline 的真实结果为 success，防止上游 skipped/cancelled 被默认为通过。用户仍可能修改工作流或绕过规则；GitHub 端保护并未由 ZIP 自动设置。

该检查名明确是“离线检查”，不能作为 APP/LIVE/G-FULL 发布门。新增应用代码后必须增加类型、集成、安全、网页和导出流水线；高风险模型/Skill 变更需单独授权真实内容回归，不在未知 fork 的 PR 中注入付费密钥。

## 版本与可重复性

requirements-ci.lock 锁定本次离线依赖实际版本（不是生产依赖或全平台兼容保证）。Actions 使用已核查源码的固定 SHA。升级前在受控 PR 重跑并审查；候选版本不是永远安全或最新版本。CI 使用 Python 3.12；本地运行的实际 Python 版本记录在 report.json，不混为已实测同环境。
