import os
import time
from typing import Any, Dict, List

from eth_account import Account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

from trade_events import append_event
from trade_record_store import finalize_trade_record


class LiveKillSwitch:
    """真实 Kill Switch：仅在 enable_live_execution=true 时允许执行。"""

    def _fetch_close_fill_stats(self, info: Info, coin: str, start_ms: int) -> Dict[str, float | str]:
        try:
            fills = info.user_fills_by_time(self.monitor_wallet, start_ms, int(time.time() * 1000), aggregate_by_time=True)
        except Exception as exc:
            return {'pnl': 0.0, 'fee': 0.0, 'error': str(exc)}
        matched = [f for f in (fills or []) if f.get('coin') == coin]
        pnl = sum(float(f.get('closedPnl', 0) or 0) for f in matched)
        fee = sum(abs(float(f.get('fee', 0) or 0)) for f in matched)
        close_price = float(matched[-1].get('px', 0) or 0) if matched else 0.0
        return {'pnl': pnl, 'fee': fee, 'close_price': close_price, 'error': ''}

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_cfg = config.get('api', {})
        self.exec_cfg = config.get('execution', {})
        self.base_url = self.api_cfg.get('base_url', 'https://api.hyperliquid.xyz')
        self.monitor_wallet = self.api_cfg.get('monitor_wallet_address', '')
        self.execution_wallet = self.api_cfg.get('execution_wallet_address', '')
        self.secret_key_env = self.api_cfg.get('secret_key_env', 'HYPERLIQUID_SECRET_KEY')
        self.enabled = bool(self.exec_cfg.get('enable_live_execution', False))

    def close_coin(self, coin: str) -> Dict[str, Any]:
        if not self.enabled:
            return {'status': 'blocked', 'reason': 'enable_live_execution is false'}
        secret = os.environ.get(self.secret_key_env, '')
        if not secret:
            return {'status': 'blocked', 'reason': f'missing env {self.secret_key_env}'}
        acct = Account.from_key(secret)
        if self.execution_wallet and acct.address.lower() != self.execution_wallet.lower():
            return {'status': 'blocked', 'reason': 'execution wallet does not match private key', 'derived_address': acct.address}
        exchange = Exchange(wallet=acct, base_url=self.base_url, account_address=self.monitor_wallet)
        info = Info(self.base_url, skip_ws=True)
        before = info.user_state(self.monitor_wallet)
        started_ms = int(time.time() * 1000) - 5000
        resp = exchange.market_close(coin)
        pos = next((item.get('position', item) for item in before.get('assetPositions', []) if (item.get('position', item) or {}).get('coin') == coin), {})
        fill_stats = self._fetch_close_fill_stats(info, coin, started_ms)
        finalize_trade_record(
            coin=coin,
            pnl=float(fill_stats.get('pnl') or pos.get('unrealizedPnl', 0) or 0),
            fee=float(fill_stats.get('fee') or 0),
            close_price=float(fill_stats.get('close_price') or 0),
            close_reason='timeout_auto_close',
        )
        append_event({'kind': 'timeout_auto_close', 'status': 'ok', 'coin': coin})
        return {'status': 'ok', 'coin': coin, 'response': resp}

    def execute(self) -> Dict[str, Any]:
        if not self.enabled:
            result = {
                'status': 'blocked',
                'reason': 'enable_live_execution is false',
            }
            append_event({'kind': 'kill_switch_blocked', **result})
            return result

        secret = os.environ.get(self.secret_key_env, '')
        if not secret:
            result = {'status': 'blocked', 'reason': f'missing env {self.secret_key_env}'}
            append_event({'kind': 'kill_switch_blocked', **result})
            return result

        acct = Account.from_key(secret)
        if self.execution_wallet and acct.address.lower() != self.execution_wallet.lower():
            result = {
                'status': 'blocked',
                'reason': 'execution wallet does not match private key',
                'derived_address': acct.address,
            }
            append_event({'kind': 'kill_switch_blocked', **result})
            return result

        exchange = Exchange(wallet=acct, base_url=self.base_url, account_address=self.monitor_wallet)
        info = Info(self.base_url, skip_ws=True)
        before = info.user_state(self.monitor_wallet)
        positions: List[Dict[str, Any]] = before.get('assetPositions', [])
        if not positions:
            result = {'status': 'noop', 'reason': 'no open positions'}
            append_event({'kind': 'kill_switch_noop', **result})
            return result

        executions = []
        for item in positions:
            pos = item['position']
            coin = pos['coin']
            started_ms = int(time.time() * 1000) - 5000
            resp = exchange.market_close(coin)
            fill_stats = self._fetch_close_fill_stats(info, coin, started_ms)
            finalize_trade_record(
                coin=coin,
                pnl=float(fill_stats.get('pnl') or pos.get('unrealizedPnl', 0) or 0),
                fee=float(fill_stats.get('fee') or 0),
                close_price=float(fill_stats.get('close_price') or 0),
                close_reason='kill_switch_execute',
            )
            executions.append({'coin': coin, 'response': resp, 'fill_stats': fill_stats})

        after = info.user_state(self.monitor_wallet)
        cleared = len(after.get('assetPositions', [])) == 0
        result = {
            'status': 'ok' if cleared else 'partial',
            'before': before,
            'executions': executions,
            'after': after,
            'cleared': cleared,
        }
        append_event({'kind': 'kill_switch_execute', 'status': result['status'], 'cleared': cleared, 'coins': [e['coin'] for e in executions]})
        return result
