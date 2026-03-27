from live_open_executor import LiveOpenExecutor


def test_live_open_executor_non_test_mode_does_not_require_test_guard():
    cfg = {
        'api': {
            'base_url': 'https://api.hyperliquid.xyz',
            'monitor_wallet_address': '0xmonitor',
            'execution_wallet_address': '0xexec',
            'secret_key_env': 'HYPERLIQUID_SECRET_KEY',
        },
        'execution': {
            'enable_live_execution': True,
            'test_order_mode': False,
        },
        'account': {'base_equity': 200},
    }
    ex = LiveOpenExecutor(cfg)
    assert ex.exec_cfg.get('test_order_mode') is False
