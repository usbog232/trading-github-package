from datetime import datetime
from typing import Any, Dict, List, Tuple

from trade_events import latest_events


class TestOrderGuard:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.exec_cfg = config.get('execution', {})
        self.account_cfg = config.get('account', {})

    def validate(self, *, order_value_usdc: float, stop_loss_pct: float) -> Tuple[bool, List[str]]:
        reasons: List[str] = []
        if not self.exec_cfg.get('test_order_mode', False):
            reasons.append('test_order_mode 未开启')
            return False, reasons

        max_usdc = float(self.exec_cfg.get('test_order_max_usdc', 15))
        if order_value_usdc > max_usdc:
            reasons.append(f'测试单名义仓位超过 {max_usdc} USDC')

        equity = float(self.account_cfg.get('base_equity', 0))
        max_loss_pct = float(self.exec_cfg.get('test_order_max_loss_pct', 1.0)) / 100.0
        max_loss_amount = equity * max_loss_pct
        estimated_loss = order_value_usdc * (stop_loss_pct / 100.0)
        if estimated_loss > max_loss_amount:
            reasons.append(f'测试单预计亏损 {estimated_loss:.4f} 超过允许上限 {max_loss_amount:.4f}')

        today = datetime.now().date().isoformat()
        daily_loss_cap = float(self.exec_cfg.get('test_order_daily_max_loss_usdc', 5.0))
        events = latest_events(100)
        today_test_losses = 0.0
        for event in events:
            if event.get('kind') == 'test_order_loss' and str(event.get('ts', '')).startswith(today):
                today_test_losses += float(event.get('loss_usdc', 0.0))
        if today_test_losses >= daily_loss_cap:
            reasons.append(f'今日测试累计亏损已达到上限 {daily_loss_cap} USDC')

        return len(reasons) == 0, reasons
