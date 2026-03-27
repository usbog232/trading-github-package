from fetcher import HyperliquidFetcher


CONFIG = {
    "api": {
        "base_url": "https://api.hyperliquid.xyz"
    }
}


def test_fetcher_has_info_url():
    fetcher = HyperliquidFetcher(CONFIG)
    assert fetcher.info_url.endswith("/info")
