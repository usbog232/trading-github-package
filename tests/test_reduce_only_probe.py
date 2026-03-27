from reduce_only_probe import ReduceOnlyProbe


CONFIG = {
    "api": {
        "base_url": "https://api.hyperliquid.xyz",
        "monitor_wallet_address": "0xmonitor",
        "execution_wallet_address": "0xexec",
        "secret_key_env": "HYPERLIQUID_SECRET_KEY",
    }
}


def test_reduce_only_probe_constructs_class():
    probe = ReduceOnlyProbe(CONFIG)
    assert probe.base_url.startswith("https://")
