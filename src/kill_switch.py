from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class KillSwitchPreview:
    enabled: bool
    execution_wallet_address: str
    positions_found: int
    actions: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    mode: str = "preview_only"


class KillSwitch:
    """紧急停机安全骨架：默认只预演，不做真实平仓。"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.exec_cfg = config.get("execution", {})
        self.api_cfg = config.get("api", {})
        self.enabled = bool(self.exec_cfg.get("enable_live_execution", False))

    @staticmethod
    def _direction_from_size(size: float) -> str:
        if size > 0:
            return "多"
        if size < 0:
            return "空"
        return "无"

    @staticmethod
    def _close_action_from_size(size: float) -> str:
        if size > 0:
            return "市价卖出平多"
        if size < 0:
            return "市价买入平空"
        return "无需动作"

    def preview(self, account_state: Dict[str, Any]) -> KillSwitchPreview:
        perps = account_state.get("perps", {}) if isinstance(account_state, dict) else {}
        positions = perps.get("assetPositions", []) if isinstance(perps, dict) else []
        actions = []
        warnings = []

        for item in positions:
            pos = item.get("position", item)
            coin = pos.get("coin")
            raw_size = pos.get("szi", "0")
            try:
                size = float(raw_size)
            except Exception:
                size = 0.0
            if not coin or size == 0:
                continue

            actions.append({
                "coin": coin,
                "direction": self._direction_from_size(size),
                "current_size": raw_size,
                "absolute_size": abs(size),
                "entry_price": pos.get("entryPx"),
                "position_value": pos.get("positionValue"),
                "unrealized_pnl": pos.get("unrealizedPnl"),
                "roe": pos.get("returnOnEquity"),
                "planned_action": self._close_action_from_size(size),
                "execution_wallet_address": self.api_cfg.get("execution_wallet_address", ""),
                "status": "preview_only",
            })

        if not actions:
            warnings.append("当前无合约持仓，无需平仓")
        if not self.api_cfg.get("execution_wallet_address"):
            warnings.append("未配置 execution_wallet_address")
        if not self.enabled:
            warnings.append("真实执行关闭，Kill Switch 仅预演")

        return KillSwitchPreview(
            enabled=self.enabled,
            execution_wallet_address=self.api_cfg.get("execution_wallet_address", ""),
            positions_found=len(actions),
            actions=actions,
            warnings=warnings,
            mode="live" if self.enabled else "preview_only",
        )

    def execute(self, account_state: Dict[str, Any]) -> Dict[str, Any]:
        preview = self.preview(account_state)
        if not self.enabled:
            return {
                "status": "blocked",
                "reason": "Kill Switch 真实执行默认禁用",
                "preview": preview.__dict__,
            }
        raise NotImplementedError("真实 Kill Switch 尚未启用；后续需接入真实签名、市价平仓和回执校验")
