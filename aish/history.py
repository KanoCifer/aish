from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aish.logger import logger

HISTORY_DIR: Path = Path.home() / ".aish"
HISTORY_PATH: Path = HISTORY_DIR / "history.json"
MAX_ENTRIES: int = 1000


def append_history(entry: dict) -> None:
    """
    命令行历史记录管理 — JSON格式
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
        with Path.open(HISTORY_PATH, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    existing.extend(data)
            except json.JSONDecodeError:
                pass

    if len(existing) > MAX_ENTRIES:
        existing = existing[-MAX_ENTRIES:]

    with Path.open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(existing + [history], f, ensure_ascii=False, indent=4)

    logger.debug(f"History appended: {history['command'][:50]}...")


def read_history() -> list[dict]:
    """Return all history entries, newest first."""
    if not HISTORY_PATH.exists():
        return []

    entries: list[dict] = []
    with Path.open(HISTORY_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                entries.extend(data)
        except json.JSONDecodeError:
            pass

    return list(reversed(entries))


def get_history(limit: int) -> list[dict]:
    """返回最近的历史记录"""
    return read_history()[:limit]


def clear_history() -> None:
    """清除历史记录"""
    if HISTORY_PATH.exists():
        HISTORY_PATH.unlink()
    logger.debug("History cleared")
