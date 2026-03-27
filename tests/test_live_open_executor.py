from live_open_executor import LiveOpenExecutor


CONFIG = {
    'api': {
        'base_url': 'https://api.hyperliquid.xyz',
        'monitor_wallet_address': '0xmonitor',
        'execution_wallet_address': '0xexec',
        'secret_key_env': 'HYPERLIQUID_SECRET_KEY',
    },
    'execution': {
        'enable_live_execution': True,
        'test_order_mode': True,
        'test_order_max_usdc': 15,
        'test_order_max_loss_pct': 1.0,
        'test_order_daily_max_loss_usdc': 5.0,
    },
    'account': {
        'base_equity': 200,
    }
}


def test_live_open_executor_constructs():
    ex = LiveOpenExecutor(CONFIG)
    assert ex.base_url.startswith('https://')
