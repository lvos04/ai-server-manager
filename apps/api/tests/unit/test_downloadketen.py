"""De opgeslagen MediaGuard-diagnose hoort bij één aflevering en één bronmeting."""

from datetime import UTC, datetime, timedelta

import pytest

from hub.incidents.downloadketen import diagnose

NU = datetime(2026, 1, 3, 12, tzinfo=UTC)
ID = 17
TIJD = NU.isoformat()
BRON = {"wanted_id": ID, "primary_code": "import-failed", "ts": TIJD}


@pytest.mark.parametrize(
    ("wijziging", "code", "reden", "heeft_tijd"),
    [
        ({}, "import-failed", None, True),
        ({"wanted_id": ID + 1}, None, "antwoord voor een andere aflevering", False),
        ({"wanted_id": True}, None, "antwoord voor een andere aflevering", False),
        ({"primary_code": "unknown"}, "unknown", "oorzaak onbekend bij de bron", True),
        ({"primary_code": "vrije-brontekst"}, None, "onbekende oorzaakcode", True),
        ({"primary_code": []}, None, "onbekende oorzaakcode", True),
        ({"ts": (NU - timedelta(seconds=900)).isoformat()}, "import-failed", None, True),
        ({"ts": (NU - timedelta(seconds=901)).isoformat()}, None, "meting verouderd", True),
        ({"ts": (NU + timedelta(minutes=1)).isoformat()}, None, "ongeldige bronmeettijd", False),
        ({"ts": ""}, None, "ongeldige bronmeettijd", False),
        ({"ts": None}, None, "ongeldige bronmeettijd", False),
        ({"ts": "2026-01-03T12:00:00"}, None, "ongeldige bronmeettijd", False),
    ],
)
def test_gecachete_diagnose(wijziging, code, reden, heeft_tijd):
    resultaat = diagnose(ID, {**BRON, **wijziging}, NU)
    assert resultaat.oorzaakcode == code
    assert resultaat.reden == reden
    assert (resultaat.observed_at is not None) == heeft_tijd
    if heeft_tijd:
        assert resultaat.observed_at == datetime.fromisoformat(wijziging.get("ts", TIJD))


@pytest.mark.parametrize(
    ("bron", "tijd", "rijen", "stand", "reden"),
    [
        ("probe", TIJD, ["aanwezig"], "aanwezig", None),
        ("probe", TIJD, ["ontbreekt"], "ontbreekt", None),
        ("probe", TIJD, ["onbekend"], None, "routestatus onbekend"),
        ("openapi", TIJD, ["aanwezig"], None, "livecontrole ontbreekt"),
        ("probe", TIJD, ["aanwezig", "ontbreekt"], None, "routestatus onbekend"),
        ("probe", TIJD, [], None, "routestatus onbekend"),
        ("probe", (NU - timedelta(hours=1)).isoformat(), ["aanwezig"], None, "meting verouderd"),
    ],
)
def test_mso_compatibiliteit_betreft_de_route(bron, tijd, rijen, stand, reden):
    from hub.incidents.downloadketen import compatibiliteit

    data = {
        "live_source": bron,
        "checked_at": tijd,
        "routes": [{"id": "wanted_diagnosis", "live": live} for live in rijen]
        + [{"id": "auth_me", "live": "aanwezig"}],
    }
    resultaat = compatibiliteit(data, NU)
    assert resultaat.bronstatus == stand and resultaat.reden == reden
    assert resultaat.oorzaakcode is None
    assert resultaat.observed_at == (None if bron != "probe" else datetime.fromisoformat(tijd))
