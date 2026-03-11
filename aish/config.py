from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, SecretStr

from aish.logger import logger

CONFIG_DIR = Path.home() / ".aish"
CONFIG_PATH = CONFIG_DIR / "config.json"


class ConfigNotFoundError(Exception):
    """Raised when ~/.aish/config does not exist."""

    pass


class ConfigInvalidError(Exception):
    """Raised when config exists but is missing required fields."""

    pass


class AishConfigs(BaseModel):
    configs: list[AishConfig] = Field(..., description="Aish configuration")


class AishConfig(BaseModel):
    base_url: str = Field(..., description="API base URL")
    api_key: SecretStr = Field(..., description="API Key")
    model: str = Field(..., description="Model")
    alias: str | None = Field(None, description="Optional command alias")
    using: bool = Field(False, description="Whether this config is currently active")


def read_config() -> AishConfigs:
    """读取配置文件"""
    if not CONFIG_PATH.exists():
        logger.debug("Config file not found")
        raise ConfigNotFoundError("Run 'aish init' first")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        configs = json.load(f)
        if not isinstance(configs, list):
            raise ConfigInvalidError(
                "Invalid config format: root must be an array of config objects"
            )
        for config in configs:
            if not isinstance(config, dict):
                raise ConfigInvalidError(
                    "Invalid config format: each config must be an object"
                )
            missing: list[str] = [
                k for k in ("base_url", "api_key", "model") if k not in config
            ]
            if missing:
                raise ConfigInvalidError(
                    f"Config missing required fields: {', '.join(missing)}"
                )
    logger.debug(f"Config loaded: {len(configs)} entries")
    return AishConfigs(
        configs=[
            AishConfig(
                base_url=config["base_url"],
                api_key=config["api_key"],
                model=config["model"],
                alias=config.get("alias"),
                using=config.get("using", False),
            )
            for config in configs
        ]
    )


def write_config(config: AishConfig) -> None:
    """写入配置文件"""
    logger.debug(f"Writing config: model={config.model}, alias={config.alias}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config = AishConfig(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        alias=config.alias,
        using=config.using,
    )

    try:
        existing_configs = read_config()
        if config.using:
            for c in existing_configs.configs:
                c.using = False

        existing_configs.configs.append(config)
    except ConfigNotFoundError:
        existing_configs = AishConfigs(configs=[config])

    save_configs(existing_configs)

    try:
        existing_configs = read_config()
        if config.using:
            # 如果新配置设置为使用中，则将其他配置的using设为False
            for c in existing_configs.configs:
                c.using = False

        existing_configs.configs.append(config)
    except ConfigNotFoundError:
        existing_configs = AishConfigs(configs=[config])

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(
            [
                {**config.model_dump(), "api_key": config.api_key.get_secret_value()}
                for config in existing_configs.configs
            ],
            f,
            ensure_ascii=False,
            indent=4,
        )


def save_configs(configs: AishConfigs) -> None:
    """保存所有配置到文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(
            [
                {**config.model_dump(), "api_key": config.api_key.get_secret_value()}
                for config in configs.configs
            ],
            f,
            ensure_ascii=False,
            indent=4,
        )


def update_config(config: AishConfig) -> None:
    """更新配置文件"""
    logger.debug(f"Updating config: model={config.model}, using={config.using}")
    existing_configs: AishConfigs = read_config()
    updated = False

    if config.using:
        for existing in existing_configs.configs:
            existing.using = False

    for i, existing in enumerate(existing_configs.configs):
        if existing.model == config.model:
            existing_configs.configs[i] = config
            updated = True
            break
    if not updated:
        existing_configs.configs.append(config)

    save_configs(existing_configs)


def config_exists() -> bool:
    if not CONFIG_PATH.exists():
        return False
    try:
        read_config()
        return True
    except Exception:
        return False
