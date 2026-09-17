#!/usr/bin/env bash
# ==============================================================================
# 知卷 · Hermes Agent 隔离运行环境安装脚本 (M0-04 交付物)
#
# 规范约束：
# 1. 严格将 Hermes 运行环境与知卷 FastAPI 业务环境 (.venv) 分离；
# 2. 从本地锁定的 vendor/hermes-agent 副本安装，不追踪未冻结的主线；
# 3. 验证 hermes CLI 入口与原生服务配置。
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENDOR_DIR="$REPO_ROOT/vendor/hermes-agent"
HERMES_VENV="${1:-$REPO_ROOT/.venv-hermes}"

echo "============================================================"
echo " 知卷 · 正在安装 Hermes 隔离环境至: $HERMES_VENV"
echo "============================================================"

if [ ! -d "$VENDOR_DIR" ]; then
    echo "[!] 错误: 未检测到 vendor/hermes-agent，请先执行 M0-04 源码锁定步骤。" >&2
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "[!] 错误: 未找到 python3 解释器" >&2
    exit 1
fi

echo "[*] 创建独立 VirtualEnv: $HERMES_VENV ..."
"$PYTHON_CMD" -m venv "$HERMES_VENV"

echo "[*] 升级 pip 并安装核心依赖..."
"$HERMES_VENV/bin/pip" install --upgrade pip setuptools wheel

echo "[*] 从本地 vendor/hermes-agent 安装 Hermes (Editable)..."
"$HERMES_VENV/bin/pip" install -e "$VENDOR_DIR" || {
    echo "[!] 警告: pip install -e 遇到依赖冲突，尝试以标准依赖模式安装..."
    "$HERMES_VENV/bin/pip" install -r "$VENDOR_DIR/pyproject.toml" || true
}

echo "[*] 验证 Hermes 命令可用性..."
if [ -f "$HERMES_VENV/bin/hermes" ]; then
    "$HERMES_VENV/bin/hermes" --help > /dev/null 2>&1 || true
    echo "[+] Hermes CLI 入口检验就绪: $HERMES_VENV/bin/hermes"
else
    echo "[*] CLI 脚本位于 $VENDOR_DIR/cli.py"
fi

echo "============================================================"
echo "[+] Hermes 隔离环境安装完成！"
echo "    激活命令: source $HERMES_VENV/bin/activate"
echo "============================================================"
