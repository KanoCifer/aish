from __future__ import annotations

import tomllib
from pathlib import Path
from dataclasses import dataclass

import tomli_w

CONFIG_DIR = Path.home() / ".aish"
CONFIG_PATH = CONFIG_DIR / "config"


class ConfigNotFoundError(Exception):
    """Raised when ~/.aish/config does not exist."""

    pass


class ConfigInvalidError(Exception):
    """Raised when config exists but is missing required fields."""

    pass


@dataclass
class AishConfig:
    base_url: str
    api_key: str
    model: str


def read_config() -> AishConfig:
    """Read config from ~/.aish/config. Raises ConfigNotFoundError if not found."""
    if not CONFIG_PATH.exists():
        raise ConfigNotFoundError("Run 'aish init' first")
    with open(CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)
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
    """Write config to ~/.aish/config as TOML."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "base_url": config.base_url,
        "api_key": config.api_key,
        "model": config.model,
    }
    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(data, f)


def config_exists() -> bool:
    """Return True if config file exists and has required fields."""
    if not CONFIG_PATH.exists():
        return False
    try:
        read_config()
        return True
    except Exception:
        return False
