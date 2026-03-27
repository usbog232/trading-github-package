#!/usr/bin/env bash
set -euo pipefail

APP_NAME="trading"
INSTALL_DIR_DEFAULT="$HOME/$APP_NAME"

echo "=== Trading macOS 一键部署 ==="
echo "本脚本不会包含你的真实敏感信息。"
echo

ask() {
  local prompt="$1"
  local default="${2:-}"
  if [ -n "$default" ]; then
    read -r -p "$prompt [$default]: " val
    echo "${val:-$default}"
  else
    read -r -p "$prompt: " val
    echo "$val"
  fi
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "缺少命令: $1"; exit 1; }
}

need_cmd git
need_cmd curl
need_cmd lsof
need_cmd pkill

REPO_URL=$(ask "请输入 Git 仓库地址")
[ -n "$REPO_URL" ] || { echo "仓库地址不能为空"; exit 1; }
INSTALL_DIR=$(ask "请输入安装目录" "$INSTALL_DIR_DEFAULT")
PYTHON_BIN=$(ask "请输入 Python 命令" "python3")

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "未找到 $PYTHON_BIN，请先安装 Python 3。"
  exit 1
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  rm -rf "$INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
$PYTHON_BIN -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

mkdir -p config logs data/dashboard data/journal
if [ ! -f config/settings.json ] && [ -f config/settings.example.json ]; then
  cp config/settings.example.json config/settings.json
fi
if [ ! -f .env ] && [ -f .env.example ]; then
  cp .env.example .env
fi

echo
echo "请现在手动编辑："
echo "  - $INSTALL_DIR/config/settings.json"
echo "  - $INSTALL_DIR/.env"
echo
echo "至少填写："
echo "  - api.monitor_wallet_address"
echo "  - api.execution_wallet_address"
echo "  - HYPERLIQUID_SECRET_KEY"
echo "  - 风控参数"
echo
read -r -p "编辑完成后按回车继续..." _

chmod +x start_trading.sh stop_trading.sh
./start_trading.sh

echo
echo "部署完成"
echo "Dashboard: http://127.0.0.1:8787/web/"
echo "启动命令: ./start_trading.sh"
echo "停止命令: ./stop_trading.sh"
