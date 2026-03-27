from protection_executor import ProtectionExecutor


CONFIG = {
    'api': {
        'base_url': 'https://api.hyperliquid.xyz',
        'monitor_wallet_address': '0xmonitor',
        'execution_wallet_address': '0xexec',
        'secret_key_env': 'HYPERLIQUID_SECRET_KEY',
    },
    'execution': {
        'enable_live_execution': True,
    },
}


def test_protection_executor_constructs():
    ex = ProtectionExecutor(CONFIG)
    assert ex.base_url.startswith('https://')
