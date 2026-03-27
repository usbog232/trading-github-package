from typing import Any, Dict

from macd_divergence import detect_macd_divergence
from strategy_plan_builder import _nearest_structure_levels


class MacdDivergencePlanBuilder:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.analysis_cfg = config.get('analysis', {})
        self.macd_cfg = config.get('macd_divergence', {})

    def build(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        min_rr = float(self.analysis_cfg.get('min_auto_rr', 2.0))
        pivot_window = int(self.macd_cfg.get('pivot_window', 3))
        max_age_bars = int(self.macd_cfg.get('max_age_bars', 20))
        entry_zone_buffer_pct = float(self.macd_cfg.get('entry_zone_buffer_pct', 0.0015))

        best = {
            'strategy_type': 'macd_divergence',
            'divergence_detected': False,
            'divergence_side': 'none',
            'symbol': '-',
            'side': 'none',
            'divergence_anchor_time': 0,
            'divergence_anchor_high': 0,
            'divergence_anchor_low': 0,
            'support': 0,
            'resistance': 0,
            'entry': 0,
            'entry_zone_low': 0,
            'entry_zone_high': 0,
            'stop_loss': 0,
            'take_profit_1': 0,
            'risk_reward_tp1': 0,
            'timeframe_source': '1h',
            'plan_complete': False,
            'executable': False,
            'block_reason': 'no_divergence',
            'notes': '当前未识别到可用的 1h MACD 背离计划',
        }
        for symbol, frames in market_data.items():
            h1 = (frames or {}).get('1h', {}) if isinstance(frames, dict) else {}
            candles = h1.get('candles', []) if isinstance(h1, dict) else []
            if len(candles) < 40:
                continue
            div = detect_macd_divergence(candles, pivot_window=pivot_window, max_age_bars=max_age_bars)
            if not div.get('detected'):
                continue
            last_close = float(candles[-1].get('c', 0) or 0)
            support, resistance = _nearest_structure_levels(candles[-200:] if len(candles) >= 200 else candles, last_close)
            side = 'sell' if div['side'] == 'bearish' else 'buy'
            if side == 'sell':
                entry = resistance
                stop = float(div.get('anchor_high', 0) or 0)
                tp1 = support
            else:
                entry = support
                stop = float(div.get('anchor_low', 0) or 0)
                tp1 = resistance
            if entry <= 0 or stop <= 0 or tp1 <= 0:
                continue
            price_risk = abs(entry - stop)
            rr = abs(tp1 - entry) / price_risk if price_risk > 0 else 0.0
            zone_low = entry * (1 - entry_zone_buffer_pct)
            zone_high = entry * (1 + entry_zone_buffer_pct)
            price_in_zone = zone_low <= last_close <= zone_high
            executable = rr >= min_rr and price_in_zone
            plan = {
                'strategy_type': 'macd_divergence',
                'symbol': symbol,
                'side': side,
                'divergence_detected': True,
                'divergence_side': div['side'],
                'divergence_anchor_time': div.get('anchor_time'),
                'divergence_anchor_high': round(float(div.get('anchor_high', 0) or 0), 6),
                'divergence_anchor_low': round(float(div.get('anchor_low', 0) or 0), 6),
                'support': round(support, 6),
                'resistance': round(resistance, 6),
                'entry': round(entry, 6),
                'entry_zone_low': round(zone_low, 6),
                'entry_zone_high': round(zone_high, 6),
                'stop_loss': round(stop, 6),
                'take_profit_1': round(tp1, 6),
                'risk_reward_tp1': round(rr, 3),
                'timeframe_source': '1h',
                'plan_complete': True,
                'executable': executable,
                'block_reason': 'ok' if executable else ('price_not_in_entry_zone' if rr >= min_rr else 'rr_too_low'),
                'notes': f"1h {div['side']} MACD 背离，等待回到结构位再执行",
            }
            if not best.get('divergence_detected') or plan['risk_reward_tp1'] > best.get('risk_reward_tp1', 0):
                best = plan
        return best
