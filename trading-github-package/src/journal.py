import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class TradeJournal:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def log(self, record: Dict[str, Any]) -> Path:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.base_dir / f"trade-{ts}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
