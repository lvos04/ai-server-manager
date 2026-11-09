"""Instellingen (prefix ``EXECUTOR_``); de Custom App heeft geen verplichte variabelen."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EXECUTOR_", extra="ignore")

    data_dir: Path = Path("/appdata")
    host: str = "0.0.0.0"  # noqa: S104 — de container publiceert precies één poort
    port: int = 30410
    log_level: Literal["debug", "info", "warning", "error"] = "info"

    @property
    def secrets_dir(self) -> Path:
        return self.data_dir / "secrets"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
