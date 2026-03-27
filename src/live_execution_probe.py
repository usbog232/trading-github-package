import os
from typing import Any, Dict

from eth_account import Account

try:
    from hyperliquid.exchange import Exchange
except Exception:  # pragma: no cover
    Exchange = None


class LiveExecutionProbe:
    """最小真实执行链路准备器：只校验依赖、密钥、SDK初始化能力。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_cfg = config.get("api", {})
        self.exec_cfg = config.get("execution", {})
        self.base_url = self.api_cfg.get("base_url", "https://api.hyperliquid.xyz")
        self.monitor_wallet = self.api_cfg.get("monitor_wallet_address", "")
        self.execution_wallet = self.api_cfg.get("execution_wallet_address", "")
        self.secret_key_env = self.api_cfg.get("secret_key_env", "HYPERLIQUID_SECRET_KEY")

    def readiness(self) -> Dict[str, Any]:
        secret = os.environ.get(self.secret_key_env, "")
        has_secret = bool(secret)
        sdk_available = Exchange is not None
        addr_match = None
        init_ok = False
        error = None

        if has_secret:
            try:
                acct = Account.from_key(secret)
                addr_match = acct.address.lower() == self.execution_wallet.lower() if self.execution_wallet else None
                if sdk_available:
                    _ = Exchange(wallet=acct, base_url=self.base_url, account_address=self.monitor_wallet or None)
                    init_ok = True
            except Exception as exc:
                error = str(exc)

        return {
            "sdk_available": sdk_available,
            "has_secret": has_secret,
            "execution_wallet_configured": bool(self.execution_wallet),
            "monitor_wallet_configured": bool(self.monitor_wallet),
            "address_match": addr_match,
            "exchange_init_ok": init_ok,
            "live_enabled": bool(self.exec_cfg.get("enable_live_execution", False)),
            "error": error,
            "note": "该探针只检查最小真实执行链路准备情况，不会发真实单",
        }

    def build_market_close_plan(self, coin: str, size: str) -> Dict[str, Any]:
        return {
            "coin": coin,
            "size": size,
            "planned_action": "market_close_reduce_only",
            "requires": [
                "execution wallet private key in env",
                "execution wallet address match",
                "exchange init ok",
                "live execution enabled",
            ],
            "note": "仅生成最小真实平仓计划，不执行",
        }
