from typing import Any, Dict, Tuple


class RiskEngine:
    """负责交易前强制风控审查。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.risk_cfg = config.get("risk", {})

    def validate_trade(self, trade_plan: Dict[str, Any], account_state: Dict[str, Any]) -> Tuple[bool, str]:
        if self.risk_cfg.get("require_stop_loss", True) and not trade_plan.get("stop_loss"):
            return False, "禁止交易：未设置止损"

        consecutive_losses = account_state.get("consecutive_losses", 0)
        max_losses = self.risk_cfg.get("max_consecutive_losses", 3)
        if consecutive_losses >= max_losses:
            return False, "禁止交易：连续亏损达到上限，强制停止"

        perps = account_state.get('perps', {}) if isinstance(account_state, dict) else {}
        asset_positions = perps.get('assetPositions', []) if isinstance(perps, dict) else []
        direction = str(trade_plan.get('direction', ''))
        symbol = direction.split('（')[-1].replace('）', '') if '（' in direction else ''
        for item in asset_positions:
            position = item.get('position', {}) if isinstance(item, dict) else {}
            if position.get('coin') == symbol:
                return False, f"禁止交易：{symbol} 已有持仓，禁止重复开仓"

        open_positions = len(asset_positions)
        max_open_positions = self.risk_cfg.get("max_open_positions", 4)
        macd_reserved_slots = self.risk_cfg.get("macd_reserved_slots", 1)
        normal_strategy_limit = max(0, max_open_positions - macd_reserved_slots)
        strategy_type = str(trade_plan.get('strategy_type', 'default'))
        effective_limit = max_open_positions if strategy_type == 'macd_divergence' else normal_strategy_limit
        if open_positions >= effective_limit:
            if strategy_type == 'macd_divergence':
                return False, f"禁止交易：当前持仓数已达到总上限 {max_open_positions}"
            return False, f"禁止交易：普通策略最多只能占用 {normal_strategy_limit} 个仓位，已为 MACD 预留 {macd_reserved_slots} 个"

        return True, f"允许进入下一步审查（总上限 {max_open_positions}，普通策略上限 {normal_strategy_limit}，MACD 预留 {macd_reserved_slots} 个）"
