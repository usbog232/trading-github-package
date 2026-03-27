#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")"

python3 - <<'PY'
import json
from pathlib import Path
p = Path('config/settings.json')
config = json.loads(p.read_text(encoding='utf-8'))
exec_cfg = config.setdefault('execution', {})
exec_cfg['enable_live_execution'] = True
exec_cfg['enable_auto_test_entries'] = True
exec_cfg['enable_auto_live_entries'] = False
exec_cfg['test_order_mode'] = True
p.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
print('已切换为半自动模式：实盘执行开启，自动测试单开启，自动正常单关闭。')
PY

./start_trading.sh

echo "半自动模式已启动。"
echo "- 实盘执行: 开"
echo "- 自动测试单: 开"
echo "- 自动正常单: 关"
