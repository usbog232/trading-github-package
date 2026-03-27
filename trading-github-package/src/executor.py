from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ExecutionPreview:
    enabled: bool
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit_1: Optional[float]
    take_profit_2: Optional[float]
    risk_amount: float
    position_value: float
    quantity_estimate: float
    mode: str
    warnings: list[str]


class TradeExecutor:
    """安全执行骨架：默认只做预演，禁用真实发单。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.account_cfg = config.get("account", {})
        self.risk_cfg = config.get("risk", {})
        self.exec_cfg = config.get("execution", {})
        self.enabled = bool(self.exec_cfg.get("enable_live_execution", False))

    @staticmethod
    def _parse_direction(direction: str) -> tuple[str, str]:
        if "多" in direction:
            return direction.split("（")[-1].replace("）", ""), "buy"
        if "空" in direction:
            return direction.split("（")[-1].replace("）", ""), "sell"
        return "", "none"

    def preview_order(self, trade_plan: Dict[str, Any]) -> ExecutionPreview:
        symbol, side = self._parse_direction(trade_plan.get("direction", ""))
        warnings = []

        if side == "none":
            warnings.append("当前无有效交易方向")
        if not trade_plan.get("stop_loss") or trade_plan.get("stop_loss") == "无":
            warnings.append("缺少止损，禁止进入执行")
        if trade_plan.get("should_trade") not in {"等待", "是"}:
            warnings.append("当前计划不允许执行")

        entry_price = self._extract_number(trade_plan.get("entry", "0"))
        stop_loss = self._extract_number(trade_plan.get("stop_loss", "0"))
        take_profit = trade_plan.get("take_profit", []) or []
        tp1 = self._extract_number(str(take_profit[0])) if len(take_profit) >= 1 else None
        tp2 = self._extract_number(str(take_profit[1])) if len(take_profit) >= 2 else None

        equity = float(self.account_cfg.get("base_equity", 0))
        risk_pct = float(self.risk_cfg.get("risk_per_trade_pct", 3.0)) / 100.0
        risk_amount = equity * risk_pct
        max_risk_pct = float(self.risk_cfg.get("max_risk_per_trade_pct", 8.0)) / 100.0
        max_risk_amount = equity * max_risk_pct
        leverage = int(self.exec_cfg.get("auto_test_leverage", 5))
        max_margin_usage_pct = float(self.exec_cfg.get("max_margin_usage_pct", 100.0)) / 100.0
        max_notional = equity * leverage if equity > 0 and leverage > 0 else 0.0
        max_margin = equity * max_margin_usage_pct if equity > 0 else 0.0

        price_risk = abs(entry_price - stop_loss)
        quantity = 0.0
        position_value = 0.0
        if entry_price > 0 and price_risk > 0:
            risk_quantity = risk_amount / price_risk
            margin_cap_quantity = (max_notional / entry_price) if max_notional > 0 else 0.0
            quantity = min(risk_quantity, margin_cap_quantity) if margin_cap_quantity > 0 else risk_quantity
            position_value = quantity * entry_price
        else:
            warnings.append("无法根据入场和止损计算仓位")

        if risk_amount > max_risk_amount:
            warnings.append("计划风险超过单笔最大风险阈值")
        estimated_margin = (position_value / leverage) if leverage > 0 else 0.0
        if estimated_margin > max_margin:
            warnings.append("预估保证金占用超过允许上限")

        return ExecutionPreview(
            enabled=self.enabled,
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            risk_amount=risk_amount,
            position_value=position_value,
            quantity_estimate=quantity,
            mode="live" if self.enabled else "preview_only",
            warnings=warnings,
        )

    def place_order(self, trade_plan: Dict[str, Any]) -> Dict[str, Any]:
        preview = self.preview_order(trade_plan)
        if not self.enabled:
            return {
                "status": "blocked",
                "reason": "真实发单默认禁用",
                "preview": preview.__dict__,
            }
        raise NotImplementedError("真实发单尚未启用；后续需接 Hyperliquid 签名和 exchange endpoint")

    @staticmethod
    def _extract_number(text: str) -> float:
        if not text:
            return 0.0
        allowed = "0123456789.-"
        buf = []
        started = False
        for ch in text:
            if ch in allowed:
                buf.append(ch)
                started = True
            elif started:
                break
        try:
            return float("".join(buf)) if buf else 0.0
        except ValueError:
            return 0.0
