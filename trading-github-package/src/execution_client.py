import time
from typing import Any, Dict

import requests


class HyperliquidExecutionClient:
    """真实执行骨干链路的最小骨架。

    当前只负责：
    - 构造 exchange 请求外壳
    - 输出 dry-run payload
    - 保持真实签名和真实发单禁用
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        api_cfg = config.get("api", {})
        self.base_url = api_cfg.get("base_url", "https://api.hyperliquid.xyz")
        self.exchange_url = f"{self.base_url}/exchange"
        self.execution_wallet_address = api_cfg.get("execution_wallet_address", "")
        self.secret_key_env = api_cfg.get("secret_key_env", "HYPERLIQUID_SECRET_KEY")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def build_order_wire(self, *, coin: str, is_buy: bool, sz: str, limit_px: str, order_type: Dict[str, Any], reduce_only: bool = False) -> Dict[str, Any]:
        return {
            "coin": coin,
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": limit_px,
            "order_type": order_type,
            "reduce_only": reduce_only,
        }

    def build_exchange_payload(self, action: Dict[str, Any], signature: Dict[str, Any] | None = None, nonce: int | None = None) -> Dict[str, Any]:
        return {
            "action": action,
            "nonce": nonce or int(time.time() * 1000),
            "signature": signature or {"r": "", "s": "", "v": 0},
        }

    def dry_run_order(self, order_action: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.build_exchange_payload(action=order_action)
        return {
            "status": "dry_run",
            "exchange_url": self.exchange_url,
            "execution_wallet_address": self.execution_wallet_address,
            "payload": payload,
            "note": "真实签名和真实发单尚未启用",
        }
