from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_alert_history(history_path: Path) -> list[dict[str, Any]]:
    """Load prior alert history from a JSON file."""

    path = Path(history_path)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return payload if isinstance(payload, list) else []


def save_alert_history(history_path: Path, history: list[dict[str, Any]]) -> None:
    """Persist alert history to disk."""

    path = Path(history_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, ensure_ascii=True, indent=2), encoding="utf-8")


def alert_already_sent(history: list[dict[str, Any]], symbol: str, pattern: str, breakout_level: float, session_key: str) -> bool:
    """Check whether the same stock/pattern/breakout was already alerted this session."""

    rounded_level = round(float(breakout_level), 4)
    for item in history:
        if (
            str(item.get("symbol")) == str(symbol)
            and str(item.get("pattern")) == str(pattern)
            and round(float(item.get("breakout_level", 0.0)), 4) == rounded_level
            and str(item.get("session_key")) == str(session_key)
        ):
            return True
    return False
