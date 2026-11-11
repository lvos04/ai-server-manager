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
    # TrueNAS (contract 1.3 §3.9). Leeg = het adres waarop de beheerder de executorpagina opent: de executor draait op
    # de NAS zelf. Alleen invullen als de TrueNAS-API op een ander adres luistert dan de executorpagina.
    truenas_host: str = Field(default="", max_length=253)
    truenas_port: int = Field(default=443, ge=1, le=65535)
    truenas_timeout_seconds: float = Field(default=15.0, ge=1, le=120)
    # Readback na een actie: zo lang wachten tot de verwachte eindtoestand er is; daarna is het een afwijking.
    readback_wait_seconds: float = Field(default=120.0, ge=0, le=1800)
    readback_poll_seconds: float = Field(default=2.0, ge=0.05, le=30)
    # Alleen ontwikkeling/CI: beleid uit een beschrijfbare map accepteren. In het image is het beleid read-only
    # (contract 1.3 §8); staat dit uit en is het beleid beschrijfbaar, dan voert de executor niets uit.
    allow_writable_policy: bool = False

    @property
    def secrets_dir(self) -> Path:
        return self.data_dir / "secrets"

    @property
    def replay_db(self) -> Path:
        """Persistente jti-replaycache (contract 1.2 §4.6); SQLite in de eigen datamap, nooit in ``secrets``."""
        return self.data_dir / "executor.sqlite3"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
