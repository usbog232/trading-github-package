from live_execution_probe import LiveExecutionProbe


CONFIG = {
    "api": {
        "base_url": "https://api.hyperliquid.xyz",
        "monitor_wallet_address": "0xmonitor",
        "execution_wallet_address": "0xexec",
        "secret_key_env": "HYPERLIQUID_SECRET_KEY",
    },
    "execution": {
        "enable_live_execution": False,
    },
}


def test_live_execution_probe_shape():
    probe = LiveExecutionProbe(CONFIG)
    data = probe.readiness()
    assert "sdk_available" in data
    assert "has_secret" in data
    assert "exchange_init_ok" in data
