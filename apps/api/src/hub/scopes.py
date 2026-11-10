"""Vaste leesscopes per dienst (contract 1.3 §4.4, C1.3-ASM-07; ADR-0029).

De scopes staan **in de Hub vast** (deze tabel), per ``app_id`` uit §2: een dienst kan ze niet kiezen of uitbreiden en
een beheerder ziet ze in de Hub-UI (Instellingen → Diensten). Zonder scope → 403 ``scope_ontbreekt``; dat is nooit een
intrekking (§3.8). Nooit geheimen via deze routes.

- ``inventaris.lezen``: ``GET /api/v1/apps`` en ``GET /api/v1/apps/{id}`` (gepagineerd over een momentopname, §5).
- ``catalogus.lezen``: route voor catalogusbeschikbaarheid — **nog niet gebouwd (P2)**; de scope staat al vast.
- ``besluiten.lezen``: ``GET /connector/v1/items?type=decision`` — standaard aan **geen** dienst (K6: gemeten leest geen
  dienst besluiten van de Hub). Toekennen vraagt een ADR met de lijst per besluittype.

Andere connector-itemtypes en de overige leesroutes van de Hub-connector (``backup.self``, ``events``, ``evidence``)
zijn alleen voor gebruikers (``viewer``+), tot een scope is vastgelegd.
"""

from __future__ import annotations

INVENTARIS_LEZEN = "inventaris.lezen"
CATALOGUS_LEZEN = "catalogus.lezen"
BESLUITEN_LEZEN = "besluiten.lezen"

ALLE_SCOPES: dict[str, str] = {
    INVENTARIS_LEZEN: "Inventaris lezen: GET /api/v1/apps en /api/v1/apps/{id}",
    CATALOGUS_LEZEN: "Catalogusbeschikbaarheid lezen (route volgt in fase P2)",
    BESLUITEN_LEZEN: "Besluiten lezen: GET /connector/v1/items?type=decision (standaard aan geen enkele dienst)",
}

# Contract 1.3 §4.4, tabel "Diensten (v1)". Vast in de Hub; niet door de dienst te kiezen.
SERVICE_SCOPES: dict[str, frozenset[str]] = {
    "appstore-en-fork": frozenset({INVENTARIS_LEZEN}),
    "jelly-leon-platform": frozenset({INVENTARIS_LEZEN, CATALOGUS_LEZEN}),
    "home-control-hub": frozenset({CATALOGUS_LEZEN}),
}


def scopes_for(app_id: str) -> list[str]:
    return sorted(SERVICE_SCOPES.get(app_id, frozenset()))


def has_scope(app_id: str | None, scope: str) -> bool:
    return app_id is not None and scope in SERVICE_SCOPES.get(app_id, frozenset())
