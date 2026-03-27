import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _events_path() -> Path:
    p = Path(__file__).resolve().parent.parent / 'data' / 'journal' / 'events.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text('[]', encoding='utf-8')
    return p


def append_event(event: Dict[str, Any]) -> Path:
    path = _events_path()
    data: List[Dict[str, Any]] = json.loads(path.read_text(encoding='utf-8'))
    payload = {
        'ts': datetime.now().isoformat(),
        **event,
    }
    data.append(payload)
    path.write_text(json.dumps(data[-100:], ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def latest_events(limit: int = 10) -> List[Dict[str, Any]]:
    path = _events_path()
    data = json.loads(path.read_text(encoding='utf-8'))
    return data[-limit:]
