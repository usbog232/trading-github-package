from __future__ import annotations

from typing import Any, Dict, List

from trade_events import append_event
from trade_record_store import finalize_trade_record


def reconcile_manual_closes(previous_positions: List[Dict[str, Any]], current_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    prev_map: Dict[str, Dict[str, Any]] = {}
    for item in previous_positions or []:
        pos = item.get('position', item) if isinstance(item, dict) else {}
        coin = pos.get('coin')
        if coin:
            prev_map[coin] = pos

    curr_coins = set()
    for item in current_positions or []:
        pos = item.get('position', item) if isinstance(item, dict) else {}
        coin = pos.get('coin')
        if coin:
            curr_coins.add(coin)

    closed = []
    for coin, prev in prev_map.items():
        if coin in curr_coins:
            continue
        pnl = float(prev.get('unrealizedPnl', 0) or 0)
        close_price = float(prev.get('entryPx', 0) or 0)
        finalize_trade_record(
            coin=coin,
            pnl=pnl,
            fee=0.0,
            close_price=close_price,
            close_reason='manual_close_reconciled',
        )
        evt = {
            'kind': 'manual_close_reconciled',
            'status': 'ok',
            'coin': coin,
            'close_price': close_price,
            'pnl': pnl,
        }
        append_event(evt)
        closed.append(evt)
    return closed
