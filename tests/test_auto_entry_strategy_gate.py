from auto_entry import AutoEntryEngine


def test_auto_entry_blocks_when_strategy_plan_not_executable():
    cfg = {
        'execution': {
            'enable_auto_test_entries': True,
            'enable_auto_live_entries': False,
        },
        'analysis': {'min_signal_score': 70, 'min_auto_rr': 1.0},
    }
    engine = AutoEntryEngine(cfg)
    result = engine.evaluate_and_maybe_execute(
        {'should_trade': '等待', 'direction': '多（ETH）', 'stop_loss': '100', 'take_profit': ['120']},
        {'plan_complete': True, 'executable': False, 'risk_reward_tp1': 0.8, 'quantity_estimate': 1.0, 'block_reason': 'rr_too_low'},
        [{'symbol': 'ETH', 'score': 90, 'setup_quality': 'candidate'}],
        True,
    )
    assert result['triggered'] is False
    assert 'strategy blocked' in result['reason']
