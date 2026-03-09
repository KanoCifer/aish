"""Command history management for aish — JSON Lines format."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_DIR: Path = Path.home() / ".aish"
HISTORY_PATH: Path = HISTORY_DIR / "history.json"
MAX_ENTRIES: int = 1000


def append_history(entry: dict) -> None:
    """
    命令行历史记录管理 — JSON Lines 格式
    """
    if "timestamp" not in entry:
        entry = {**entry, "timestamp": datetime.now(timezone.utc).isoformat()}

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    history = {
        "timestamp": entry["timestamp"],
        "command": entry.get("command", ""),
        "args": entry.get("args", []),
    }
    existing = []
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    existing.extend(data)
            except json.JSONDecodeError:
                pass

    if len(existing) > MAX_ENTRIES:
        existing = existing[-MAX_ENTRIES:]

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(existing + [history], f, ensure_ascii=False, indent=4)


def read_history() -> list[dict]:
    """Return all history entries, newest first."""
    if not HISTORY_PATH.exists():
        return []

    entries: list[dict] = []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                entries.extend(data)
        except json.JSONDecodeError:
            pass

    return list(reversed(entries))
