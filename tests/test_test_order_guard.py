from test_order_guard import TestOrderGuard


CONFIG = {
    'account': {'base_equity': 200},
    'execution': {
        'test_order_mode': True,
        'test_order_max_usdc': 15,
        'test_order_max_loss_pct': 1.0,
        'test_order_daily_max_loss_usdc': 5.0,
    }
}


def test_test_order_guard_allows_small_order():
    ok, reasons = TestOrderGuard(CONFIG).validate(order_value_usdc=10, stop_loss_pct=1)
    assert ok is True
    assert reasons == []
