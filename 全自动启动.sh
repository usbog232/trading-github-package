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
exec_cfg['enable_auto_test_entries'] = False
exec_cfg['enable_auto_live_entries'] = True
exec_cfg['test_order_mode'] = False
p.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
print('已切换为全自动模式：实盘执行开启，自动测试单关闭，自动正常单开启。')
PY

./start_trading.sh

echo "全自动模式已启动。"
echo "- 实盘执行: 开"
echo "- 自动测试单: 关"
echo "- 自动正常单: 开"
