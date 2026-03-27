from analyzer import TradeAnalyzer


CONFIG = {}


def test_analyzer_returns_plan():
    analyzer = TradeAnalyzer(CONFIG)
    plan, scores = analyzer.analyze({})
    assert plan.should_trade in {"否", "等待", "是"}
    assert isinstance(plan.notes, str)
    assert isinstance(scores, list)


def test_analyzer_1h_long_15m_bullish_is_candidate():
    analyzer = TradeAnalyzer(CONFIG)
    market_data = {
        'ETH': {
            '15m': {'open': 100, 'close': 102, 'high': 103, 'low': 99, 'price': 102},
            '1h': {'open': 100, 'close': 103, 'high': 104, 'low': 99, 'price': 103},
        }
    }
    plan, scores = analyzer.analyze(market_data)
    assert scores[0]['bias'] == 'long'
    assert scores[0]['setup_quality'] == 'candidate'
    assert '多' in plan.direction


def test_analyzer_1h_short_15m_flat_is_developing():
    analyzer = TradeAnalyzer(CONFIG)
    market_data = {
        'BTC': {
            '15m': {'open': 100, 'close': 100.01, 'high': 100.2, 'low': 99.9, 'price': 100.01},
            '1h': {'open': 100, 'close': 97, 'high': 100, 'low': 96, 'price': 97},
        }
    }
    plan, scores = analyzer.analyze(market_data)
    assert scores[0]['bias'] == 'short'
    assert scores[0]['setup_quality'] == 'developing'
    assert '观察做空' in plan.direction
