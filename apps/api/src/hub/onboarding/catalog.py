"""Besluiten D01–D18 (onboarding-wizard, B01-001) met een getypt waardeschema per besluit.

Regels (contract §1, ADR-0007):
- Er staan **geen voorbeeldwaarden** in de schema's: verplichte velden hebben geen standaardwaarde en plaatshouders
  (``<POOL>``, ``x.x.x.x``, ``TODO`` …) worden geweigerd. Alleen D10 is een vast besluit van de gebruiker.
- ``Getest`` ontstaat alleen door een echte meting (TrueNAS-readback) of een expliciet bewijsrecord, nooit door
  invullen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from hub.truenas.client import validate_host

STATUSES: tuple[str, ...] = ("Open", "Ingevuld", "Getest", "Geblokkeerd", "N.v.t.")

_PLACEHOLDER_RE = re.compile(
    r"(<[^>]*>|\bTODO\b|\bTBD\b|\bxxx+\b|x\.x\.x\.x|\bvoorbeeld\b|\bexample\b|\bplaceholder\b)", re.I
)
_DATASET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*(/[A-Za-z0-9_.: -]+)*$")


def _no_placeholder(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("mag niet leeg zijn")
    if _PLACEHOLDER_RE.search(value):
        raise ValueError("lijkt een plaatshouder/voorbeeldwaarde; vul de echte waarde in")
    return value


Tekst = Annotated[str, Field(min_length=1, max_length=500), AfterValidator(_no_placeholder)]
KorteTekst = Annotated[str, Field(min_length=1, max_length=128), AfterValidator(_no_placeholder)]


def _dataset(value: str) -> str:
    value = _no_placeholder(value).strip("/")
    if value.startswith("mnt/"):
        raise ValueError("geef de datasetnaam (pool/pad), niet het /mnt-pad")
    if not _DATASET_RE.match(value):
        raise ValueError("ongeldige datasetnaam")
    return value


Dataset = Annotated[str, Field(min_length=1, max_length=512), AfterValidator(_dataset)]


def _host(value: str) -> str:
    return validate_host(_no_placeholder(value))


Host = Annotated[str, Field(min_length=1, max_length=253), AfterValidator(_host)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ------------------------------------------------------------------ waardeschema's per besluit
class D01Waarde(Strict):
    versie: KorteTekst = Field(description="Exacte TrueNAS-versie/build zoals de NAS die meldt (System → General).")
    api_versie: KorteTekst | None = Field(default=None, description="API-versie-endpoint, indien bekend.")


class D02Waarde(Strict):
    pools: list[KorteTekst] = Field(min_length=1, max_length=16)
    appdata_datasets: list[Dataset] = Field(min_length=1, max_length=64)
    media_datasets: list[Dataset] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def _datasets_in_pools(self) -> D02Waarde:
        for ds in [*self.appdata_datasets, *self.media_datasets]:
            if ds.split("/", 1)[0] not in self.pools:
                raise ValueError(f"dataset {ds} hoort niet bij een van de opgegeven pools")
        return self


class D03Waarde(Strict):
    nas_adres: Host = Field(description="LAN-IP of hostnaam van TrueNAS (zonder http:// of poort).")
    https_poort: int | None = Field(default=None, ge=1, le=65535, description="Leeg = standaard HTTPS-poort.")
    hostnamen: list[Host] = Field(default_factory=list, max_length=16)
    vpn: KorteTekst | None = None
    tunnel: KorteTekst | None = None
    open_poorten_firewall: list[Annotated[int, Field(ge=1, le=65535)]] = Field(default_factory=list, max_length=64)


class D04Waarde(Strict):
    methode: Literal["truenas_cloud_sync", "rclone", "restic", "onedrive_client", "anders"]
    taken: list[KorteTekst] = Field(min_length=1, max_length=32, description="Namen/omschrijvingen van de taken.")
    versleuteld: bool
    scope: list[Tekst] = Field(min_length=1, max_length=64, description="Datasets/paden die worden meegenomen.")
    retentie: Tekst
    herstel_credentials_locatie: Tekst = Field(
        description="Wáár de herstelgegevens bewaard worden (nooit de sleutel of het wachtwoord zelf)."
    )


class D05Waarde(Strict):
    foto_hersteld: bool
    db_export_hersteld: bool
    omgeving: Tekst = Field(description="Geïsoleerde omgeving waarin is teruggezet.")
    uitgevoerd_op: date
    referentie: Tekst


class PoolGezondheid(Strict):
    naam: KorteTekst
    status: KorteTekst
    gezond: bool
    gebruik_pct: float | None = Field(default=None, ge=0, le=100)
    laatste_scrub: str | None = None
    scrub_fouten: int | None = Field(default=None, ge=0)


class D06Waarde(Strict):
    pools: list[PoolGezondheid] = Field(min_length=1, max_length=16)
    smart_ok: bool | None = None
    snapshot_capaciteit_ok: bool | None = None


class AppVersie(Strict):
    naam: KorteTekst
    image: Tekst | None = None
    versie: KorteTekst | None = None
    staat: KorteTekst | None = None


class D07Waarde(Strict):
    apps: list[AppVersie] = Field(min_length=1, max_length=256)


class GpuNode(Strict):
    rol: Literal["a310", "uhd770", "anders"]
    pci_slot: KorteTekst
    render_node: Annotated[str, Field(pattern=r"^/dev/dri/renderD\d{3}$")]


class D08Waarde(Strict):
    gpus: list[GpuNode] = Field(min_length=1, max_length=8)
    qsv_apps: list[KorteTekst] = Field(default_factory=list, max_length=32)

    @field_validator("gpus")
    @classmethod
    def _unique(cls, v: list[GpuNode]) -> list[GpuNode]:
        if len({g.pci_slot for g in v}) != len(v) or len({g.render_node for g in v}) != len(v):
            raise ValueError("PCI-slot en render-node moeten per GPU uniek zijn")
        return v


class D09Waarde(Strict):
    account_gekoppeld: bool
    inbegrepen_maandbudget: Tekst | None = Field(default=None, description="Zoals de officiële console het toont.")
    harde_stop: Literal[True] = Field(description="Verplicht: harde stop bij 0 resterend tegoed.")
    overage_toegestaan: Literal[False] = Field(description="Verplicht onwaar: nooit betaalde overage.")


class D10Waarde(Strict):
    mini_pc_uitgesloten: Literal[True]
    doel: Tekst


class D11Waarde(Strict):
    routermodel: KorteTekst
    huidige_dns: list[KorteTekst] = Field(min_length=1, max_length=8)
    poort53_eigenaar: KorteTekst
    rollback_toegang: Tekst


class D12Waarde(Strict):
    gree_type: KorteTekst
    firmware: KorteTekst
    lokaal_udp: Literal["ondersteund", "niet_ondersteund", "onbekend"]


class D13Waarde(Strict):
    dongle: KorteTekst
    adapter: KorteTekst
    serial_by_id: Annotated[str, Field(pattern=r"^/dev/serial/by-id/[A-Za-z0-9_.:+-]+$")]
    sensortypes: list[KorteTekst] = Field(min_length=1, max_length=32)


class D14Waarde(Strict):
    p1_meter: bool
    energy_socket_boiler_alleen_meten: Literal[True] = Field(description="Boiler wordt nooit geschakeld (EX27).")
    airco_1fase_meter: bool | None = None


class D15Waarde(Strict):
    tvs: list[KorteTekst] = Field(default_factory=list, max_length=16)
    telefoons: list[KorteTekst] = Field(default_factory=list, max_length=16)
    spelers: list[KorteTekst] = Field(default_factory=list, max_length=16)
    offline_gedrag: Tekst

    @model_validator(mode="after")
    def _minstens_een(self) -> D15Waarde:
        if not (self.tvs or self.telefoons or self.spelers):
            raise ValueError("geef minstens één tv, telefoon of speler op")
        return self


class AppRpoRto(Strict):
    app_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_.-]{0,63}$")]
    rpo_uren: float = Field(gt=0, le=24 * 365)
    rto_uren: float = Field(gt=0, le=24 * 365)


class D16Waarde(Strict):
    per_app: list[AppRpoRto] = Field(min_length=1, max_length=256)

    @field_validator("per_app")
    @classmethod
    def _uniek(cls, v: list[AppRpoRto]) -> list[AppRpoRto]:
        if len({x.app_id for x in v}) != len(v):
            raise ValueError("elke app maar één keer")
        return v


class D17Waarde(Strict):
    domeinnaam: Host
    https: bool
    recovery_account: bool
    rollen: list[KorteTekst] = Field(min_length=1, max_length=16)


class D18Waarde(Strict):
    navidrome_gewenst: bool
    toelichting: Tekst


@dataclass(frozen=True)
class DecisionDef:
    id: str
    titel: str
    wat_vastleggen: str
    gate: str
    schema: type[Strict]
    meetbaar: bool = False  # Getest via TrueNAS-readback mogelijk
    nvt_toegestaan: bool = False
    vast: bool = False


DECISIONS: tuple[DecisionDef, ...] = (
    DecisionDef(
        "D01",
        "TrueNAS versie",
        "Exact build en API schema uit System > General, https lokale API docs",
        "Verplicht vóór connector/bouw",
        D01Waarde,
        meetbaar=True,
    ),
    DecisionDef(
        "D02",
        "Poolnaam en datasetpaden",
        "Alle appdata en mediapaden uit TrueNAS Storage export",
        "Verplicht vóór mount/backup",
        D02Waarde,
        meetbaar=True,
    ),
    DecisionDef(
        "D03",
        "NAS IP en domeinen",
        "LAN IP, hostnames, VPN/tunnel en firewalled ports",
        "Verplicht vóór deployment",
        D03Waarde,
        meetbaar=True,
    ),
    DecisionDef(
        "D04",
        "OneDrive methode",
        "Welke taak/tool, encryptie, scope, retentie en restore credentials",
        "Verplicht vóór backup gate",
        D04Waarde,
    ),
    DecisionDef(
        "D05",
        "OneDrive restore bewijs",
        "Foto plus DB export geïsoleerd getest",
        "Verplicht vóór bestaande app updates",
        D05Waarde,
    ),
    DecisionDef(
        "D06",
        "ZFS pool gezondheid",
        "SMART, scrubs, free space, degraded errors, snapshot capaciteit",
        "Verplicht vóór data-mutaties",
        D06Waarde,
        meetbaar=True,
    ),
    DecisionDef(
        "D07",
        "Huidige appversies",
        "Image tags, current API, config backups, health, actief gebruik",
        "Verplicht vóór upgrade",
        D07Waarde,
        meetbaar=True,
    ),
    DecisionDef(
        "D08",
        "Intel GPU rendernodes",
        "/dev/dri mapping A310/UHD770 en QSV app support",
        "Verplicht vóór fork/transcode",
        D08Waarde,
    ),
    DecisionDef(
        "D09",
        "Claude API-credit claim",
        "Console org link, officieel inbegrepen maandbudget, hard stop en no-pay overage",
        "Verplicht vóór AI agent cloud tool",
        D09Waarde,
        nvt_toegestaan=True,
    ),
    DecisionDef(
        "D10",
        "Bestaande mini-pc doel",
        "Videoapp/andere projecten, geen Home Hub services",
        "Vast besluit",
        D10Waarde,
        vast=True,
    ),
    DecisionDef(
        "D11",
        "Netwerk router DNS fallback",
        "Routermodel, huidige DNS, poort53 eigenaar, rollback access",
        "Verplicht vóór AdGuard DNS cutover",
        D11Waarde,
        nvt_toegestaan=True,
    ),
    DecisionDef(
        "D12",
        "Gree type en firmware",
        "Gree local UDP compatibility via echte bind/readback",
        "Verplicht vóór Gree actuation",
        D12Waarde,
        nvt_toegestaan=True,
    ),
    DecisionDef(
        "D13",
        "Zigbee hardwarestatus",
        "Dongle/adapter/serial-by-id en sensortype",
        "Verplicht vóór Zigbee installatie",
        D13Waarde,
        nvt_toegestaan=True,
    ),
    DecisionDef(
        "D14",
        "HomeWizard meterkoppeling",
        "P1, Energy Socket boiler alleen meten, airco 1fase meter aanwezig?",
        "Verplicht vóór energy dashboard exact",
        D14Waarde,
        nvt_toegestaan=True,
    ),
    DecisionDef(
        "D15",
        "Media clients/platforms",
        "Tv model(s), telefoons, Android TV/Apple TV, gewenste offline gedrag",
        "Verplicht vóór mediaserver cutover",
        D15Waarde,
    ),
    DecisionDef(
        "D16",
        "RPO/RTO",
        "Hoeveel historie/downtime maximaal toegestaan per app",
        "Verplicht vóór restore-policy",
        D16Waarde,
    ),
    DecisionDef(
        "D17",
        "OIDC bereikbaarheid",
        "Domeinnaam, HTTPS, recovery account, roles",
        "Verplicht vóór Authentik",
        D17Waarde,
        nvt_toegestaan=True,
    ),
    DecisionDef(
        "D18",
        "Optional Navidrome",
        "Meerwaarde boven Jellyfin na gebruikerstest",
        "Optioneel",
        D18Waarde,
        nvt_toegestaan=True,
    ),
)

BY_ID: dict[str, DecisionDef] = {d.id: d for d in DECISIONS}

# D10 is een vast besluit van de gebruiker (geen NAS-gegeven en geen voorbeeldwaarde).
D10_VAST: dict[str, Any] = {"mini_pc_uitgesloten": True, "doel": "Videoapp/andere projecten, geen Home Hub services"}


def validate_value(decision_id: str, value: Any) -> dict[str, Any]:
    """Valideer tegen het schema; geeft de genormaliseerde waarde terug of gooit ``ValidationError``."""
    model = BY_ID[decision_id].schema.model_validate(value)
    return model.model_dump(mode="json")


def schema_json(decision_id: str) -> dict[str, Any]:
    return BY_ID[decision_id].schema.model_json_schema()


__all__ = [
    "BY_ID",
    "D10_VAST",
    "DECISIONS",
    "STATUSES",
    "DecisionDef",
    "ValidationError",
    "schema_json",
    "validate_value",
]
