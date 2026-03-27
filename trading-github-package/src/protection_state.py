import json
from pathlib import Path
from typing import Any, Dict


def _path() -> Path:
    p = Path(__file__).resolve().parent.parent / 'data' / 'journal' / 'protection_state.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text('{}', encoding='utf-8')
    return p


def load_protection_state() -> Dict[str, Any]:
    try:
        return json.loads(_path().read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_protection_state(data: Dict[str, Any]) -> Path:
    p = _path()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return p
