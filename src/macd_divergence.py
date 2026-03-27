from typing import Any, Dict, List


def _ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    alpha = 2 / (period + 1)
    ema = [values[0]]
    for value in values[1:]:
        ema.append((value * alpha) + (ema[-1] * (1 - alpha)))
    return ema


def compute_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
    if len(closes) < slow:
        return {'macd': [], 'signal': [], 'hist': []}
    fast_ema = _ema(closes, fast)
    slow_ema = _ema(closes, slow)
    macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
    signal_line = _ema(macd_line, signal)
    hist = [m - s for m, s in zip(macd_line, signal_line)]
    return {'macd': macd_line, 'signal': signal_line, 'hist': hist}


def _pivot_highs(candles: List[Dict[str, Any]], window: int = 3) -> List[int]:
    idxs = []
    for i in range(window, len(candles) - window):
        h = float(candles[i].get('h', 0) or 0)
        if all(h >= float(candles[j].get('h', 0) or 0) for j in range(i - window, i + window + 1) if j != i):
            idxs.append(i)
    return idxs


def _pivot_lows(candles: List[Dict[str, Any]], window: int = 3) -> List[int]:
    idxs = []
    for i in range(window, len(candles) - window):
        l = float(candles[i].get('l', 0) or 0)
        if all(l <= float(candles[j].get('l', 0) or 0) for j in range(i - window, i + window + 1) if j != i):
            idxs.append(i)
    return idxs


def detect_macd_divergence(candles: List[Dict[str, Any]], pivot_window: int = 3, max_age_bars: int = 20) -> Dict[str, Any]:
    closes = [float(c.get('c', 0) or 0) for c in candles]
    macd = compute_macd(closes)
    macd_line = macd.get('macd', [])
    if len(candles) < 40 or len(macd_line) != len(candles):
        return {'detected': False, 'side': 'none'}

    highs = _pivot_highs(candles, pivot_window)
    lows = _pivot_lows(candles, pivot_window)
    last_index = len(candles) - 1

    recent_highs = [i for i in highs if last_index - i <= max_age_bars]
    if len(recent_highs) >= 2:
        i1, i2 = recent_highs[-2], recent_highs[-1]
        p1 = float(candles[i1].get('h', 0) or 0)
        p2 = float(candles[i2].get('h', 0) or 0)
        m1 = macd_line[i1]
        m2 = macd_line[i2]
        if p2 >= p1 and m2 < m1:
            return {
                'detected': True,
                'side': 'bearish',
                'pivot_index_1': i1,
                'pivot_index_2': i2,
                'anchor_time': candles[i2].get('t'),
                'anchor_high': p2,
                'anchor_low': float(candles[i2].get('l', 0) or 0),
                'price_1': p1,
                'price_2': p2,
                'macd_1': m1,
                'macd_2': m2,
            }

    recent_lows = [i for i in lows if last_index - i <= max_age_bars]
    if len(recent_lows) >= 2:
        i1, i2 = recent_lows[-2], recent_lows[-1]
        p1 = float(candles[i1].get('l', 0) or 0)
        p2 = float(candles[i2].get('l', 0) or 0)
        m1 = macd_line[i1]
        m2 = macd_line[i2]
        if p2 <= p1 and m2 > m1:
            return {
                'detected': True,
                'side': 'bullish',
                'pivot_index_1': i1,
                'pivot_index_2': i2,
                'anchor_time': candles[i2].get('t'),
                'anchor_high': float(candles[i2].get('h', 0) or 0),
                'anchor_low': p2,
                'price_1': p1,
                'price_2': p2,
                'macd_1': m1,
                'macd_2': m2,
            }

    return {'detected': False, 'side': 'none'}
