import os
import time
from typing import Any, Dict

from eth_account import Account

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils.signing import get_timestamp_ms, order_request_to_order_wire, order_wires_to_order_action, sign_l1_action


class ReduceOnlyProbe:
    """最小真实执行链路准备：本地构造并签名 reduce-only 平仓请求，不发单。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        api_cfg = config.get("api", {})
        self.base_url = api_cfg.get("base_url", "https://api.hyperliquid.xyz")
        self.monitor_wallet = api_cfg.get("monitor_wallet_address", "")
        self.execution_wallet = api_cfg.get("execution_wallet_address", "")
        self.secret_key_env = api_cfg.get("secret_key_env", "HYPERLIQUID_SECRET_KEY")

    def build_signed_market_close(self, coin: str) -> Dict[str, Any]:
        secret = os.environ.get(self.secret_key_env, "")
        if not secret:
            return {"status": "blocked", "reason": f"missing env {self.secret_key_env}"}

        acct = Account.from_key(secret)
        if self.execution_wallet and acct.address.lower() != self.execution_wallet.lower():
            return {
                "status": "blocked",
                "reason": "execution wallet does not match private key",
                "derived_address": acct.address,
            }

        exchange = Exchange(wallet=acct, base_url=self.base_url, account_address=self.monitor_wallet or None)
        info = Info(self.base_url, skip_ws=True)
        positions = info.user_state(self.monitor_wallet or acct.address)["assetPositions"]

        target = None
        for item in positions:
            pos = item["position"]
            if pos.get("coin") == coin:
                target = pos
                break
        if not target:
            return {"status": "blocked", "reason": f"no open position for {coin}"}

        szi = float(target["szi"])
        if szi == 0:
            return {"status": "blocked", "reason": f"position size is zero for {coin}"}

        close_is_buy = True if szi < 0 else False
        size = abs(szi)
        px = exchange._slippage_price(coin, close_is_buy, Exchange.DEFAULT_SLIPPAGE, None)
        asset = exchange.info.name_to_asset(coin)
        order_request = {
            "coin": coin,
            "is_buy": close_is_buy,
            "sz": size,
            "limit_px": px,
            "order_type": {"limit": {"tif": "Ioc"}},
            "reduce_only": True,
        }
        order_wire = order_request_to_order_wire(order_request, asset)
        action = order_wires_to_order_action([order_wire], None, "na")
        nonce = get_timestamp_ms()
        signature = sign_l1_action(acct, action, None, nonce, None, True)

        can_submit_live = True
        blockers = []
        if not self.execution_wallet:
            can_submit_live = False
            blockers.append("execution wallet not configured")
        if acct.address.lower() != self.execution_wallet.lower():
            can_submit_live = False
            blockers.append("private key does not match execution wallet")

        return {
            "status": "ready",
            "monitor_wallet": self.monitor_wallet,
            "execution_wallet": self.execution_wallet,
            "derived_address": acct.address,
            "coin": coin,
            "position_size": target["szi"],
            "entry_price": target.get("entryPx"),
            "position_value": target.get("positionValue"),
            "unrealized_pnl": target.get("unrealizedPnl"),
            "close_is_buy": close_is_buy,
            "limit_px": px,
            "nonce": nonce,
            "action": action,
            "signature": signature,
            "signature_ready": bool(signature),
            "can_submit_live": can_submit_live,
            "blockers": blockers,
            "note": "local signature only; not submitted to /exchange",
        }
