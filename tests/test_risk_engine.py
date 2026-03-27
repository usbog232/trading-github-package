from risk_engine import RiskEngine


def test_risk_engine_allows_up_to_three_positions_but_blocks_same_symbol():
    cfg = {'risk': {'max_open_positions': 3, 'require_stop_loss': True, 'max_consecutive_losses': 3}}
    engine = RiskEngine(cfg)
    trade_plan = {'direction': '多（BTC）', 'stop_loss': '100'}
    account_state = {
        'perps': {
            'assetPositions': [
                {'position': {'coin': 'ETH'}},
                {'position': {'coin': 'HYPE'}},
            ]
        }
    }
    allowed, reason = engine.validate_trade(trade_plan, account_state)
    assert allowed is True
    assert '最多 3 个持仓' in reason

    account_state['perps']['assetPositions'].append({'position': {'coin': 'BTC'}})
    allowed, reason = engine.validate_trade(trade_plan, account_state)
    assert allowed is False
    assert 'BTC 已有持仓' in reason
