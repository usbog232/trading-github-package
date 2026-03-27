import json
import time
from pathlib import Path
from typing import Any, Dict, List

from position_tracker import load_tracker, save_tracker


def _records_path() -> Path:
    p = Path(__file__).resolve().parent.parent / 'data' / 'journal' / 'trade_records.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text('[]', encoding='utf-8')
    return p


def load_trade_records() -> List[Dict[str, Any]]:
    path = _records_path()
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []


def save_trade_records(records: List[Dict[str, Any]]) -> Path:
    path = _records_path()
    path.write_text(json.dumps(records[-300:], ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def append_trade_record(record: Dict[str, Any]) -> Path:
    records = load_trade_records()
    payload = {
        'ts': int(time.time()),
        **record,
    }
    records.append(payload)
    return save_trade_records(records)


def finalize_trade_record(*, coin: str, pnl: float = 0.0, fee: float = 0.0, close_price: float | None = None, close_reason: str = 'close', closed_at_iso: str | None = None) -> Path | None:
    tracker = load_tracker()
    opened = tracker.get(coin)
    if not opened:
        return None
    open_fee = float(opened.get('open_fee', 0) or 0)
    close_fee = float(fee or 0)
    path = append_trade_record({
        'coin': coin,
        'opened_at_iso': opened.get('opened_at_iso'),
        'entry_price': opened.get('entry_price'),
        'side': opened.get('side'),
        'position_size': opened.get('position_size'),
        'strategy_type': opened.get('strategy_type'),
        'pnl': pnl,
        'close_price': close_price,
        'open_fee': open_fee,
        'close_fee': close_fee,
        'fee': open_fee + close_fee,
        'close_reason': close_reason,
        'closed_at_iso': closed_at_iso or time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime()),
    })
    tracker.pop(coin, None)
    save_tracker(tracker)
    return path


def summarize_trade_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_pnl = 0.0
    total_fees = 0.0
    win_count = 0
    for r in records:
        pnl = float(r.get('pnl', 0) or 0)
        total_pnl += pnl
        total_fees += float(r.get('fee', 0) or 0)
        if pnl > 0:
            win_count += 1
    net_pnl = total_pnl - total_fees
    count = len(records)
    return {
        'count': count,
        'gross_pnl': round(total_pnl, 6),
        'total_fees': round(total_fees, 6),
        'net_pnl': round(net_pnl, 6),
        'win_count': win_count,
        'win_rate': round((win_count / count * 100), 2) if count else 0.0,
    }
