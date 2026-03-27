import json
import logging
import time
from datetime import datetime
from pathlib import Path

from env_loader import load_local_env
from main import load_config, run_once


def _dashboard_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "dashboard" / "latest.json"


def _has_valid_account_block(dashboard: dict) -> bool:
    if not isinstance(dashboard, dict):
        return False
    account = dashboard.get('account_state') or {}
    open_orders = dashboard.get('open_orders')
    if not isinstance(account, dict):
        return False
    return bool(account.get('perps') or account.get('spot')) and isinstance(open_orders, list)


def _load_previous_dashboard() -> dict:
    path = _dashboard_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _write_dashboard(dashboard: dict) -> None:
    path = _dashboard_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding='utf-8')


def main() -> None:
    load_local_env()
    log_path = Path(__file__).resolve().parent.parent / "logs" / "runner.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=str(log_path), level=logging.INFO, format='%(message)s')

    while True:
        previous_dashboard = _load_previous_dashboard()
        try:
            config = load_config()
            interval = int(config.get("refresh_seconds", 15))
            dashboard = run_once(config)
            if _has_valid_account_block(dashboard) or not _has_valid_account_block(previous_dashboard):
                _write_dashboard(dashboard)
                persisted = 'fresh'
            else:
                dashboard = previous_dashboard
                persisted = 'kept_previous'
            summary = dashboard.get("execution_summary", {}) or {}
            message = (
                f"[{datetime.now().isoformat()}] updated dashboard"
                f" | persisted={persisted}"
                f" | market_state={dashboard['trade_plan']['market_state']}"
                f" | direction={dashboard['trade_plan']['direction']}"
                f" | risk={dashboard['trade_plan']['risk_level']}"
                f" | live={dashboard.get('live_execution_probe', {}).get('live_enabled')}"
                f" | flat={summary.get('is_flat', '?')}"
                f" | pos={summary.get('current_position_count', '?')}"
            )
        except Exception as exc:
            interval = 15
            message = f"[{datetime.now().isoformat()}] runner error: {exc} | persisted=previous"

        print(message, flush=True)
        logging.info(message)
        time.sleep(interval)


if __name__ == "__main__":
    main()
