from typing import Any, Dict

from hyperliquid.info import Info

from live_open_executor import LiveOpenExecutor
from trade_events import append_event


class AutoEntryEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.exec_cfg = config.get('execution', {})
        self.analysis_cfg = config.get('analysis', {})
        self.api_cfg = config.get('api', {})
        self.live_executor = LiveOpenExecutor(config)

    def evaluate_and_maybe_execute(self, trade_plan: Dict[str, Any], strategy_plan: Dict[str, Any], signal_scores: list[Dict[str, Any]], risk_allowed: bool, macd_plan: Dict[str, Any] | None = None) -> Dict[str, Any]:
        auto_test = bool(self.exec_cfg.get('enable_auto_test_entries', False))
        auto_live = bool(self.exec_cfg.get('enable_auto_live_entries', False))
        min_score = int(self.analysis_cfg.get('min_signal_score', 70))
        min_rr = float(self.analysis_cfg.get('min_auto_rr', 1.0))
        top = signal_scores[0] if signal_scores else {}
        score = int(top.get('score', 0) or 0)
        setup_quality = top.get('setup_quality', 'no-trade')

        selected_plan = strategy_plan
        selected_trade_plan = trade_plan
        selected_source = 'default'
        if isinstance(macd_plan, dict) and macd_plan.get('executable'):
            selected_plan = {
                **strategy_plan,
                'strategy_type': 'macd_divergence',
                'symbol': macd_plan.get('symbol', '-'),
                'side': macd_plan.get('side', 'none'),
                'entry': macd_plan.get('entry', 0),
                'stop_loss': macd_plan.get('stop_loss', 0),
                'take_profit_1': macd_plan.get('take_profit_1', 0),
                'risk_reward_tp1': macd_plan.get('risk_reward_tp1', 0),
                'plan_complete': macd_plan.get('plan_complete', False),
                'executable': macd_plan.get('executable', False),
                'block_reason': macd_plan.get('block_reason', '-'),
            }
            direction_text = f"{'多' if macd_plan.get('side') == 'buy' else '空'}（{macd_plan.get('symbol', '-') }）"
            selected_trade_plan = {
                **trade_plan,
                'direction': direction_text,
                'stop_loss': macd_plan.get('stop_loss', 0),
                'take_profit': [macd_plan.get('take_profit_1', 0)],
                'strategy_type': 'macd_divergence',
                'should_trade': '是',
            }
            selected_source = 'macd_divergence'

        result = {
            'auto_test_enabled': auto_test,
            'auto_live_enabled': auto_live,
            'armed_mode': 'live' if auto_live else ('test' if auto_test else 'off'),
            'triggered': False,
            'reason': 'auto entry disabled',
            'execution': None,
            'selected_source': selected_source,
            'plan_complete': bool(selected_plan.get('plan_complete', False)),
            'plan_executable': bool(selected_plan.get('executable', False)),
            'plan_rr': selected_plan.get('risk_reward_tp1', 0),
            'plan_qty': selected_plan.get('quantity_estimate', 0),
        }

        if not (auto_test or auto_live):
            return result
        if not risk_allowed:
            result['reason'] = 'risk check blocked'
            return result
        if selected_trade_plan.get('should_trade') not in {'等待', '是'}:
            result['reason'] = 'trade plan not eligible'
            return result
        if selected_source != 'macd_divergence' and setup_quality not in {'candidate'}:
            result['reason'] = f'setup_quality={setup_quality} not ready'
            return result
        if score < min_score:
            result['reason'] = f'score {score} below min {min_score}'
            return result
        if not selected_plan.get('plan_complete', False):
            result['reason'] = 'strategy plan incomplete'
            return result
        if not selected_plan.get('executable', False):
            result['reason'] = f"strategy blocked: {selected_plan.get('block_reason', 'not_executable')}"
            return result
        if float(selected_plan.get('risk_reward_tp1', 0) or 0) < min_rr:
            result['reason'] = f"rr below min_auto_rr {min_rr}"
            return result
        if float(selected_plan.get('quantity_estimate', strategy_plan.get('quantity_estimate', 0)) or 0) <= 0 and selected_source != 'macd_divergence':
            result['reason'] = 'strategy quantity invalid'
            return result

        direction = str(selected_trade_plan.get('direction', ''))
        if '多' in direction:
            is_buy = True
        elif '空' in direction:
            is_buy = False
        else:
            result['reason'] = 'no actionable direction'
            return result

        coin = direction.split('（')[-1].replace('）', '') if '（' in direction else ''
        stop_loss = _to_float(selected_trade_plan.get('stop_loss') or selected_plan.get('stop_loss'))
        monitor_wallet = self.api_cfg.get('monitor_wallet_address', '')
        if coin and monitor_wallet:
            try:
                info = Info(self.api_cfg.get('base_url', 'https://api.hyperliquid.xyz'), skip_ws=True)
                user_state = info.user_state(monitor_wallet)
                active = [((item.get('position', item) if isinstance(item, dict) else {}) .get('coin')) for item in (user_state.get('assetPositions', []) or [])]
                if coin in active:
                    result['reason'] = f'already in position: {coin}'
                    return result
            except Exception:
                pass
        tp_values = selected_trade_plan.get('take_profit') or []
        take_profit = _to_float(tp_values[0] if tp_values else selected_plan.get('take_profit_1', 0))
        leverage = int(selected_plan.get('leverage', self.exec_cfg.get('auto_entry_leverage', 5)))
        order_value = float(self.exec_cfg.get('test_order_max_usdc', 15)) if auto_test and not auto_live else float(self.exec_cfg.get('auto_live_order_usdc', 25))

        exec_result = self.live_executor.market_open(
            coin=coin,
            is_buy=is_buy,
            order_value_usdc=order_value,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_type=selected_trade_plan.get('strategy_type', 'default'),
        )
        result.update({
            'triggered': exec_result.get('status') == 'ok',
            'reason': exec_result.get('reason', 'executed' if exec_result.get('status') == 'ok' else 'execution_failed'),
            'execution': exec_result,
        })
        append_event({'kind': 'auto_entry_decision', 'status': exec_result.get('status', 'blocked'), 'mode': result['armed_mode'], 'coin': coin, 'score': score, 'setup_quality': setup_quality, 'strategy_type': selected_trade_plan.get('strategy_type', 'default'), 'reason': result['reason']})
        return result


def _to_float(value: Any) -> float:
    text = str(value or '0')
    buf = []
    started = False
    for ch in text:
        if ch in '0123456789.-':
            buf.append(ch)
            started = True
        elif started:
            break
    try:
        return float(''.join(buf)) if buf else 0.0
    except Exception:
        return 0.0
