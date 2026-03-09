from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

CONFIG_DIR = Path.home() / ".aish"
CONFIG_PATH = CONFIG_DIR / "config.json"


class ConfigNotFoundError(Exception):
    """Raised when ~/.aish/config does not exist."""

    pass


class ConfigInvalidError(Exception):
    """Raised when config exists but is missing required fields."""

    pass


class AishConfig(BaseModel):
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API Key")
    model: str = Field(..., description="Model")


def read_config() -> AishConfig:
    """读取配置文件"""
    if not CONFIG_PATH.exists():
        raise ConfigNotFoundError("Run 'aish init' first")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    missing = [k for k in ("base_url", "api_key", "model") if k not in data]
    if missing:
        raise ConfigInvalidError(
            f"Config missing required fields: {', '.join(missing)}"
        )
    return AishConfig(
        base_url=data["base_url"],
        api_key=data["api_key"],
        model=data["model"],
    )


def write_config(config: AishConfig) -> None:
    """写入配置文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "base_url": config.base_url,
        "api_key": config.api_key,
        "model": config.model,
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def config_exists() -> bool:
    """Return True if config file exists and has required fields."""
    if not CONFIG_PATH.exists():
        return False
    try:
        read_config()
        return True
    except Exception:
        return False
