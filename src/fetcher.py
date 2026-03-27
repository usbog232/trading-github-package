from dataclasses import dataclass
from typing import Any, Dict, List

import requests


@dataclass
class MarketSnapshot:
    symbol: str
    timeframe: str
    price: float
    volume: float
    open: float
    high: float
    low: float
    close: float
    candles: List[Dict[str, Any]]
    raw: Dict[str, Any]


class HyperliquidFetcher:
    """第一版：接入 Hyperliquid Info API 获取基础行情与账户状态。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_cfg = config.get("api", {})
        self.base_url = self.api_cfg.get("base_url", "https://api.hyperliquid.xyz")
        self.info_url = f"{self.base_url}/info"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def close(self) -> None:
        try:
            self.session.close()
        except Exception:
            pass

    def _post_info(self, payload: Dict[str, Any]) -> Any:
        resp = self.session.post(self.info_url, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def fetch_meta(self) -> Dict[str, Any]:
        return self._post_info({"type": "meta"})

    def fetch_all_mids(self) -> Dict[str, str]:
        return self._post_info({"type": "allMids"})

    def fetch_candles(self, symbol: str, timeframe: str, start_time_ms: int, end_time_ms: int) -> List[Dict[str, Any]]:
        payload = {
            "type": "candleSnapshot",
            "req": {
                "coin": symbol,
                "interval": timeframe,
                "startTime": start_time_ms,
                "endTime": end_time_ms,
            },
        }
        return self._post_info(payload)

    def fetch_market_snapshot(self, symbol: str, timeframe: str, start_time_ms: int, end_time_ms: int) -> MarketSnapshot:
        mids = self.fetch_all_mids()
        candles = self.fetch_candles(symbol, timeframe, start_time_ms, end_time_ms)
        if not candles:
            raise ValueError(f"未获取到 {symbol} {timeframe} K线数据")

        last = candles[-1]
        price = float(mids.get(symbol, last.get("c", 0)))
        return MarketSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            price=price,
            volume=float(last["v"]),
            open=float(last["o"]),
            high=float(last["h"]),
            low=float(last["l"]),
            close=float(last["c"]),
            candles=candles,
            raw={"mids": mids, "candles": candles},
        )

    def fetch_perps_account_state(self, wallet_address: str) -> Dict[str, Any]:
        return self._post_info({"type": "clearinghouseState", "user": wallet_address})

    def fetch_spot_account_state(self, wallet_address: str) -> Dict[str, Any]:
        return self._post_info({"type": "spotClearinghouseState", "user": wallet_address})

    def fetch_account_state(self, wallet_address: str) -> Dict[str, Any]:
        perps = self.fetch_perps_account_state(wallet_address)
        spot = self.fetch_spot_account_state(wallet_address)
        return {
            "perps": perps,
            "spot": spot,
        }

    def fetch_open_orders(self, wallet_address: str) -> List[Dict[str, Any]]:
        return self._post_info({"type": "openOrders", "user": wallet_address})
