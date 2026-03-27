from kill_switch import KillSwitch


CONFIG = {
    "execution": {"enable_live_execution": False},
    "api": {"execution_wallet_address": "0xtest"},
}


def test_kill_switch_preview_only_when_disabled():
    ks = KillSwitch(CONFIG)
    result = ks.execute({"perps": {"assetPositions": []}})
    assert result["status"] == "blocked"
    assert result["preview"]["mode"] == "preview_only"
