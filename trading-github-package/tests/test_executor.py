from executor import TradeExecutor


CONFIG = {
    "account": {"base_equity": 200},
    "risk": {"risk_per_trade_pct": 3.0, "max_risk_per_trade_pct": 8.0},
    "execution": {"enable_live_execution": False},
}


def test_executor_preview_blocks_live_order():
    executor = TradeExecutor(CONFIG)
    result = executor.place_order({
        "direction": "多（HYPE）",
        "entry": "现价附近回踩确认后，参考 40.72",
        "stop_loss": "40.29",
        "take_profit": ["41.16", "41.38"],
        "should_trade": "等待",
    })
    assert result["status"] == "blocked"
    assert result["preview"]["mode"] == "preview_only"
