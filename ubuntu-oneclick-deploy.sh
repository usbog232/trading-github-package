#!/usr/bin/env bash
set -euo pipefail

APP_NAME="trading"
INSTALL_DIR_DEFAULT="$HOME/$APP_NAME"

echo "=== Trading Ubuntu 一键部署 ==="
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

REPO_URL=$(ask "请输入 Git 仓库地址")
[ -n "$REPO_URL" ] || { echo "仓库地址不能为空"; exit 1; }
INSTALL_DIR=$(ask "请输入安装目录" "$INSTALL_DIR_DEFAULT")
PYTHON_BIN=$(ask "请输入 Python 命令" "python3")
ENABLE_SERVICE=$(ask "是否安装为 systemd 服务？yes/no" "yes")

sudo apt-get update
sudo apt-get install -y git curl lsof pkill "$PYTHON_BIN" python3-venv python3-pip

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
printf '%s\n' "请现在手动编辑以下文件："
printf '  - %s\n' "$INSTALL_DIR/config/settings.json"
printf '  - %s\n' "$INSTALL_DIR/.env"
echo
printf '%s\n' "至少填写："
printf '%s\n' "  - api.monitor_wallet_address"
printf '%s\n' "  - api.execution_wallet_address"
printf '%s\n' "  - HYPERLIQUID_SECRET_KEY"
printf '%s\n' "  - 你的风控参数"
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
echo "启动命令: ./start_trading.sh"
echo "停止命令: ./stop_trading.sh"
if [ "$ENABLE_SERVICE" = "yes" ]; then
  echo "systemd 启动: sudo systemctl start trading-dashboard.service"
  echo "systemd 停止: sudo systemctl stop trading-dashboard.service"
fi
