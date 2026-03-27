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

echo "=== Trading Ubuntu Deploy ==="
echo

need_cmd sudo
need_cmd bash

INSTALL_DIR=$(ask "确认项目目录" "$INSTALL_DIR_DEFAULT")
PYTHON_BIN=$(ask "Python 命令" "python3")
ENABLE_SERVICE=$(ask "安装为 systemd 服务？yes/no" "yes")

cd "$INSTALL_DIR"

sudo apt-get update
sudo apt-get install -y git curl lsof pkill "$PYTHON_BIN" python3-venv python3-pip

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

if [ "$ENABLE_SERVICE" = "yes" ]; then
  sudo tee /etc/systemd/system/trading-dashboard.service >/dev/null <<EOF
[Unit]
Description=Trading Dashboard Runner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=/usr/bin/env bash $INSTALL_DIR/start_trading.sh
ExecStop=/usr/bin/env bash $INSTALL_DIR/stop_trading.sh
Restart=always
RestartSec=5
User=$USER

[Install]
WantedBy=multi-user.target
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable trading-dashboard.service
fi

./start_trading.sh

echo
echo "部署完成"
echo "Dashboard: http://127.0.0.1:8787/web/"
echo "启动: ./start_trading.sh"
echo "停止: ./stop_trading.sh"
if [ "$ENABLE_SERVICE" = "yes" ]; then
  echo "systemd 启动: sudo systemctl start trading-dashboard.service"
  echo "systemd 停止: sudo systemctl stop trading-dashboard.service"
  echo "systemd 状态: sudo systemctl status trading-dashboard.service"
fi
