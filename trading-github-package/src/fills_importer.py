from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from hyperliquid.info import Info

from trade_record_store import save_trade_records


def import_trade_records_from_fills(config: Dict[str, Any], lookback_days: int = 30) -> List[Dict[str, Any]]:
    api_cfg = config.get('api', {})
    base_url = api_cfg.get('base_url', 'https://api.hyperliquid.xyz')
    user = api_cfg.get('monitor_wallet_address', '')
    if not user:
        return []

    info = Info(base_url, skip_ws=True)
    end_ms = int(datetime.now().timestamp() * 1000)
    start_ms = end_ms - lookback_days * 24 * 60 * 60 * 1000
    fills = info.user_fills_by_time(user, start_ms, end_ms, aggregate_by_time=False) or []
    fills = sorted(fills, key=lambda x: int(x.get('time', 0) or 0))

    open_lots: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    records: List[Dict[str, Any]] = []

    for f in fills:
        coin = f.get('coin')
        if not coin:
            continue
        side = str(f.get('side', '')).upper()
        px = float(f.get('px', 0) or 0)
        sz = abs(float(f.get('sz', 0) or 0))
        fee = abs(float(f.get('fee', 0) or 0))
        ts = int(f.get('time', 0) or 0)
        iso = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%dT%H:%M:%S') if ts else None
        start_pos = float(f.get('startPosition', 0) or 0)
        closed_pnl = float(f.get('closedPnl', 0) or 0)

        is_opening = (start_pos >= 0 and side == 'B') or (start_pos <= 0 and side == 'A')
        if is_opening:
            open_lots[coin].append({
                'opened_at_iso': iso,
                'entry_price': px,
                'side': 'buy' if side == 'B' else 'sell',
                'position_size': sz,
                'open_fee': fee,
            })
            continue

        lot = open_lots[coin].pop(0) if open_lots[coin] else {
            'opened_at_iso': iso,
            'entry_price': px,
            'side': 'buy' if side == 'A' else 'sell',
            'position_size': sz,
            'open_fee': 0.0,
        }
        records.append({
            'coin': coin,
            'opened_at_iso': lot.get('opened_at_iso'),
            'entry_price': lot.get('entry_price'),
            'close_price': px,
            'side': lot.get('side'),
            'position_size': sz,
            'pnl': closed_pnl,
            'open_fee': float(lot.get('open_fee', 0) or 0),
            'close_fee': fee,
            'fee': float(lot.get('open_fee', 0) or 0) + fee,
            'close_reason': 'fills_import',
            'closed_at_iso': iso,
        })

    save_trade_records(records)
    return records
