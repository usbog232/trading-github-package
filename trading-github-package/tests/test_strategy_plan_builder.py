from strategy_plan_builder import StrategyPlanBuilder


def test_strategy_plan_builder_uses_1h_only_structure():
    cfg = {
        'account': {'base_equity': 200},
        'risk': {'risk_per_trade_pct': 3.0, 'max_risk_per_trade_pct': 8.0},
        'execution': {'auto_test_leverage': 5, 'auto_live_leverage_min': 5, 'auto_live_leverage_max': 8, 'enable_auto_live_entries': True},
        'analysis': {'min_auto_rr': 3.0},
    }
    builder = StrategyPlanBuilder(cfg)
    market_data = {
        'ETH': {
            '15m': {
                'candles': [
                    {'t': 1, 'i': '15m', 'l': '99', 'h': '102', 'c': '100'}
                ]
            },
            '1h': {
                'candles': [
                    {'t': 1, 'i': '1h', 'l': '95', 'h': '105', 'c': '100'},
                    {'t': 2, 'i': '1h', 'l': '96', 'h': '106', 'c': '101'},
                    {'t': 3, 'i': '1h', 'l': '97', 'h': '107', 'c': '102'},
                    {'t': 4, 'i': '1h', 'l': '98', 'h': '108', 'c': '103'},
                ]
            }
        }
    }
    plan = builder.build({'direction': '多（ETH）'}, market_data)
    assert plan['timeframe_source'] == '1h'
    assert plan['support'] == 98.0
    assert plan['resistance'] == 105.0
    assert plan['leverage'] >= 5
