#!/usr/bin/env bash
set -euo pipefail

APP_NAME="trading"
INSTALL_DIR_DEFAULT="$(pwd)"

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

echo "=== Trading macOS Deploy ==="
echo

need_cmd git
need_cmd curl
need_cmd lsof
need_cmd pkill

INSTALL_DIR=$(ask "确认项目目录" "$INSTALL_DIR_DEFAULT")
PYTHON_BIN=$(ask "Python 命令" "python3")
need_cmd "$PYTHON_BIN"

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
echo "请编辑以下文件后继续："
echo "  - $INSTALL_DIR/config/settings.json"
echo "  - $INSTALL_DIR/.env"
echo
read -r -p "编辑完成后按回车继续..." _

chmod +x start_trading.sh stop_trading.sh
./start_trading.sh

echo
echo "部署完成"
echo "Dashboard: http://127.0.0.1:8787/web/"
echo "启动: ./start_trading.sh"
echo "停止: ./stop_trading.sh"
