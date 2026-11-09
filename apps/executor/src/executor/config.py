"""Instellingen (prefix ``EXECUTOR_``); de Custom App heeft geen verplichte variabelen."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EXECUTOR_", extra="ignore")

    data_dir: Path = Path("/appdata")
    host: str = "0.0.0.0"  # noqa: S104 — de container publiceert precies één poort
    port: int = 30410
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    # Alleen voor ontwikkeling/CI: een Hub op 127.0.0.1 toestaan (contract 1.2 §3.2 verbiedt loopback standaard).
    allow_loopback_hub: bool = False
    # Koppelformulier op de statuspagina (contract 1.2 §3.7): per bron-IP en voor de hele executor per 15 min.
    pairing_attempts_per_ip: int = Field(default=5, ge=1, le=5)
    pairing_attempts_total: int = Field(default=20, ge=1, le=20)
    pairing_window_seconds: int = Field(default=15 * 60, ge=60, le=3600)

    @property
    def secrets_dir(self) -> Path:
        return self.data_dir / "secrets"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
