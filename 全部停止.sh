#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

python3 - <<'PY'
import json
from pathlib import Path
p = Path('config/settings.json')
config = json.loads(p.read_text(encoding='utf-8'))
exec_cfg = config.setdefault('execution', {})
exec_cfg['enable_live_execution'] = False
exec_cfg['enable_auto_test_entries'] = False
exec_cfg['enable_auto_live_entries'] = False
p.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
print('已关闭所有自动/实盘开关。')
PY

./stop_trading.sh

echo "已停止全部 trading 组件（含平仓、runner、dashboard、toggle）。"
