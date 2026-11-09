"""Instellingen (pydantic-settings, prefix ``HUB_``).

De standaard TrueNAS Custom App heeft géén verplichte variabelen: alle standaardwaarden hieronder werken in de
alles-in-één image. Variabelen zijn er voor ontwikkeling/CI (zie ``.env.example``). Er staan nooit NAS-gegevens
(IP, poolnaam, versie) in de instellingen: die komen uit de onboarding-wizard (D01–D18) of uit gemeten readback.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from hub.outbound import OutboundPolicy

DEFAULT_SOCKET_DIR = "/tmp/asm-pg"  # noqa: S108 — map 0700 van uid 568, alleen unix-socket, geen netwerkpoort


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HUB_", extra="ignore")

    data_dir: Path = Path("/appdata")
    database_url: str = f"postgresql+psycopg://hub@/hub?host={DEFAULT_SOCKET_DIR}"

    host: str = "0.0.0.0"  # noqa: S104 — de container publiceert precies één poort
    port: int = 30400
    # Achter de (latere) ingebouwde web-UI luistert de API alleen op 127.0.0.1:<internal_api_port>.
    internal_api_port: int = 8400
    forwarded_allow_ips: str = "127.0.0.1"

    log_level: Literal["debug", "info", "warning", "error"] = "info"

    # Sessies en login
    cookie_secure: Literal["auto", "true", "false"] = "auto"
    session_ttl_seconds: int = Field(default=12 * 3600, ge=300, le=7 * 24 * 3600)
    session_idle_seconds: int = Field(default=2 * 3600, ge=300, le=24 * 3600)
    login_max_failures: int = Field(default=5, ge=1, le=100)
    login_window_seconds: int = Field(default=15 * 60, ge=60, le=24 * 3600)
    password_min_length: int = Field(default=12, ge=8, le=128)
    setup_code_ttl_seconds: int = Field(default=24 * 3600, ge=600, le=7 * 24 * 3600)

    # JWT voor gebruikerscontext naar diensten (contract §4: exp ≤ 120 s)
    jwt_ttl_seconds: int = Field(default=120, ge=10, le=120)

    # Enrollment (contract 1.2 §3.3–§3.8)
    enrollment_token_ttl_seconds: int = Field(default=60 * 60, ge=60, le=60 * 60)
    pairing_code_ttl_seconds: int = Field(default=60 * 60, ge=60, le=60 * 60)
    executor_pairing_code_ttl_seconds: int = Field(default=30 * 60, ge=60, le=30 * 60)
    enroll_max_failures: int = Field(default=10, ge=1, le=100)  # mislukte pogingen (401) per bron-IP …
    enroll_window_seconds: int = Field(default=15 * 60, ge=60, le=24 * 3600)  # … binnen dit venster → 429
    # Oud service-token blijft na een rotatie geldig tot zoveel seconden na het eerste gebruik van het nieuwe …
    service_token_rotation_grace_seconds: int = Field(default=10 * 60, ge=0, le=24 * 3600)
    # … maar hooguit zoveel seconden na de rotatie.
    service_token_rotation_max_seconds: int = Field(default=24 * 3600, ge=60, le=24 * 3600)
    service_token_rotation_advice_days: int = Field(default=180, ge=1, le=3650)  # alleen een melding, nooit automatisch

    # Uitgaande aanroepen van de Hub naar eigen diensten (contract §5: 5 s connect / 15 s read, nooit redirects)
    service_call_connect_timeout: float = Field(default=5.0, gt=0, le=60)
    service_call_read_timeout: float = Field(default=15.0, gt=0, le=120)

    # Noodlogin (contract 1.2 §4.1)
    break_glass_password_min_length: int = Field(default=20, ge=20, le=256)
    break_glass_session_minutes_default: int = Field(default=60, ge=5, le=240)
    break_glass_reconfirm_days: int = Field(default=90, ge=1, le=365)

    # TrueNAS JSON-RPC (contract §5: 5 s connect / 15 s read)
    truenas_connect_timeout: float = Field(default=5.0, gt=0, le=60)
    truenas_read_timeout: float = Field(default=15.0, gt=0, le=120)
    truenas_extra_ca_file: Path | None = None  # optioneel eigen CA; anders systeem-CA of vingerafdruk

    # Inventaris
    inventory_ttl_seconds: int = Field(default=15 * 60, ge=30, le=24 * 3600)
    inventory_interval_seconds: int = Field(default=5 * 60, ge=30, le=24 * 3600)

    # Eigen back-up (pg_dump) van de ingebouwde database
    self_backup_interval_seconds: int = Field(default=24 * 3600, ge=300, le=7 * 24 * 3600)
    self_backup_keep: int = Field(default=7, ge=1, le=365)
    pg_dump_bin: str = "pg_dump"
    pg_restore_bin: str = "pg_restore"

    worker_poll_seconds: float = Field(default=5.0, gt=0, le=300)

    # Uitgaande aanroepen naar monitoringbronnen en meldingskanalen (contract §5; nooit redirects of proxy).
    # Loopback/link-local alleen met deze ontwikkelvlag (tests); nooit in de image.
    outbound_allow_loopback: bool = False
    outbound_extra_ca_file: Path | None = None  # optioneel eigen CA voor https-bronnen

    # Monitoring (B09): pollinterval van de bronnen, veroudering en tijdreeksen.
    monitoring_interval_seconds: int = Field(default=60, ge=10, le=3600)
    nas_metrics_interval_seconds: int = Field(default=30, ge=10, le=3600)  # reporting.realtime
    nas_metrics_ttl_seconds: int = Field(default=180, ge=30, le=3600)  # ouder → unknown in de observability
    health_record_interval_seconds: int = Field(default=60, ge=10, le=3600)
    monitor_ttl_seconds: int = Field(default=300, ge=30, le=24 * 3600)  # Uptime Kuma/Beszel-waarneming
    connector_fail_threshold: int = Field(default=2, ge=1, le=10)  # opeenvolgende fouten vóór 'down'
    metrics_max_series: int = Field(default=2000, ge=10, le=100_000)
    metrics_raw_retention_seconds: int = Field(default=48 * 3600, ge=3600, le=30 * 24 * 3600)
    metrics_5m_retention_seconds: int = Field(default=30 * 24 * 3600, ge=24 * 3600, le=400 * 24 * 3600)
    metrics_1h_retention_seconds: int = Field(default=400 * 24 * 3600, ge=7 * 24 * 3600, le=5 * 365 * 24 * 3600)
    metrics_maintenance_interval_seconds: int = Field(default=300, ge=30, le=3600)
    alert_interval_seconds: int = Field(default=30, ge=5, le=3600)
    alert_stale_seconds: int = Field(default=600, ge=60, le=24 * 3600)  # zonder verse meting geen overgang

    # Meldingen (Gotify): pogingen, veroudering van de wachtrij.
    notify_max_attempts: int = Field(default=8, ge=1, le=50)
    notify_expire_seconds: int = Field(default=24 * 3600, ge=600, le=7 * 24 * 3600)

    # AI is standaard uit (lokale modellen optioneel en standaard uit; geen betaalde overage)
    ai_enabled: bool = False

    def outbound_policy(self) -> OutboundPolicy:
        return OutboundPolicy(
            connect_timeout=self.service_call_connect_timeout,
            read_timeout=self.service_call_read_timeout,
            allow_loopback=self.outbound_allow_loopback,
            extra_ca_file=self.outbound_extra_ca_file,
        )

    @property
    def secrets_dir(self) -> Path:
        return self.data_dir / "secrets"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def libpq_url(self) -> str:
        """URL voor pg_dump/pg_restore (zonder SQLAlchemy-driverdeel)."""
        url = self.database_url
        for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
            if url.startswith(prefix):
                return "postgresql://" + url[len(prefix) :]
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
