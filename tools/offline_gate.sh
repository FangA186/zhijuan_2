#!/usr/bin/env bash
# 知卷离线测试门禁：净化环境后运行项目统一单测收集器（report 必须位于
# acceptance-runs/ 下）。
#
# 用途：确保 CI/门禁不会因为本机残留的环境变量（DSN、broker、密钥、
# token）把离线单测变成带上游副作用或秘密泄漏的运行。本脚本自身不通话
# 任何网络、不加载 .env、不输出任何秘密。
#
# 用法：
#   bash tools/offline_gate.sh acceptance-runs/<类型>/<run-id>/report.json
set -u

if [ "$#" -ne 1 ]; then
  echo "usage: bash tools/offline_gate.sh acceptance-runs/<type>/<id>/report.json" >&2
  exit 2
fi

REPORT="$1"

case "$REPORT" in
  acceptance-runs/*) ;;
  *)
    echo "error: report 必须位于 acceptance-runs/ 下: $REPORT" >&2
    exit 2
    ;;
esac

# 报告父目录提前创建，避免收集器因目录缺失失败。
mkdir -p "$(dirname "$REPORT")" || exit 2

# 净化：跳过 .env 加载，并清空一切可能触发上游调用或泄漏秘密的变量。
unset DATABASE_URL
unset ZHIJUAN_TEST_DATABASE_URL
unset CELERY_BROKER_URL
unset DEEPSEEK_API_KEY
unset DEEPSEEK_UPSTREAM_API_KEY
unset HERMES_API_BASE_URL
unset HERMES_API_KEY
unset HERMES_SOLVER_API_BASE_URL
unset HERMES_SOLVER_API_KEY
unset HERMES_SOLVER_UPSTREAM_KEY
unset ZHIJUAN_BUDGET_PROXY_TOKEN
unset API_SERVER_KEY

export ZHIJUAN_SKIP_DOTENV=1

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/tools/run_unittests.py" --report "$REPORT"
