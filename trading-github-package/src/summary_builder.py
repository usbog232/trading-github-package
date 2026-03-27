from typing import Any, Dict, List


def build_execution_summary(events: List[Dict[str, Any]], account_state: Dict[str, Any], live_probe: Dict[str, Any]) -> Dict[str, Any]:
    latest_open = next((e for e in reversed(events) if e.get('kind') == 'market_open_execute'), None)
    latest_close = next((e for e in reversed(events) if e.get('kind') in {'kill_switch_execute', 'manual_close_reconciled', 'timeout_auto_close'}), None)
    latest_protection = next((e for e in reversed(events) if e.get('kind') == 'protection_orders_place'), None)

    perps = account_state.get('perps', {}) if isinstance(account_state, dict) else {}
    positions = perps.get('assetPositions', []) if isinstance(perps, dict) else []

    return {
        'current_position_count': len(positions),
        'is_flat': len(positions) == 0,
        'live_ready': bool(live_probe.get('sdk_available') and live_probe.get('has_secret') and live_probe.get('address_match') and live_probe.get('exchange_init_ok')),
        'latest_open': latest_open,
        'latest_close': latest_close,
        'latest_protection': latest_protection,
    }
