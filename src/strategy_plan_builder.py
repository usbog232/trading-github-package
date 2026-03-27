from typing import Any, Dict, List


class StrategyPlanBuilder:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_cfg = config.get('account', {})
        self.risk_cfg = config.get('risk', {})
        self.exec_cfg = config.get('execution', {})
        self.analysis_cfg = config.get('analysis', {})

    def build(self, trade_plan: Dict[str, Any], market_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        strategy_type = str(trade_plan.get('strategy_type', 'default'))
        direction = str(trade_plan.get('direction', ''))
        symbol = _extract_symbol(direction)
        side = 'buy' if '多' in direction else ('sell' if '空' in direction else 'none')

        structure = self._derive_1h_levels(symbol, side, market_data or {})
        entry = structure['entry'] if structure['entry'] > 0 else _to_float(trade_plan.get('entry'))
        stop_loss = structure['stop_loss'] if structure['stop_loss'] > 0 else _to_float(trade_plan.get('stop_loss'))
        tp1 = structure['take_profit_1'] if structure['take_profit_1'] > 0 else _to_float((trade_plan.get('take_profit') or [0])[0])
        tp2_default = (trade_plan.get('take_profit') or [0, 0])
        tp2 = structure['take_profit_2'] if structure['take_profit_2'] > 0 else _to_float(tp2_default[1] if len(tp2_default) > 1 else 0)

        equity = float(self.account_cfg.get('base_equity', 0))
        risk_pct = float(self.risk_cfg.get('risk_per_trade_pct', 3.0)) / 100.0
        risk_amount = equity * risk_pct
        max_risk_pct = float(self.risk_cfg.get('max_risk_per_trade_pct', 8.0)) / 100.0
        max_risk_amount = equity * max_risk_pct
        min_rr = float(self.analysis_cfg.get('min_auto_rr', 2.0))
        leverage = self._determine_leverage(rr_tp1=0.0, symbol=symbol)
        max_notional = equity * leverage if equity > 0 and leverage > 0 else 0.0
        max_margin_usage_pct = float(self.exec_cfg.get('max_margin_usage_pct', 100.0)) / 100.0
        max_margin = equity * max_margin_usage_pct if equity > 0 else 0.0

        price_risk = abs(entry - stop_loss) if entry and stop_loss else 0.0
        risk_quantity = risk_amount / price_risk if price_risk > 0 else 0.0
        margin_cap_quantity = (max_notional / entry) if entry > 0 and max_notional > 0 else 0.0
        quantity = min(risk_quantity, margin_cap_quantity) if risk_quantity > 0 and margin_cap_quantity > 0 else risk_quantity
        position_value = quantity * entry if entry > 0 else 0.0
        rr_tp1 = abs(tp1 - entry) / price_risk if price_risk > 0 and tp1 > 0 else 0.0
        rr_tp2 = abs(tp2 - entry) / price_risk if price_risk > 0 and tp2 > 0 else 0.0
        leverage = self._determine_leverage(rr_tp1=rr_tp1, symbol=symbol)
        max_notional = equity * leverage if equity > 0 and leverage > 0 else 0.0
        margin_cap_quantity = (max_notional / entry) if entry > 0 and max_notional > 0 else 0.0
        quantity = min(risk_quantity, margin_cap_quantity) if risk_quantity > 0 and margin_cap_quantity > 0 else risk_quantity
        position_value = quantity * entry if entry > 0 else 0.0
        estimated_margin = (position_value / leverage) if leverage > 0 else 0.0

        plan_complete = all([symbol, side != 'none', entry > 0, stop_loss > 0, tp1 > 0])
        structure_ok = bool(structure.get('structure_clear')) and _structure_allows_target(side, entry, tp1, structure['support'], structure['resistance'])
        margin_ok = estimated_margin <= max_margin if max_margin > 0 else True
        executable = plan_complete and structure_ok and risk_amount <= max_risk_amount and quantity > 0 and rr_tp1 >= min_rr and margin_ok
        block_reason = 'ok' if executable else _block_reason(plan_complete, quantity, rr_tp1, risk_amount, max_risk_amount, min_rr, structure_ok, margin_ok)

        return {
            'strategy_type': strategy_type,
            'symbol': symbol or '-', 'side': side,
            'entry': round(entry, 6) if entry else 0,
            'stop_loss': round(stop_loss, 6) if stop_loss else 0,
            'take_profit_1': round(tp1, 6) if tp1 else 0,
            'take_profit_2': round(tp2, 6) if tp2 else 0,
            'support': round(structure['support'], 6) if structure['support'] else 0,
            'resistance': round(structure['resistance'], 6) if structure['resistance'] else 0,
            'timeframe_source': '1h',
            'raw_structure_stop': round(float(structure.get('raw_structure_stop', 0) or 0), 6),
            'atr_buffer': round(float(structure.get('atr_buffer', 0) or 0), 6),
            'buffered_stop_loss': round(float(structure.get('buffered_stop_loss', 0) or 0), 6),
            'risk_amount': round(risk_amount, 6),
            'max_risk_amount': round(max_risk_amount, 6),
            'quantity_estimate': round(quantity, 6),
            'position_value': round(position_value, 6),
            'max_notional_value': round(max_notional, 6),
            'estimated_margin': round(estimated_margin, 6),
            'max_margin_allowed': round(max_margin, 6),
            'risk_reward_tp1': round(rr_tp1, 3),
            'risk_reward_tp2': round(rr_tp2, 3),
            'min_rr_required': round(min_rr, 3),
            'leverage': leverage,
            'plan_complete': plan_complete,
            'executable': executable,
            'block_reason': block_reason,
            'source': '1h_structure_only',
        }

    def _determine_leverage(self, *, rr_tp1: float, symbol: str) -> int:
        test_leverage = int(self.exec_cfg.get('auto_test_leverage', 5))
        live_min = int(self.exec_cfg.get('auto_live_leverage_min', 5))
        live_max = int(self.exec_cfg.get('auto_live_leverage_max', 8))
        live_enabled = bool(self.exec_cfg.get('enable_auto_live_entries', False))
        if not live_enabled:
            return max(5, test_leverage)
        lev = live_min
        if rr_tp1 >= 4.0:
            lev = live_max
        elif rr_tp1 >= 3.5:
            lev = min(live_max, live_min + 1)
        if symbol == 'HYPE':
            lev = max(5, lev - 1)
        return max(5, lev)

    def _derive_1h_levels(self, symbol: str, side: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = (market_data.get(symbol, {}) or {}).get('1h', {}) if symbol else {}
        candles = snapshot.get('candles', []) if isinstance(snapshot, dict) else []
        if not candles:
            return {'entry': 0.0, 'stop_loss': 0.0, 'take_profit_1': 0.0, 'take_profit_2': 0.0, 'support': 0.0, 'resistance': 0.0, 'structure_clear': False}

        recent = candles[-200:] if len(candles) >= 200 else candles
        last_close = float(recent[-1].get('c', 0) or 0)
        atr = _atr(recent, period=14)
        support, resistance, structure_clear = _confirmed_structure_levels(recent, last_close, side)
        atr_buffer = atr * 0.65 if atr > 0 else last_close * 0.003

        if side == 'buy' and support > 0 and last_close > 0 and structure_clear:
            stop_loss = max(0.0, support - atr_buffer)
            risk = last_close - stop_loss
            return {
                'entry': last_close,
                'stop_loss': stop_loss,
                'take_profit_1': last_close + risk * 2.0,
                'take_profit_2': last_close + risk * 3.0,
                'support': support,
                'resistance': resistance,
                'raw_structure_stop': support,
                'atr_buffer': atr_buffer,
                'buffered_stop_loss': stop_loss,
                'structure_clear': True,
            }
        if side == 'sell' and resistance > 0 and last_close > 0 and structure_clear:
            stop_loss = resistance + atr_buffer
            risk = stop_loss - last_close
            return {
                'entry': last_close,
                'stop_loss': stop_loss,
                'take_profit_1': last_close - risk * 2.0,
                'take_profit_2': last_close - risk * 3.0,
                'support': support,
                'resistance': resistance,
                'raw_structure_stop': resistance,
                'atr_buffer': atr_buffer,
                'buffered_stop_loss': stop_loss,
                'structure_clear': True,
            }
        return {'entry': 0.0, 'stop_loss': 0.0, 'take_profit_1': 0.0, 'take_profit_2': 0.0, 'support': support, 'resistance': resistance, 'structure_clear': False}


def _nearest_structure_levels(candles: List[Dict[str, Any]], last_close: float) -> tuple[float, float]:
    support, resistance, _ = _confirmed_structure_levels(candles, last_close, side='buy')
    return support, resistance


def _confirmed_structure_levels(candles: List[Dict[str, Any]], last_close: float, side: str, pivot_window: int = 3) -> tuple[float, float, bool]:
    lows = []
    highs = []
    for i in range(pivot_window, len(candles) - pivot_window):
        low = float(candles[i].get('l', 0) or 0)
        high = float(candles[i].get('h', 0) or 0)
        left = candles[i - pivot_window:i]
        right = candles[i + 1:i + 1 + pivot_window]
        if low > 0 and all(low <= float(x.get('l', 0) or 0) for x in left + right):
            lows.append(low)
        if high > 0 and all(high >= float(x.get('h', 0) or 0) for x in left + right):
            highs.append(high)

    support_candidates = [x for x in lows if x < last_close]
    resistance_candidates = [x for x in highs if x > last_close]
    support = max(support_candidates) if support_candidates else 0.0
    resistance = min(resistance_candidates) if resistance_candidates else 0.0
    structure_clear = bool((side == 'buy' and support > 0 and resistance > last_close) or (side == 'sell' and resistance > 0 and support < last_close))
    return support, resistance, structure_clear


def _atr(candles: List[Dict[str, Any]], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for prev, cur in zip(candles[:-1], candles[1:]):
        high = float(cur.get('h', 0) or 0)
        low = float(cur.get('l', 0) or 0)
        prev_close = float(prev.get('c', 0) or 0)
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    recent = trs[-period:]
    return sum(recent) / len(recent) if recent else 0.0


def _extract_symbol(direction: str) -> str:
    return direction.split('（')[-1].replace('）', '') if '（' in direction else ''


def _to_float(value: Any) -> float:
    text = str(value or '0')
    buf = []
    started = False
    for ch in text:
        if ch in '0123456789.-':
            buf.append(ch)
            started = True
        elif started:
            break
    try:
        return float(''.join(buf)) if buf else 0.0
    except Exception:
        return 0.0


def _structure_allows_target(side: str, entry: float, tp1: float, support: float, resistance: float) -> bool:
    if side == 'buy' and resistance > 0:
        return resistance >= tp1
    if side == 'sell' and support > 0:
        return support <= tp1
    return True


def _block_reason(plan_complete: bool, quantity: float, rr_tp1: float, risk_amount: float, max_risk_amount: float, min_rr: float, structure_ok: bool, margin_ok: bool) -> str:
    if not plan_complete:
        return 'plan_incomplete'
    if not structure_ok:
        return 'structure_target_insufficient'
    if quantity <= 0:
        return 'size_invalid'
    if rr_tp1 < min_rr:
        return 'rr_too_low'
    if risk_amount > max_risk_amount:
        return 'risk_above_max'
    if not margin_ok:
        return 'margin_above_limit'
    return 'blocked'
