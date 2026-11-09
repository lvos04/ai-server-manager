"""Adapterprofielen van bekende apps (B01-002): adaptertype, eigenaar, documentatie, UI-poort en gezondheidseisen.

Een profiel zegt **hoe** de Hub een app benadert, nooit iets over de NAS van de gebruiker. Herkenning gebeurt op
TrueNAS-appnaam en image (``hub.truenas.normalize.recognize_app``); een onbekende app krijgt het profiel ``onbekend``
en wordt nooit gegokt.

``binnenkant_vereist``: de app voert zelf taken uit (worker/jobs). Zo'n app is pas ``healthy`` als er naast een
bereikbaarheidscontrole ook een verse binnenkant-controle is (heartbeat, connector-health of de eigen worker van de
Hub). Ontbreekt die, dan blijft de app ``unknown`` — een app die 200 teruggeeft maar geen jobs uitvoert, mag nooit als
gezond verschijnen (B09-002, ADR-0016).
"""

from __future__ import annotations

from dataclasses import dataclass

# Vaste lijst van adaptertypen (API-waarden).
ADAPTER_TYPES: tuple[str, ...] = (
    "hub_zelf",  # de Hub zelf (eigen worker-hartslag)
    "eigen_dienst",  # eigen nieuwe dienst met connectorcontract §6 (enrollment)
    "bestaand_mediaguard",  # bestaande app: Hub-adapter via bestaande routes met gescopete sleutel (§2.3)
    "bestaand_mso",
    "bestaand_my_house",
    "jellyfin",  # Jellyfin/Jelly Leon: alleen openbare routes (§2.3)
    "uptime_kuma",  # monitoringbron
    "beszel",  # monitoringbron
    "gotify",  # meldingskanaal
    "alleen_truenas",  # app van derden: alleen TrueNAS-staat en externe controles (Uptime Kuma)
    "onbekend",
)

SOORTEN: tuple[str, ...] = ("eigen", "bestaand", "derde", "onbekend")

# Waar de binnenkant-controle vandaan komt.
BINNENKANT_HUB = "hub_worker"
BINNENKANT_DIENST = "heartbeat_of_connector"
BINNENKANT_P3 = "adapter_p3"  # bestaande app: read-model met gescopete sleutel volgt in P3 (nog niet gebouwd)


@dataclass(frozen=True)
class AppProfile:
    key: str
    titel: str
    adapter: str
    soort: str
    eigenaar_repo: str | None
    documentatie: str | None
    ui_poort: int | None  # containerpoort van de eigen UI (voor de deep-link); None = eerste TCP-poort
    binnenkant: str | None  # bron van de binnenkant-controle; None = alleen externe controles mogelijk
    binnenkant_vereist: bool


_DOCS = "docs/platform-v2"

_PROFILES: tuple[AppProfile, ...] = (
    AppProfile(
        "ai-server-manager",
        "Hub (AI Server Manager)",
        "hub_zelf",
        "eigen",
        "lvos04/ai-server-manager",
        f"{_DOCS}/02_BOUWPLANNEN/B01_HOME_CONTROL_HUB.md",
        30400,
        BINNENKANT_HUB,
        True,
    ),
    AppProfile(
        "ai-server-manager-executor",
        "Executor",
        "eigen_dienst",
        "eigen",
        "lvos04/ai-server-manager",
        f"{_DOCS}/02_BOUWPLANNEN/B02_AI_SERVER_MANAGER.md",
        30410,
        None,  # nog geen connector-health of heartbeat (P2); alleen bereikbaarheid
        False,
    ),
    AppProfile(
        "home-control-hub",
        "Home Control Hub (integraties)",
        "eigen_dienst",
        "eigen",
        "lvos04/home-control-hub",
        f"{_DOCS}/03_INSTALLATIE/I23_HOME_CONTROL_HUB.md",
        30420,
        BINNENKANT_DIENST,
        True,
    ),
    AppProfile(
        "appstore-en-fork",
        "Appstore",
        "eigen_dienst",
        "eigen",
        "lvos04/appstore-en-fork",
        f"{_DOCS}/02_BOUWPLANNEN/B08_APPSTORE_LIFECYCLE.md",
        30430,
        BINNENKANT_DIENST,
        True,
    ),
    AppProfile(
        "jelly-leon-platform",
        "Jelly Leon-platform (lifecycle)",
        "eigen_dienst",
        "eigen",
        "lvos04/jelly-leon-platform",
        f"{_DOCS}/02_BOUWPLANNEN/B08_APPSTORE_LIFECYCLE.md",
        30440,
        BINNENKANT_DIENST,
        True,
    ),
    AppProfile(
        "zoeken-en-persoonlijke-ai",
        "Zoeken en persoonlijke AI",
        "eigen_dienst",
        "eigen",
        "lvos04/zoeken-en-persoonlijke-ai",
        f"{_DOCS}/03_INSTALLATIE/I25_SEARCH.md",
        30450,
        BINNENKANT_DIENST,
        True,
    ),
    AppProfile(
        "jelly-leon",
        "Jelly Leon",
        "jellyfin",
        "eigen",
        "lvos04/jelly-leon",
        f"{_DOCS}/03_INSTALLATIE/I24_UNIVERSELE_MEDIASERVER.md",
        8096,
        None,
        False,
    ),
    AppProfile(
        "mediaguard",
        "MediaGuard",
        "bestaand_mediaguard",
        "bestaand",
        "lvos04/media-guard-ultimate",
        f"{_DOCS}/04_BESTAANDE_APPS/A18_MEDIAGUARD.md",
        30080,
        BINNENKANT_P3,
        True,
    ),
    AppProfile(
        "media-source-optimizer",
        "Media Source Optimizer",
        "bestaand_mso",
        "bestaand",
        "lvos04/media-source-optimizer",
        f"{_DOCS}/04_BESTAANDE_APPS/A19_MEDIA_SOURCE_OPTIMIZER.md",
        38081,
        BINNENKANT_P3,
        True,
    ),
    AppProfile(
        "my_house",
        "my_house (smart home)",
        "bestaand_my_house",
        "bestaand",
        "lvos04/my_house",
        f"{_DOCS}/04_BESTAANDE_APPS/A20_MY_HOUSE.md",
        8080,
        BINNENKANT_P3,
        True,
    ),
    AppProfile(
        "jellyfin",
        "Jellyfin",
        "jellyfin",
        "derde",
        None,
        f"{_DOCS}/04_BESTAANDE_APPS/A17_JELLYFIN.md",
        8096,
        None,
        False,
    ),
    AppProfile(
        "uptime-kuma",
        "Uptime Kuma",
        "uptime_kuma",
        "derde",
        None,
        f"{_DOCS}/03_INSTALLATIE/I08_UPTIME_KUMA.md",
        3001,
        None,
        False,
    ),
    AppProfile("beszel", "Beszel", "beszel", "derde", None, f"{_DOCS}/03_INSTALLATIE/I07_BESZEL.md", 8090, None, False),
    AppProfile("gotify", "Gotify", "gotify", "derde", None, f"{_DOCS}/03_INSTALLATIE/I13_GOTIFY.md", 80, None, False),
)

# Apps van derden die de Hub alleen via TrueNAS en externe controles kent (documentatie uit het pakket).
_DERDEN: dict[str, tuple[str, str | None]] = {
    "plex": ("Plex", "04_BESTAANDE_APPS/A01_PLEX.md"),
    "emby": ("Emby", "04_BESTAANDE_APPS/A02_EMBY.md"),
    "immich": ("Immich", "04_BESTAANDE_APPS/A10_IMMICH.md"),
    "prowlarr": ("Prowlarr", "04_BESTAANDE_APPS/A11_PROWLARR.md"),
    "sabnzbd": ("SABnzbd", "04_BESTAANDE_APPS/A13_SABNZBD.md"),
    "qbittorrent": ("qBittorrent", "04_BESTAANDE_APPS/A14_QBITTORRENT.md"),
    "bazarr": ("Bazarr", "04_BESTAANDE_APPS/A09_BAZARR.md"),
    "seerr": ("Seerr", "04_BESTAANDE_APPS/A12_SEERR.md"),
    "readarr": ("Readarr", "04_BESTAANDE_APPS/A04_READARR.md"),
    "flaresolverr": ("FlareSolverr", "04_BESTAANDE_APPS/A05_FLARESOLVERR.md"),
    "tailscale": ("Tailscale", "04_BESTAANDE_APPS/A15_TAILSCALE.md"),
    "cloudflared": ("Cloudflared", "04_BESTAANDE_APPS/A16_CLOUDFLARED.md"),
    "authentik": ("Authentik", "03_INSTALLATIE/I09_AUTHENTIK.md"),
    "node-red": ("Node-RED", "03_INSTALLATIE/I10_NODE_RED.md"),
    "adguard-home": ("AdGuard Home", "03_INSTALLATIE/I12_ADGUARD_HOME.md"),
    "netalertx": ("NetAlertX", "03_INSTALLATIE/I11_NETALERTX.md"),
}

ONBEKEND = AppProfile("onbekend", "Onbekende app", "onbekend", "onbekend", None, None, None, None, False)

PROFILES: dict[str, AppProfile] = {p.key: p for p in _PROFILES}
for _key, (_titel, _doc) in _DERDEN.items():
    PROFILES[_key] = AppProfile(
        _key, _titel, "alleen_truenas", "derde", None, f"{_DOCS}/{_doc}" if _doc else None, None, None, False
    )


def profile_for(key: str | None) -> AppProfile:
    return PROFILES.get(key or "", ONBEKEND)
