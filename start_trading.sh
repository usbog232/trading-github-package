#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

DASHBOARD_URL="http://127.0.0.1:8787/web/"
ROOT="$(pwd)"
mkdir -p logs data/dashboard

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -q -r requirements.txt

if [ -f .env ]; then
  set -a
  source ./.env
  set +a
fi

cleanup_existing() {
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
}

wait_port_free() {
  local port="$1"
  for _ in {1..20}; do
    if ! lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.3
  done
  echo "端口 $port 仍被占用"
  return 1
}

start_service() {
  local cmd="$1"
  local pid_file="$2"
  local log_file="$3"
  nohup zsh -lc "$cmd" > "$log_file" 2>&1 & echo $! > "$pid_file"
}

verify_pid() {
  local pid_file="$1"
  local name="$2"
  if [ ! -f "$pid_file" ]; then
    echo "启动失败：$name pid 文件不存在"
    exit 1
  fi
  local pid
  pid=$(cat "$pid_file")
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "启动失败：$name 进程未存活"
    exit 1
  fi
}

verify_http() {
  local url="$1"
  local name="$2"
  TARGET_URL="$url" python3 - <<'PY'
import os, sys, urllib.request, urllib.error
url=os.environ['TARGET_URL']
for _ in range(15):
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            sys.exit(0 if r.status < 500 else 1)
    except urllib.error.HTTPError as e:
        if e.code < 500:
            sys.exit(0)
    except Exception:
        pass
import time; time.sleep(0.4)
sys.exit(1)
PY
  if [ $? -ne 0 ]; then
    echo "启动失败：$name HTTP 服务未就绪"
    exit 1
  fi
}

cleanup_existing
wait_port_free 8787
wait_port_free 8788

start_service ".venv/bin/python src/runner.py" logs/runner.pid logs/runner.out
start_service ".venv/bin/python web/server.py" logs/dashboard.pid logs/dashboard.log
start_service ".venv/bin/python web/toggle_server.py" logs/toggle.pid logs/toggle.log

sleep 2
verify_pid logs/runner.pid runner
verify_pid logs/dashboard.pid dashboard
verify_pid logs/toggle.pid toggle
verify_http "$DASHBOARD_URL" dashboard
verify_http "http://127.0.0.1:8788/api/health" toggle

RUNNER_COUNT=$(pgrep -f "$ROOT/src/runner.py" | wc -l | tr -d ' ')
if [ "$RUNNER_COUNT" != "1" ]; then
  echo "启动失败：检测到 $RUNNER_COUNT 个 runner 进程，要求必须只有 1 个"
  exit 1
fi

if command -v open >/dev/null 2>&1; then
  open "$DASHBOARD_URL" >/dev/null 2>&1 || true
fi

echo "交易监控已启动"
echo "Dashboard: $DASHBOARD_URL"
echo "RUNNER_PID=$(cat logs/runner.pid)"
echo "DASHBOARD_PID=$(cat logs/dashboard.pid)"
echo "TOGGLE_PID=$(cat logs/toggle.pid)"
