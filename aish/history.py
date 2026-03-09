"""Command history management for aish — JSON Lines format."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_DIR = Path.home() / ".aish"
HISTORY_PATH = HISTORY_DIR / "history"
MAX_ENTRIES = 1000


def append_history(entry: dict) -> None:
    """
    Append one history entry to ~/.aish/history (JSON Lines format).
    Auto-trims to MAX_ENTRIES by removing oldest entries.

    Expected entry fields:
        timestamp: str (ISO 8601) — auto-added if missing
        prompt: str
        command: str
        exit_code: int | None
        executed: bool
    """
    if "timestamp" not in entry:
        entry = {**entry, "timestamp": datetime.now(timezone.utc).isoformat()}

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    existing: list[dict] = []
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        existing.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

    existing.append(entry)

    if len(existing) > MAX_ENTRIES:
        existing = existing[-MAX_ENTRIES:]

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        for e in existing:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def read_history() -> list[dict]:
    """Return all history entries, newest first."""
    if not HISTORY_PATH.exists():
        return []

    entries: list[dict] = []
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    return list(reversed(entries))
