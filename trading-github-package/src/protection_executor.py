import os
import time
from typing import Any, Dict

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

from protection_state import load_protection_state, save_protection_state
from trade_events import append_event


class ProtectionExecutor:
    """开仓后自动提交止损/止盈保护单。"""

    def ensure_protection_orders(self, *, coin: str, position_size: float, is_long: bool, stop_loss: float, take_profit: float) -> Dict[str, Any]:
        return self.place_protection_orders(
            coin=coin,
            position_size=position_size,
            is_long=is_long,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_cfg = config.get('api', {})
        self.exec_cfg = config.get('execution', {})
        self.base_url = self.api_cfg.get('base_url', 'https://api.hyperliquid.xyz')
        self.monitor_wallet = self.api_cfg.get('monitor_wallet_address', '')
        self.execution_wallet = self.api_cfg.get('execution_wallet_address', '')
        self.secret_key_env = self.api_cfg.get('secret_key_env', 'HYPERLIQUID_SECRET_KEY')

    def place_protection_orders(self, *, coin: str, position_size: float, is_long: bool, stop_loss: float, take_profit: float) -> Dict[str, Any]:
        state = load_protection_state()
        desired = {
            'coin': coin,
            'position_size': round(abs(position_size), 8),
            'is_long': bool(is_long),
            'stop_loss': round(float(stop_loss), 8),
            'take_profit': round(float(take_profit), 8),
        }
        prev = state.get(coin)
        secret = os.environ.get(self.secret_key_env, '')
        if not secret:
            return {'status': 'blocked', 'reason': f'missing env {self.secret_key_env}'}

        acct = Account.from_key(secret)
        exchange = Exchange(wallet=acct, base_url=self.base_url, account_address=self.monitor_wallet)
        info = Info(self.base_url, skip_ws=True)
        close_is_buy = not is_long
        sz = abs(position_size)

        existing = info.open_orders(self.monitor_wallet) or []
        coin_reduce_orders = [o for o in existing if o.get('coin') == coin and o.get('reduceOnly')]
        prices = {str(o.get('limitPx')) for o in coin_reduce_orders}
        expected = {str(stop_loss), str(take_profit)}
        if prev == desired and expected.issubset(prices):
            return {
                'status': 'ok',
                'skipped': True,
                'reason': 'protection already in sync',
                'existing_orders': coin_reduce_orders,
            }

        cancelled = []
        for order in coin_reduce_orders:
            oid = order.get('oid')
            if oid is not None:
                try:
                    cancelled.append(exchange.cancel(coin, int(oid)))
                except Exception:
                    pass
        time.sleep(0.6)

        sl_order = exchange.order(
            coin,
            close_is_buy,
            sz,
            stop_loss,
            order_type={'trigger': {'triggerPx': stop_loss, 'isMarket': True, 'tpsl': 'sl'}},
            reduce_only=True,
        )
        tp_order = exchange.order(
            coin,
            close_is_buy,
            sz,
            take_profit,
            order_type={'trigger': {'triggerPx': take_profit, 'isMarket': True, 'tpsl': 'tp'}},
            reduce_only=True,
        )

        post_orders = [o for o in (info.open_orders(self.monitor_wallet) or []) if o.get('coin') == coin and o.get('reduceOnly')]
        post_prices = {str(o.get('limitPx')) for o in post_orders}
        ok = expected.issubset(post_prices)
        result = {
            'status': 'ok' if ok else 'partial',
            'cancelled_orders': cancelled,
            'stop_loss_order': sl_order,
            'take_profit_order': tp_order,
            'verified_orders': post_orders,
        }
        if ok:
            state[coin] = desired
            save_protection_state(state)
        append_event({'kind': 'protection_orders_place', 'status': result['status'], 'coin': coin, 'position_size': sz, 'stop_loss': stop_loss, 'take_profit': take_profit})
        return result
