from execution_client import HyperliquidExecutionClient


CONFIG = {
    "api": {
        "base_url": "https://api.hyperliquid.xyz",
        "execution_wallet_address": "0xtest",
    }
}


def test_execution_client_builds_payload():
    client = HyperliquidExecutionClient(CONFIG)
    action = {"type": "order", "orders": []}
    payload = client.build_exchange_payload(action)
    assert payload["action"]["type"] == "order"
    assert "nonce" in payload
