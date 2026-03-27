import json
import time
from pathlib import Path
from typing import Any, Dict


def _tracker_path() -> Path:
    p = Path(__file__).resolve().parent.parent / 'data' / 'journal' / 'position_tracker.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text('{}', encoding='utf-8')
    return p


def load_tracker() -> Dict[str, Any]:
    path = _tracker_path()
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_tracker(data: Dict[str, Any]) -> Path:
    path = _tracker_path()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def record_open(*, coin: str, strategy_type: str, side: str, entry_price: float, position_size: float, open_fee: float = 0.0) -> Path:
    data = load_tracker()
    now_ts = int(time.time())
    data[coin] = {
        'coin': coin,
        'strategy_type': strategy_type,
        'side': side,
        'entry_price': entry_price,
        'position_size': position_size,
        'open_fee': open_fee,
        'opened_at_ts': now_ts,
        'opened_at_iso': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now_ts)),
    }
    return save_tracker(data)


def remove_closed_positions(active_coins: list[str]) -> Path:
    data = load_tracker()
    active = set(active_coins)
    cleaned = {coin: payload for coin, payload in data.items() if coin in active}
    return save_tracker(cleaned)


def sync_tracker_with_positions(positions: list[dict[str, Any]]) -> Path:
    data = load_tracker()
    now_ts = int(time.time())
    for item in positions:
        pos = item.get('position', item) if isinstance(item, dict) else {}
        coin = pos.get('coin')
        if not coin or coin in data:
            continue
        szi = float(pos.get('szi', 0) or 0)
        data[coin] = {
            'coin': coin,
            'strategy_type': 'recovered_live_position',
            'side': 'buy' if szi > 0 else 'sell',
            'entry_price': float(pos.get('entryPx', 0) or 0),
            'position_size': abs(szi),
            'open_fee': 0.0,
            'opened_at_ts': now_ts,
            'opened_at_iso': time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(now_ts)),
            'recovered_from_live_state': True,
        }
    return save_tracker(data)


def build_position_meta(active_coins: list[str], max_hold_hours: int = 10) -> Dict[str, Any]:
    data = load_tracker()
    now_ts = int(time.time())
    result: Dict[str, Any] = {}
    for coin in active_coins:
        payload = data.get(coin, {})
        opened_at_ts = int(payload.get('opened_at_ts', 0) or 0)
        held_sec = max(0, now_ts - opened_at_ts) if opened_at_ts else 0
        remain_sec = max(0, max_hold_hours * 3600 - held_sec) if opened_at_ts else 0
        result[coin] = {
            **payload,
            'hold_seconds': held_sec,
            'auto_close_countdown_seconds': remain_sec,
            'expired': bool(opened_at_ts and held_sec >= max_hold_hours * 3600),
        }
    return result
