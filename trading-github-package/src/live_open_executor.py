import os
import time
from typing import Any, Dict

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

from position_tracker import record_open
from protection_executor import ProtectionExecutor
from size_utils import quantize_down
from test_order_guard import TestOrderGuard
from trade_events import append_event


def _sum_fill_fee(info: Info, address: str, coin: str, start_ms: int) -> float:
    try:
        fills = info.user_fills_by_time(address, start_ms, aggregate_by_time=True)
    except Exception:
        return 0.0
    matched = [f for f in (fills or []) if f.get('coin') == coin]
    return sum(abs(float(f.get('fee', 0) or 0)) for f in matched)


class LiveOpenExecutor:
    """最小真实开仓执行器：当前先支持市价开仓。"""

    MIN_ORDER_VALUE_USDC = 10.0

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_cfg = config.get('api', {})
        self.exec_cfg = config.get('execution', {})
        self.base_url = self.api_cfg.get('base_url', 'https://api.hyperliquid.xyz')
        self.monitor_wallet = self.api_cfg.get('monitor_wallet_address', '')
        self.execution_wallet = self.api_cfg.get('execution_wallet_address', '')
        self.secret_key_env = self.api_cfg.get('secret_key_env', 'HYPERLIQUID_SECRET_KEY')
        self.live_enabled = bool(self.exec_cfg.get('enable_live_execution', False))
        self.guard = TestOrderGuard(config)
        self.protection = ProtectionExecutor(config)

    def _resolve_order_size(self, *, coin: str, target_usdc: float, mid: float, sz_decimals: int) -> tuple[float, float, str | None]:
        sz = quantize_down(target_usdc / mid, sz_decimals)
        actual_value = sz * mid
        max_usdc = float(self.exec_cfg.get('test_order_max_usdc', 15)) if self.exec_cfg.get('test_order_mode', False) else target_usdc

        adjusted = False
        if actual_value < self.MIN_ORDER_VALUE_USDC:
            probe = target_usdc
            while probe <= max_usdc:
                test_sz = quantize_down(probe / mid, sz_decimals)
                test_value = test_sz * mid
                if test_value >= self.MIN_ORDER_VALUE_USDC:
                    sz = test_sz
                    actual_value = test_value
                    target_usdc = probe
                    adjusted = True
                    break
                probe += 0.1

        if actual_value < self.MIN_ORDER_VALUE_USDC:
            return sz, actual_value, '无法在当前测试单上限内达到交易所最小下单金额'

        note = None
        if adjusted:
            note = f'已自动上调目标金额到 {target_usdc:.2f} USDC 以满足最小成交额'
        return sz, actual_value, note

    def market_open(self, *, coin: str, is_buy: bool, order_value_usdc: float, leverage: int, stop_loss: float, take_profit: float, strategy_type: str = 'default') -> Dict[str, Any]:
        if not self.live_enabled:
            return {'status': 'blocked', 'reason': 'enable_live_execution is false'}

        secret = os.environ.get(self.secret_key_env, '')
        if not secret:
            return {'status': 'blocked', 'reason': f'missing env {self.secret_key_env}'}

        acct = Account.from_key(secret)
        if self.execution_wallet and acct.address.lower() != self.execution_wallet.lower():
            return {'status': 'blocked', 'reason': 'execution wallet does not match private key', 'derived_address': acct.address}

        info = Info(self.base_url, skip_ws=True)
        mids = info.all_mids()
        meta = info.meta()
        mid = float(mids[coin])
        stop_loss_pct = abs(mid - stop_loss) / mid * 100
        if self.exec_cfg.get('test_order_mode', False):
            ok, reasons = self.guard.validate(order_value_usdc=order_value_usdc, stop_loss_pct=stop_loss_pct)
            if not ok:
                return {'status': 'blocked', 'reason': ' ; '.join(reasons)}

        sz_decimals = next((int(item['szDecimals']) for item in meta.get('universe', []) if item.get('name') == coin), 4)
        sz, actual_value, min_value_note = self._resolve_order_size(coin=coin, target_usdc=order_value_usdc, mid=mid, sz_decimals=sz_decimals)
        if min_value_note == '无法在当前测试单上限内达到交易所最小下单金额':
            return {'status': 'blocked', 'reason': min_value_note}

        exchange = Exchange(wallet=acct, base_url=self.base_url, account_address=self.monitor_wallet)
        started_ms = int(time.time() * 1000) - 5000
        lev_resp = exchange.update_leverage(leverage, coin, is_cross=True)
        open_resp = exchange.market_open(coin, is_buy, sz)
        open_fee = _sum_fill_fee(info, self.monitor_wallet, coin, started_ms)
        user_state = info.user_state(self.monitor_wallet)

        protection_resp = self.protection.place_protection_orders(
            coin=coin,
            position_size=sz,
            is_long=is_buy,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        record_open(
            coin=coin,
            strategy_type=strategy_type,
            side='buy' if is_buy else 'sell',
            entry_price=mid,
            position_size=sz,
            open_fee=open_fee,
        )

        result = {
            'status': 'ok',
            'coin': coin,
            'open_fee': open_fee,
            'is_buy': is_buy,
            'strategy_type': strategy_type,
            'requested_order_value_usdc': order_value_usdc,
            'actual_order_value_usdc': actual_value,
            'leverage': leverage,
            'estimated_size': sz,
            'mid_price': mid,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'update_leverage_response': lev_resp,
            'open_response': open_resp,
            'protection_response': protection_resp,
            'after_state': user_state,
            'mode': 'test_order' if self.exec_cfg.get('test_order_mode', False) else 'live_order',
            'note': min_value_note,
        }
        append_event({'kind': 'market_open_execute', 'status': 'ok', 'coin': coin, 'is_buy': is_buy, 'order_value_usdc': actual_value, 'leverage': leverage})
        return result
