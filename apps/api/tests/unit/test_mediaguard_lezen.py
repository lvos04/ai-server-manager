"""Toestandstabel voor het MediaGuard-overzicht: alleen een verse, volledige bronmeting wordt een getal."""

from datetime import UTC, datetime, timedelta

import pytest

from hub.adapters.mediaguard_lezen import aanbod, av1_cijfer, grens, pagina, status_cijfer

NU = datetime(2026, 1, 3, 12, tzinfo=UTC)
TIJD = NU.isoformat()
OUD = (NU - timedelta(seconds=901)).isoformat()


def bron(kind: str = "wanted", **wijziging: object) -> dict[str, object]:
    return {
        "type": kind,
        "items": [],
        "status": "ok",
        "reason_code": None,
        "snapshot_id": None,
        "observed_at": TIJD,
        "total": 42,
        "next_cursor": "c",
    } | wijziging


@pytest.mark.parametrize(
    ("wijziging", "status", "waarde", "reden", "heeft_tijd"),
    [
        ({}, "gemeten", 42, None, True),
        ({"total": 0, "next_cursor": None}, "gemeten", 0, None, True),
        ({"total": 1, "next_cursor": None, "items": [{}]}, "gemeten", 1, None, True),
        # Tegenstrijdige pagina (R-VEILIG-3): totaal, items en cursor bevestigen elkaar niet.
        ({"total": 0, "next_cursor": None, "items": [{}]}, "onbekend", None, "tegenstrijdige bronpagina", True),
        ({"total": 0}, "onbekend", None, "tegenstrijdige bronpagina", True),
        ({"total": 1, "items": [{}]}, "onbekend", None, "tegenstrijdige bronpagina", True),
        ({"total": 1, "items": [{}, {}]}, "onbekend", None, "tegenstrijdige bronpagina", True),
        ({"total": 3, "next_cursor": None, "items": [{}]}, "onbekend", None, "tegenstrijdige bronpagina", True),
        ({"observed_at": (NU - timedelta(seconds=900)).isoformat()}, "gemeten", 42, None, True),
        # Negatieve rijen: nooit 0 of een oude waarde als actueel.
        ({"observed_at": OUD}, "onbekend", None, "meting verouderd", True),
        ({"observed_at": (NU + timedelta(minutes=1)).isoformat()}, "onbekend", None, "ongeldige bronmeettijd", False),
        ({"observed_at": "2026-01-03T12:00:00"}, "onbekend", None, "ongeldige bronmeettijd", False),
        ({"observed_at": None}, "onbekend", None, "ongeldige bronmeettijd", False),
        (
            {"status": "unknown", "reason_code": "bron_onbereikbaar", "total": None},
            "onbekend",
            None,
            "bron onbereikbaar",
            True,
        ),
        (
            {"status": "unknown", "reason_code": "meting_verouderd", "total": None, "observed_at": OUD},
            "onbekend",
            None,
            "meting verouderd",
            True,
        ),
        (
            {"status": "unknown", "reason_code": "meting_ontbreekt", "total": None, "observed_at": None},
            "onbekend",
            None,
            "meting ontbreekt bij de bron",
            False,
        ),
        ({"status": "unknown", "reason_code": "vrije brontekst"}, "onbekend", None, "onbekende bronreden", True),
        ({"status": "ok", "reason_code": "meting_verouderd"}, "onbekend", None, "meting verouderd", True),
        ({"total": None}, "onbekend", None, "ongeldig bronantwoord", True),
        ({"type": "status"}, "onbekend", None, "ongeldig bronantwoord", False),
    ],
)
def test_pagina(wijziging, status, waarde, reden, heeft_tijd):
    cijfer, _ = pagina("wanted", bron(**wijziging), NU)
    assert (cijfer.status, cijfer.waarde, cijfer.reden) == (status, waarde, reden)
    assert (cijfer.observed_at is not None) == heeft_tijd


# Toestandstabel ongeldige vormen (R-VEILIG-3): elk veld van ItemPage is verplicht en exact getypeerd;
# ontbrekend is geen null en een booleaan is geen getal of cursor. Uitkomst altijd onbekend, zonder getal of meettijd.
ONGELDIGE_PAGINA = [
    *({"weg": veld} for veld in ("type", "items", "status", "reason_code", "snapshot_id", "observed_at", "total")),
    {"weg": "next_cursor"},
    {"next_cursor": False},
    {"next_cursor": True},
    {"next_cursor": 0},
    {"next_cursor": None, "total": 0, "weg": "next_cursor"},
    {"total": -1},
    {"total": True},
    {"total": False},
    {"total": "42"},
    {"total": 42.0},
    {"items": None},
    {"items": {}},
    {"items": [1]},
    {"items": ["x"]},
    {"type": None},
    {"status": True},
    {"reason_code": 0},
    {"snapshot_id": False},
    {"observed_at": 0},
]


@pytest.mark.parametrize("vorm", ONGELDIGE_PAGINA, ids=str)
def test_pagina_ongeldige_vorm(vorm):
    vorm = dict(vorm)
    body = bron(total=0, next_cursor=None) | {k: v for k, v in vorm.items() if k != "weg"}
    body.pop(vorm.get("weg", ""), None)
    cijfer, items = pagina("wanted", body, NU)
    assert (cijfer.status, cijfer.waarde, cijfer.observed_at, cijfer.reden, items) == (
        "onbekend",
        None,
        None,
        "ongeldig bronantwoord",
        [],
    )
    # Ook geen pagina die geen object is.
    assert pagina("wanted", [body], NU)[0].reden == "ongeldig bronantwoord"


SYSTEEM = {
    "id": "status:installation",
    "observed_at": TIJD,
    "emergency_stop_active": False,
    "emergency_stop_since": None,
    "jobs_queued": 1,
    "jobs_running": 2,
    "jobs_failed": 3,
    "unread_notifications": 4,
}


@pytest.mark.parametrize(
    ("item", "body", "mislukt", "actief", "sinds", "reden"),
    [
        ({}, {}, 3, False, None, None),
        ({"emergency_stop_active": True, "emergency_stop_since": OUD}, {}, 3, True, OUD, None),
        ({"emergency_stop_active": True}, {}, 3, True, None, None),
        # Negatief: twijfel is nooit 'geen noodstop'.
        ({"emergency_stop_active": None}, {}, None, None, None, "ongeldig bronantwoord"),
        ({"emergency_stop_active": "false"}, {}, None, None, None, "ongeldig bronantwoord"),
        (
            {"emergency_stop_active": True, "emergency_stop_since": "gisteren"},
            {},
            None,
            None,
            None,
            "ongeldig bronantwoord",
        ),
        ({"jobs_failed": None}, {}, None, None, None, "ongeldig bronantwoord"),
        ({}, {"next_cursor": "x"}, None, None, None, "tegenstrijdige bronpagina"),
        ({}, {"next_cursor": "x", "total": 2}, None, None, None, "onvolledige bronpagina"),
        ({}, {"total": 2}, None, None, None, "tegenstrijdige bronpagina"),
        # R-VEILIG-4: een oud of ontbrekend statusitem op een verse pagina is nooit 'noodstop uit'.
        ({"observed_at": OUD}, {}, None, None, None, "meting verouderd"),
        ({"observed_at": None}, {}, None, None, None, "ongeldige bronmeettijd"),
        ({}, {"observed_at": OUD}, None, None, None, "meting verouderd"),
        ({}, {"status": "unknown", "reason_code": "bron_onbereikbaar"}, None, None, None, "bron onbereikbaar"),
    ],
)
def test_status_en_noodstop(item, body, mislukt, actief, sinds, reden):
    data = bron("status", total=1, next_cursor=None, items=[SYSTEEM | item]) | body
    cijfer, items = pagina("status", data, NU)
    cijfer, stop = status_cijfer(cijfer, data, items, NU)
    assert (cijfer.waarde, cijfer.reden) == (mislukt, reden)
    assert (stop.actief, stop.reden) == (actief, reden)
    assert stop.sinds == (datetime.fromisoformat(sinds) if sinds else None)
    assert (stop.status == "gemeten") == (reden is None)


@pytest.mark.parametrize(
    "vorm",
    [
        *({"weg": v} for v in ("observed_at", "emergency_stop_active", "emergency_stop_since", "jobs_failed")),
        {"emergency_stop_active": 0},
        {"emergency_stop_active": 1},
        {"jobs_failed": True},
        {"jobs_failed": False},
        {"jobs_failed": -1},
        {"jobs_failed": 3.0},
        {"emergency_stop_since": False},
        {"observed_at": 0},
    ],
    ids=str,
)
def test_statusitem_ongeldige_vorm(vorm):
    # Ontbrekend is geen null en een booleaan geen getal: nooit 'noodstop uit' of 0 mislukte jobs.
    item = SYSTEEM | {k: v for k, v in vorm.items() if k != "weg"}
    item.pop(vorm.get("weg", ""), None)
    data = bron("status", total=1, next_cursor=None, items=[item])
    cijfer, items = pagina("status", data, NU)
    cijfer, stop = status_cijfer(cijfer, data, items, NU)
    assert (cijfer.status, cijfer.waarde, cijfer.reden) == ("onbekend", None, "ongeldig bronantwoord")
    assert (stop.status, stop.actief, stop.sinds) == ("onbekend", None, None)


def test_kortere_brontermijn_geldt_voor_pagina_en_statusitem():
    tijd = (NU - timedelta(seconds=120)).isoformat()
    data = bron("status", total=1, next_cursor=None, items=[SYSTEEM | {"observed_at": TIJD}], observed_at=tijd)
    cijfer, items = pagina("status", data, NU, 60)
    assert (cijfer.status, cijfer.reden) == ("onbekend", "meting verouderd")
    data = bron("status", total=1, next_cursor=None, items=[SYSTEEM | {"observed_at": tijd}])
    cijfer, items = pagina("status", data, NU, 60)
    cijfer, stop = status_cijfer(cijfer, data, items, NU, 60)
    assert (stop.status, stop.actief, stop.reden) == ("onbekend", None, "meting verouderd")
    assert stop.observed_at == datetime.fromisoformat(tijd)


@pytest.mark.parametrize(
    ("pagina_s", "item_s"),
    [(30, 0), (0, 30), (30, 30)],
    ids=["pagina-oudste", "item-oudste", "gelijk"],
)
def test_verse_status_draagt_oudste_bronmeettijd(pagina_s, item_s):
    # R-VEILIG-4: het scherm laat de meting verlopen op de oudste van pagina en statusitem.
    pagina_tijd, item_tijd = NU - timedelta(seconds=pagina_s), NU - timedelta(seconds=item_s)
    data = bron(
        "status",
        total=1,
        next_cursor=None,
        items=[SYSTEEM | {"observed_at": item_tijd.isoformat()}],
        observed_at=pagina_tijd.isoformat(),
    )
    cijfer, items = pagina("status", data, NU, 60)
    cijfer, stop = status_cijfer(cijfer, data, items, NU, 60)
    oudste = min(pagina_tijd, item_tijd)
    assert (cijfer.status, cijfer.observed_at) == ("gemeten", oudste)
    assert (stop.status, stop.observed_at) == ("gemeten", oudste)


AANBOD = {
    "app_id": "media-guard-ultimate",
    "schema_version": "1.0",
    "capabilities": ["read"],
    "item_types": ["wanted", "status"],
    "limits": {"max_age_s": {"status": 60}, "max_page_size": 200},
}


@pytest.mark.parametrize(
    ("limits", "verwacht"),
    [
        (None, 900),
        ({"max_age_s": {"status": 60}}, 60),
        ({"max_age_s": {"status": 3600}}, 900),
        ({"max_age_s": {"wanted": 60}}, 900),
        ({"max_age_s": {"status": 0}}, 0),
    ],
)
def test_grens(limits, verwacht):
    termijnen = aanbod(
        AANBOD | {"limits": limits} if limits is not None else {k: v for k, v in AANBOD.items() if k != "limits"}
    )
    assert termijnen is not None
    assert grens(termijnen[1], "status") == verwacht


# Toestandstabel ongeldig aanbod (R-VEILIG-2, R-VEILIG-4): twijfel aan rechten of termijn = geen leesbare bron.
@pytest.mark.parametrize(
    "wijziging",
    [
        {"capabilities": ["read", False]},
        {"capabilities": ["read", None]},
        {"capabilities": ["read", 1]},
        {"capabilities": [["read"]]},
        {"capabilities": {"read": True}},
        {"capabilities": "read"},
        {"capabilities": True},
        {"capabilities": None},
        {"capabilities": []},
        {"capabilities": ["propose"]},
        {"item_types": None},
        {"item_types": ["wanted", 1]},
        {"item_types": "wanted"},
        {"app_id": "andere-app"},
        {"schema_version": 1.0},
        {"limits": None},
        {"limits": []},
        {"limits": {"max_age_s": 60}},
        {"limits": {"max_age_s": None}},
        {"limits": {"max_age_s": [60]}},
        {"limits": {"max_age_s": {"status": "60"}}},
        {"limits": {"max_age_s": {"status": -1}}},
        {"limits": {"max_age_s": {"status": True}}},
        {"limits": {"max_age_s": {"status": 60.0}}},
        {"limits": {"max_age_s": {"status": None}}},
    ],
    ids=str,
)
def test_aanbod_ongeldige_vorm(wijziging):
    assert aanbod(AANBOD | wijziging) is None


@pytest.mark.parametrize("veld", ["app_id", "schema_version", "capabilities", "item_types"])
def test_aanbod_verplicht_veld(veld):
    assert aanbod({k: v for k, v in AANBOD.items() if k != veld}) is None
    assert aanbod(None) is None and aanbod([AANBOD]) is None


def test_aanbod_geldig():
    assert aanbod(AANBOD | {"capabilities": ["read", "stream"], "extra": {"geheim": "x"}}) == (
        ["wanted", "status"],
        {"status": 60},
    )


def baan(lane: str, running: object) -> dict[str, object]:
    return {"id": lane, "lane": lane, "running": running, "slots": 2, "desired_slots": 2, "paused": False}


@pytest.mark.parametrize(
    ("banen", "waarde", "reden"),
    [
        ([baan("cpu", 1), baan("gpu", 2)], 3, None),
        ([baan("cpu", 0), baan("gpu", 0)], 0, None),
        ([baan("cpu", 1)], None, "tegenstrijdige bronpagina"),
        ([baan("cpu", 1), baan("cpu", 2)], None, "ongeldig bronantwoord"),
        ([baan("cpu", None), baan("gpu", 2)], None, "ongeldig bronantwoord"),
        ([baan("cpu", True), baan("gpu", 2)], None, "ongeldig bronantwoord"),
        ([baan("cpu", 1.0), baan("gpu", 2)], None, "ongeldig bronantwoord"),
        ([baan("cpu", -1), baan("gpu", 2)], None, "ongeldig bronantwoord"),
        ([{"id": "cpu", "running": 1}, baan("gpu", 2)], None, "ongeldig bronantwoord"),
    ],
)
def test_av1_lopende_encodes(banen, waarde, reden):
    body = bron("av1_lanes", total=2, next_cursor=None, items=banen)
    cijfer, items = pagina("av1_lanes", body, NU)
    cijfer = av1_cijfer(cijfer, body, items)
    assert (cijfer.waarde, cijfer.reden) == (waarde, reden)
