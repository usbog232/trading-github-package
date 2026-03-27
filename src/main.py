import json
import time
from pathlib import Path

from env_loader import load_local_env
from analyzer import TradeAnalyzer
from auto_entry import AutoEntryEngine
from candle_store import CandleStore
from executor import TradeExecutor
from fetcher import HyperliquidFetcher
from position_tracker import build_position_meta, load_tracker, remove_closed_positions, sync_tracker_with_positions
from kill_switch import KillSwitch
from live_execution_probe import LiveExecutionProbe
from live_kill_switch import LiveKillSwitch
from macd_divergence_plan_builder import MacdDivergencePlanBuilder
from reduce_only_probe import ReduceOnlyProbe
from risk_engine import RiskEngine
from strategy_plan_builder import StrategyPlanBuilder
from summary_builder import build_execution_summary
from test_order_guard import TestOrderGuard
from trade_events import latest_events
from trade_record_store import load_trade_records, summarize_trade_records
from manual_close_reconciler import reconcile_manual_closes
from protection_executor import ProtectionExecutor
from fills_importer import import_trade_records_from_fills


def load_config() -> dict:
    root = Path(__file__).resolve().parent.parent
    settings_path = root / "config" / "settings.json"
    example_path = root / "config" / "settings.example.json"
    target = settings_path if settings_path.exists() else example_path
    return json.loads(target.read_text(encoding="utf-8"))


def build_dashboard_payload(config: dict, market_data: dict, account_state: dict, open_orders: list, trade_plan, signal_scores: list, execution_preview: dict, strategy_plan: dict, macd_divergence_plan: dict, kill_switch_preview: dict, live_probe: dict, reduce_only_probe: dict, execution_summary: dict, auto_entry_status: dict, test_order_rules: dict, recent_events: list, allowed: bool, reason: str, position_tracker: dict, timeout_auto_close: dict | None, trade_records: list, trade_record_summary: dict) -> dict:
    api_cfg = config.get("api", {})
    if isinstance(account_state, dict):
        account_state = {
            **account_state,
            "monitor_wallet_address": api_cfg.get("monitor_wallet_address", ""),
            "execution_wallet_address": api_cfg.get("execution_wallet_address", ""),
            "base_equity": config.get('account', {}).get('base_equity', 0),
        }
        if 'error' in account_state and ('perps' in account_state or 'spot' in account_state):
            account_state.pop('error', None)
    return {
        "updated_at": int(time.time()),
        "mode": config.get("mode"),
        "symbols": config.get("symbols", []),
        "analysis": config.get("analysis", {}),
        "execution": config.get("execution", {}),
        "account": config.get("account", {}),
        "risk": config.get("risk", {}),
        "strategy_framework": {
            "big_direction_timeframe": "1h",
            "main_execution_timeframes": ["1h"],
            "timing_timeframe": "15m",
            "regime_rules": {
                "trend": "1h 最近 200 根K线提取主结构与支撑阻力；15m 抓取约 200 根用于入场确认；4h 已从主轮询移除以降低 API 压力",
                "range": "若 1h 无清晰结构，则视作震荡/观望"
            },
            "strategy_map": {
                "bullish_trend": "1h 支撑做多，15m 回踩确认",
                "bearish_trend": "1h 阻力做空，15m 反弹承压确认",
                "range": "1h 震荡观望，不强行交易"
            }
        },
        "leverage_policy": {
            "test_fixed": config.get("execution", {}).get("auto_test_leverage", 5),
            "live_min": config.get("execution", {}).get("auto_live_leverage_min", 5),
            "live_max": config.get("execution", {}).get("auto_live_leverage_max", 8),
            "rr_rules": [
                {"min_rr": 2.0, "max_rr": 2.49, "leverage": config.get("execution", {}).get("auto_live_leverage_min", 5)},
                {"min_rr": 2.5, "max_rr": 2.99, "leverage": min(config.get("execution", {}).get("auto_live_leverage_min", 5) + 1, config.get("execution", {}).get("auto_live_leverage_max", 8))},
                {"min_rr": 3.0, "max_rr": None, "leverage": config.get("execution", {}).get("auto_live_leverage_max", 8)}
            ]
        },
        "market_data": market_data,
        "account_state": account_state,
        "account_snapshot_meta": {
            "updated_at": int(time.time()),
            "positions_count": len((((account_state or {}).get('perps') or {}).get('assetPositions') or [])) if isinstance(account_state, dict) else 0,
            "orders_count": len(open_orders) if isinstance(open_orders, list) else 0,
            "stale": bool(isinstance(account_state, dict) and account_state.get('stale_account_fallback')),
        },
        "open_orders": open_orders,
        "signal_scores": signal_scores,
        "trade_plan": trade_plan.__dict__,
        "execution_preview": execution_preview,
        "strategy_plan": strategy_plan,
        "macd_divergence_plan": macd_divergence_plan,
        "kill_switch_preview": kill_switch_preview,
        "live_execution_probe": live_probe,
        "reduce_only_probe": reduce_only_probe,
        "execution_summary": execution_summary,
        "auto_entry_status": auto_entry_status,
        "test_order_rules": test_order_rules,
        "recent_events": recent_events,
        "risk_check": {
            "allowed": allowed,
            "reason": reason,
        },
        "position_tracker": position_tracker,
        "timeout_auto_close": timeout_auto_close,
        "trade_records": trade_records,
        "trade_record_summary": trade_record_summary,
    }


def _load_previous_dashboard() -> dict:
    dashboard_path = Path(__file__).resolve().parent.parent / "data" / "dashboard" / "latest.json"
    if not dashboard_path.exists():
        return {}
    try:
        return json.loads(dashboard_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _has_valid_account_snapshot(account_state: dict, open_orders: list) -> bool:
    if not isinstance(account_state, dict):
        return False
    has_perps = bool(account_state.get('perps'))
    has_spot = bool(account_state.get('spot'))
    has_orders = isinstance(open_orders, list)
    return (has_perps or has_spot) and has_orders


def run_once(config: dict) -> dict:
    fetcher = HyperliquidFetcher(config)
    candle_store = CandleStore()
    analyzer = TradeAnalyzer(config)
    risk_engine = RiskEngine(config)
    executor = TradeExecutor(config)
    strategy_plan_builder = StrategyPlanBuilder(config)
    macd_plan_builder = MacdDivergencePlanBuilder(config)
    auto_entry_engine = AutoEntryEngine(config)
    kill_switch = KillSwitch(config)
    live_probe_client = LiveExecutionProbe(config)
    live_kill_switch = LiveKillSwitch(config)
    reduce_only_client = ReduceOnlyProbe(config)
    test_guard = TestOrderGuard(config)
    protection_executor = ProtectionExecutor(config)

    previous_dashboard = _load_previous_dashboard()
    previous_market_data = previous_dashboard.get('market_data', {}) if isinstance(previous_dashboard, dict) else {}
    previous_account_state = previous_dashboard.get('account_state', {}) if isinstance(previous_dashboard, dict) else {}
    previous_open_orders = previous_dashboard.get('open_orders', []) if isinstance(previous_dashboard, dict) else []
    previous_updated_at = int(previous_dashboard.get('updated_at', 0) or 0) if isinstance(previous_dashboard, dict) else 0
    previous_perps_state = previous_account_state.get('perps', {}) if isinstance(previous_account_state, dict) else {}
    previous_positions = previous_perps_state.get('assetPositions', []) if isinstance(previous_perps_state, dict) else []
    now_sec = int(time.time())
    now = int(time.time() * 1000)
    timeframes = [tf for tf in config.get("timeframes", ["15m", "1h", "4h"]) if tf != "4h"]
    ranges = {
        "15m": 52 * 60 * 60 * 1000,
        "1h": 220 * 60 * 60 * 1000,
        "4h": 7 * 24 * 60 * 60 * 1000,
        "1d": 30 * 24 * 60 * 60 * 1000,
    }

    refresh_cfg = {
        'mids_seconds': 1,
        'candles_seconds': 5,
        'account_seconds': 10,
    }
    if previous_updated_at > 0:
        elapsed = max(0, now_sec - previous_updated_at)
    else:
        elapsed = 10**9
    should_refresh_mids = elapsed >= refresh_cfg['mids_seconds']
    should_refresh_candles = True
    should_refresh_account = elapsed >= refresh_cfg['account_seconds']

    mids = {}
    if should_refresh_mids:
        try:
            mids = fetcher.fetch_all_mids()
        except Exception:
            mids = {}
    if not mids and isinstance(previous_market_data, dict):
        for frames in previous_market_data.values():
            if isinstance(frames, dict):
                any_snap = next((snap for snap in frames.values() if isinstance(snap, dict) and snap.get('raw', {}).get('mids')), None)
                if any_snap:
                    mids = any_snap.get('raw', {}).get('mids', {})
                    break

    market_data = {}
    for symbol in config.get("symbols", []):
        market_data[symbol] = {}
        for timeframe in timeframes:
            try:
                if timeframe in {'15m', '1h'}:
                    latest_open_time = candle_store.get_latest_open_time(symbol, timeframe)
                    cached_count = candle_store.count_candles(symbol, timeframe)
                    interval_ms = 15 * 60 * 1000 if timeframe == '15m' else 60 * 60 * 1000
                    lookback_ms = 2 * 60 * 60 * 1000 if timeframe == '15m' else 6 * 60 * 60 * 1000
                    cache_healthy = candle_store.is_cache_healthy(symbol, timeframe, now, keep=200)
                    if cached_count < 200 or latest_open_time is None or not cache_healthy:
                        start = now - ranges.get(timeframe, 24 * 60 * 60 * 1000)
                        full_rebuild = True
                    else:
                        start = max(now - lookback_ms, latest_open_time - interval_ms)
                        full_rebuild = False

                    rebuild_status = 'idle'
                    rebuild_error = ''
                    if should_refresh_candles:
                        try:
                            candles = fetcher.fetch_candles(symbol, timeframe, start, now)
                            if candles:
                                if full_rebuild:
                                    candle_store.replace_candles(symbol, timeframe, candles, keep=200)
                                    rebuild_status = 'ok'
                                else:
                                    candle_store.upsert_candles(symbol, timeframe, candles, keep=200)
                            elif full_rebuild:
                                rebuild_status = 'failed'
                                rebuild_error = 'fetch returned empty candles'
                        except Exception as exc:
                            if full_rebuild:
                                rebuild_status = 'failed'
                                rebuild_error = str(exc)

                    cached_candles = candle_store.get_latest_candles(symbol, timeframe, limit=200)
                    if not cached_candles:
                        raise ValueError(f'未缓存到 {symbol} {timeframe} K线数据')
                    last = cached_candles[-1]
                    market_data[symbol][timeframe] = {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'price': float(mids.get(symbol, last.get('c', 0) or 0)),
                        'volume': float(last['v']),
                        'open': float(last['o']),
                        'high': float(last['h']),
                        'low': float(last['l']),
                        'close': float(last['c']),
                        'candles': cached_candles,
                        'raw': {
                            'mids': mids,
                            'candles': cached_candles,
                            'cache': {
                                'enabled': True,
                                'count': len(cached_candles),
                                'latest_open_time': cached_candles[-1]['t'],
                                'timeframe': timeframe,
                                'healthy': candle_store.is_cache_healthy(symbol, timeframe, now, keep=200),
                                'rebuild_mode': full_rebuild,
                                'rebuild_status': rebuild_status,
                                'rebuild_error': rebuild_error,
                            },
                        },
                    }
                    continue
                start = now - ranges.get(timeframe, 24 * 60 * 60 * 1000)
                snapshot = fetcher.fetch_market_snapshot(symbol, timeframe, start, now)
                market_data[symbol][timeframe] = snapshot.__dict__
            except Exception as exc:
                previous_snapshot = previous_market_data.get(symbol, {}).get(timeframe, {}) if isinstance(previous_market_data, dict) else {}
                previous_cache = previous_snapshot.get('raw', {}).get('cache') if isinstance(previous_snapshot, dict) else None
                if previous_cache:
                    market_data[symbol][timeframe] = {
                        **previous_snapshot,
                        'stale_cache_fallback': True,
                        'fallback_reason': str(exc),
                    }
                else:
                    market_data[symbol][timeframe] = {"error": str(exc)}

    monitor_wallet_address = config.get("api", {}).get("monitor_wallet_address", "")
    account_state = previous_account_state if isinstance(previous_account_state, dict) else {}
    open_orders = previous_open_orders if isinstance(previous_open_orders, list) else []
    if monitor_wallet_address and should_refresh_account:
        try:
            fresh_account_state = fetcher.fetch_account_state(monitor_wallet_address)
            fresh_open_orders = fetcher.fetch_open_orders(monitor_wallet_address)
            if isinstance(fresh_account_state, dict) and (fresh_account_state.get('perps') or fresh_account_state.get('spot')):
                account_state = fresh_account_state
            if isinstance(fresh_open_orders, list):
                open_orders = fresh_open_orders
        except Exception as exc:
            if isinstance(account_state, dict) and account_state:
                account_state = {
                    **account_state,
                    'stale_account_fallback': True,
                    'fallback_reason': str(exc),
                }
            else:
                account_state = {"error": str(exc), 'stale_account_fallback': True, 'fallback_reason': str(exc)}

    trade_plan, signal_scores = analyzer.analyze(market_data)
    execution_preview = executor.preview_order(trade_plan.__dict__)
    strategy_plan = strategy_plan_builder.build(trade_plan.__dict__, market_data)
    macd_divergence_plan = macd_plan_builder.build(market_data)
    kill_switch_preview = kill_switch.preview(account_state)
    live_probe = live_probe_client.readiness()
    reduce_only_probe = {}
    if kill_switch_preview.actions:
        first_coin = kill_switch_preview.actions[0].get("coin")
        if first_coin:
            reduce_only_probe = reduce_only_client.build_signed_market_close(first_coin)

    perps_state = account_state.get("perps", {}) if isinstance(account_state, dict) else {}
    current_positions = perps_state.get('assetPositions', []) if isinstance(perps_state, dict) else []
    reconcile_manual_closes(previous_positions, current_positions)
    sync_tracker_with_positions(current_positions)
    active_coins = [((item.get('position', item) if isinstance(item, dict) else {}).get('coin')) for item in current_positions]
    active_coins = [coin for coin in active_coins if coin]
    remove_closed_positions(active_coins)
    position_tracker = build_position_meta(active_coins, max_hold_hours=10)
    expired_positions = [coin for coin, meta in position_tracker.items() if meta.get('expired')]
    timeout_auto_close = None
    if expired_positions:
        timeout_auto_close = live_kill_switch.close_coin(expired_positions[0])
    risk_account_state = {
        "consecutive_losses": 0,
        "open_positions": len(perps_state.get("assetPositions", [])) if isinstance(perps_state, dict) else 0,
    }
    allowed, reason = risk_engine.validate_trade(trade_plan.__dict__, risk_account_state)

    auto_entry_status = auto_entry_engine.evaluate_and_maybe_execute(trade_plan.__dict__, strategy_plan, signal_scores, allowed, macd_divergence_plan)
    if isinstance(account_state, dict):
        current_positions = ((account_state.get('perps') or {}).get('assetPositions') or []) if isinstance(account_state.get('perps'), dict) else []
        for item in current_positions:
            pos = item.get('position', item) if isinstance(item, dict) else {}
            coin = pos.get('coin')
            szi = float(pos.get('szi', 0) or 0)
            if not coin or szi == 0:
                continue
            related_orders = [o for o in (open_orders or []) if o.get('coin') == coin and o.get('reduceOnly')]
            if len(related_orders) >= 2:
                continue
            tracked = (position_tracker or {}).get(coin, {})
            entry_price = float(pos.get('entryPx', 0) or 0)
            is_long = szi > 0
            if tracked.get('side') == 'buy':
                is_long = True
            elif tracked.get('side') == 'sell':
                is_long = False
            stop_loss = 0.0
            take_profit = 0.0
            if coin == 'BTC':
                stop_loss = 68424.0 if is_long else 69149.0
                take_profit = 72012.0 if is_long else 66379.0
            if coin == 'ETH':
                stop_loss = 2045.5 if is_long else 2150.1
                take_profit = 2150.1 if is_long else 2045.5
            if coin == 'HYPE':
                stop_loss = 38.693 if not is_long else 37.739
                take_profit = 37.739 if not is_long else 38.693
            if stop_loss > 0 and take_profit > 0:
                protection_executor.ensure_protection_orders(
                    coin=coin,
                    position_size=abs(szi),
                    is_long=is_long,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
    recent_events = latest_events(10)
    execution_summary = build_execution_summary(recent_events, account_state, live_probe)
    test_order_rules = {
        'enabled': bool(config.get('execution', {}).get('test_order_mode', False)),
        'max_usdc': config.get('execution', {}).get('test_order_max_usdc', 10),
        'max_loss_pct': config.get('execution', {}).get('test_order_max_loss_pct', 1.0),
        'daily_max_loss_usdc': config.get('execution', {}).get('test_order_daily_max_loss_usdc', 5.0),
    }
    if not _has_valid_account_snapshot(account_state, open_orders):
        prev_account = previous_dashboard.get('account_state', {}) if isinstance(previous_dashboard, dict) else {}
        prev_orders = previous_dashboard.get('open_orders', []) if isinstance(previous_dashboard, dict) else []
        if _has_valid_account_snapshot(prev_account, prev_orders):
            account_state = {
                **prev_account,
                'stale_account_fallback': True,
                'fallback_reason': account_state.get('error', 'final_dashboard_guard') if isinstance(account_state, dict) else 'final_dashboard_guard',
            }
            open_orders = prev_orders

    trade_records = load_trade_records()
    if not trade_records:
        try:
            trade_records = import_trade_records_from_fills(config, lookback_days=30)
        except Exception:
            trade_records = load_trade_records()
    trade_record_summary = summarize_trade_records(trade_records)
    dashboard = build_dashboard_payload(config, market_data, account_state, open_orders, trade_plan, signal_scores, execution_preview.__dict__, strategy_plan, macd_divergence_plan, kill_switch_preview.__dict__, live_probe, reduce_only_probe, execution_summary, auto_entry_status, test_order_rules, recent_events, allowed, reason, position_tracker, timeout_auto_close, trade_records, trade_record_summary)
    try:
        fetcher.close()
    except Exception:
        pass
    return dashboard


def main() -> None:
    load_local_env()
    config = load_config()
    dashboard = run_once(config)
    trade_plan = dashboard["trade_plan"]
    risk = dashboard["risk_check"]

    print("=== Trade Plan ===")
    print(f"1. 市场状态: {trade_plan['market_state']}")
    print(f"2. 是否建议交易: {trade_plan['should_trade']}")
    print(f"3. 交易方向: {trade_plan['direction']}")
    print(f"4. 入场位置: {trade_plan['entry']}")
    print(f"5. 止损位置: {trade_plan['stop_loss']}")
    print(f"6. 止盈目标: {trade_plan['take_profit']}")
    print(f"7. 仓位建议: {trade_plan['position_size']}")
    print(f"8. 风险等级: {trade_plan['risk_level']}")
    print(f"9. 备注: {trade_plan['notes']}")
    print(f"\n风控结果: {risk['reason']} | allowed={risk['allowed']}")


if __name__ == "__main__":
    main()
