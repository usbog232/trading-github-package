from auto_entry import AutoEntryEngine


def test_auto_entry_disabled_by_default():
    cfg = {
        'execution': {
            'enable_auto_test_entries': False,
            'enable_auto_live_entries': False,
        },
        'analysis': {'min_signal_score': 70},
    }
    engine = AutoEntryEngine(cfg)
    result = engine.evaluate_and_maybe_execute(
        {'should_trade': '等待', 'direction': '多（ETH）', 'stop_loss': '100', 'take_profit': ['120']},
        {'plan_complete': True, 'executable': True, 'risk_reward_tp1': 1.5, 'quantity_estimate': 1.0, 'block_reason': 'ok'},
        [{'symbol': 'ETH', 'score': 90, 'setup_quality': 'candidate'}],
        True,
    )
    assert result['armed_mode'] == 'off'
    assert result['triggered'] is False
