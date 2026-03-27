from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class TradePlan:
    market_state: str
    should_trade: str
    direction: str
    entry: str
    stop_loss: str
    take_profit: List[str] = field(default_factory=list)
    position_size: str = "light"
    risk_level: str = "medium"
    notes: str = ""


class TradeAnalyzer:
    """1h 结构主导，15m 只做入场节奏确认。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @staticmethod
    def _classify_candle(snapshot: Dict[str, Any]) -> str:
        try:
            open_price = float(snapshot["open"])
            close_price = float(snapshot["close"])
            high = float(snapshot["high"])
            low = float(snapshot["low"])
        except Exception:
            return "unknown"

        if high == low:
            return "flat"
        change_pct = (close_price - open_price) / open_price * 100
        range_pct = (high - low) / open_price * 100
        if abs(change_pct) < 0.2 and range_pct < 0.8:
            return "flat"
        if change_pct >= 0.2:
            return "bullish"
        if change_pct <= -0.2:
            return "bearish"
        return "choppy"

    def score_symbols(self, market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        scored = []
        for symbol, frames in market_data.items():
            if not isinstance(frames, dict):
                continue
            h1 = frames.get('1h', {})
            m15 = frames.get('15m', {})
            h1_state = self._classify_candle(h1) if isinstance(h1, dict) and 'error' not in h1 else 'unknown'
            m15_state = self._classify_candle(m15) if isinstance(m15, dict) and 'error' not in m15 else 'unknown'

            bias = 'neutral'
            score = 0
            setup_quality = 'no-trade'

            if h1_state == 'bullish':
                bias = 'long'
                score = 70
                if m15_state == 'bullish':
                    score = 90
                    setup_quality = 'candidate'
                elif m15_state in {'flat', 'choppy'}:
                    score = 75
                    setup_quality = 'developing'
                else:
                    score = 55
                    setup_quality = 'watch'
            elif h1_state == 'bearish':
                bias = 'short'
                score = 70
                if m15_state == 'bearish':
                    score = 90
                    setup_quality = 'candidate'
                elif m15_state in {'flat', 'choppy'}:
                    score = 75
                    setup_quality = 'developing'
                else:
                    score = 55
                    setup_quality = 'watch'
            else:
                bias = 'neutral'
                score = 20 if m15_state in {'bullish', 'bearish'} else 0
                setup_quality = 'no-trade'

            scored.append({
                'symbol': symbol,
                'score': score,
                'bias': bias,
                'setup_quality': setup_quality,
                'states': {'1h': h1_state, '15m': m15_state},
                'notes': f'1h={h1_state}, 15m={m15_state}',
                'daily_trend': 'unused',
            })

        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored

    def analyze(self, market_data: Dict[str, Any]) -> Tuple[TradePlan, List[Dict[str, Any]]]:
        scored = self.score_symbols(market_data)
        if not scored:
            return TradePlan('信息不足', '否', '无', '无', '无', [], '空仓观望', '高', '当前无优势，不建议交易'), []

        best = scored[0]
        symbol = best['symbol']
        frames = market_data.get(symbol, {})
        h1 = frames.get('1h', {}) if isinstance(frames, dict) else {}
        price = float(h1.get('price', 0) or 0)

        if best['bias'] == 'neutral' or price <= 0:
            return TradePlan('震荡', '否', '无', '无', '无', [], '空仓观望', '高', '1h 无清晰结构，当前不交易'), scored

        if best['setup_quality'] == 'developing':
            action = '观察做多' if best['bias'] == 'long' else '观察做空'
            note = '1h 主结构已形成，15m 还在等确认。'
            return TradePlan('机会形成中', '等待', f'{action}（{symbol}）', f'等待 15m 确认后再处理，参考 {price:.4f}', '待 1h 结构确认', [], '空仓观察', '中', f'{note} 周期状态：{best["states"]}'), scored

        if best['bias'] == 'long':
            stop = float(h1.get('low', 0) or 0)
            risk = price - stop
            if risk <= 0:
                return TradePlan('高风险', '否', '无', '无', '无', [], '空仓观望', '高', '1h 止损结构异常，放弃交易'), scored
            return TradePlan('趋势', '等待', f'多（{symbol}）', f'等待 15m 回踩确认，参考 {price:.4f}', f'{stop:.4f}', [f'{price + risk * 3.0:.4f}', f'{price + risk * 4.0:.4f}'], '轻仓', '中', f'1h 偏多，15m 已配合。先看 1h 结构，再等 15m 回踩。周期状态：{best["states"]}'), scored

        stop = float(h1.get('high', 0) or 0)
        risk = stop - price
        if risk <= 0:
            return TradePlan('高风险', '否', '无', '无', '无', [], '空仓观望', '高', '1h 止损结构异常，放弃交易'), scored
        return TradePlan('趋势', '等待', f'空（{symbol}）', f'等待 15m 反弹承压确认，参考 {price:.4f}', f'{stop:.4f}', [f'{price - risk * 3.0:.4f}', f'{price - risk * 4.0:.4f}'], '轻仓', '中', f'1h 偏空，15m 已配合。先看 1h 结构，再等 15m 反弹承压。周期状态：{best["states"]}'), scored
