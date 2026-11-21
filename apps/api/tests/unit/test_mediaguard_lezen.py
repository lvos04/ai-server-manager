"""Toestandstabel voor het MediaGuard-overzicht: alleen een verse, volledige bronmeting wordt een getal."""

from datetime import UTC, datetime, timedelta

import pytest

from hub.adapters.mediaguard_lezen import av1_cijfer, pagina, status_cijfer

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
        ({"total": 0}, "gemeten", 0, None, True),
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
        ({"total": -1}, "onbekend", None, "ongeldig bronantwoord", True),
        ({"total": True}, "onbekend", None, "ongeldig bronantwoord", True),
        ({"total": "42"}, "onbekend", None, "ongeldig bronantwoord", True),
        ({"items": None}, "onbekend", None, "ongeldig bronantwoord", True),
        ({"type": "status"}, "onbekend", None, "ongeldig bronantwoord", False),
    ],
)
def test_pagina(wijziging, status, waarde, reden, heeft_tijd):
    cijfer, _ = pagina("wanted", bron(**wijziging), NU)
    assert (cijfer.status, cijfer.waarde, cijfer.reden) == (status, waarde, reden)
    assert (cijfer.observed_at is not None) == heeft_tijd


SYSTEEM = {
    "id": "status:installation",
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
        ({}, {"next_cursor": "x"}, None, None, None, "onvolledige bronpagina"),
        ({}, {"total": 2}, None, None, None, "onvolledige bronpagina"),
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


def baan(lane: str, running: object) -> dict[str, object]:
    return {"id": lane, "lane": lane, "running": running, "slots": 2, "desired_slots": 2, "paused": False}


@pytest.mark.parametrize(
    ("banen", "waarde", "reden"),
    [
        ([baan("cpu", 1), baan("gpu", 2)], 3, None),
        ([baan("cpu", 0), baan("gpu", 0)], 0, None),
        ([baan("cpu", 1)], None, "onvolledige bronpagina"),
        ([baan("cpu", 1), baan("cpu", 2)], None, "ongeldig bronantwoord"),
        ([baan("cpu", None), baan("gpu", 2)], None, "ongeldig bronantwoord"),
    ],
)
def test_av1_lopende_encodes(banen, waarde, reden):
    body = bron("av1_lanes", total=2, next_cursor=None, items=banen)
    cijfer, items = pagina("av1_lanes", body, NU)
    cijfer = av1_cijfer(cijfer, body, items)
    assert (cijfer.waarde, cijfer.reden) == (waarde, reden)
