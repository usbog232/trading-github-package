#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"
ROOT="$(pwd)"

if [ -d .venv ]; then
  source .venv/bin/activate
fi
if [ -f .env ]; then
  set -a
  source ./.env
  set +a
fi

echo "先执行 Kill Switch..."
python src/run_kill_switch.py || true

echo "正在停止后台进程..."
for pid_file in logs/runner.pid logs/dashboard.pid logs/toggle.pid; do
  if [ -f "$pid_file" ]; then
    pid=$(cat "$pid_file" 2>/dev/null || true)
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
    rm -f "$pid_file"
  fi
done

pkill -f "$ROOT/src/runner.py" 2>/dev/null || true
pkill -f "$ROOT/web/server.py" 2>/dev/null || true
pkill -f "$ROOT/web/toggle_server.py" 2>/dev/null || true
sleep 1
pkill -9 -f "$ROOT/src/runner.py" 2>/dev/null || true
pkill -9 -f "$ROOT/web/server.py" 2>/dev/null || true
pkill -9 -f "$ROOT/web/toggle_server.py" 2>/dev/null || true

for port in 8787 8788; do
  pids=$(lsof -tiTCP:$port -sTCP:LISTEN 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
done

echo "已完成 trading 相关进程彻底停机。"
