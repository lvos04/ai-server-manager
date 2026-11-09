"""Incidentregels (B01-005) en het strenge schoningsbeleid voor de log-index (B09-004): zuivere functies."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

import pytest

from hub import APP_ID
from hub.incidents.rules import EventIn, classify
from hub.redact import SecretMatcher, redact_log_text, redact_log_value

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)


def ev(
    source: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    entity: tuple[str, str] = ("app", "x"),
    stroom: str = "inbox",
) -> EventIn:
    return EventIn(stroom, f"{stroom}:1", source, event_type, entity[0], entity[1], payload or {}, "internal", NOW)


@pytest.mark.parametrize(
    ("text", "absent", "present"),
    [
        ("van 192.168.1.20 en 8.8.8.8", ["192.168.1.20", "8.8.8.8"], ["[ip-privé]", "[ip-publiek]"]),
        ("lokaal 127.0.0.1 en fe80::1", ["127.0.0.1", "fe80::1"], ["[ip-lokaal]"]),
        ("tijd 12:30:45 blijft", [], ["12:30:45"]),
        ("Authorization: Bearer abcdefghijklmnop", ["abcdefghijklmnop"], []),
        ('{"password": "Geheim-123", "x": 1}', ["Geheim-123"], []),
        ("wachtwoord=Hunter2-Hunter2 sleutel: abcd-efgh-1234", ["Hunter2-Hunter2", "abcd-efgh-1234"], []),
        ("?code=AbC&state=xy&nonce=n1", ["AbC", "=xy", "n1"], []),
        ("svc_" + "a" * 43 + " en enr_" + "b" * 43, ["a" * 43, "b" * 43], ["[token]"]),
        ("eyJhbGciOi.eyJzdWIiOiIx.c2ln", ["eyJzdWIiOiIx"], ["[jwt]"]),
        ("mail leon@example.org", ["leon@example.org"], ["[e-mail]"]),
        ("image x@sha256:" + "a" * 64, [], ["sha256:" + "a" * 64]),
        ("hex " + "0123456789abcdef" * 3, ["0123456789abcdef" * 3], ["[hex]"]),
        ("status code: 500 reason_code=auth_failed", [], ["code: 500", "reason_code=auth_failed"]),
        ("bestand TrueNAS_V2_Uitvoering_en_Afvinken_2026.xlsx", [], ["TrueNAS_V2_Uitvoering_en_Afvinken_2026.xlsx"]),
    ],
)
def test_strenge_schoning(text: str, absent: list[str], present: list[str]) -> None:
    out = redact_log_text(text)
    for a in absent:
        assert a not in out, out
    for p in present:
        assert p in out, out


def test_willekeurig_token_en_bekend_geheim() -> None:
    tok = "Zz9" + secrets.token_urlsafe(32)
    assert tok not in redact_log_text(f"token {tok} einde")
    m = SecretMatcher([SecretMatcher.fingerprint("kort-maar-bekend!")])
    assert redact_log_text("gotify key kort-maar-bekend! lekt", m) == "gotify key *** lekt"
    assert "kort" not in str(m.fingerprints)  # alleen vingerafdrukken in het geheugen


def test_velden_en_grenzen() -> None:
    out = redact_log_value({"token": "x" * 10, "wachtwoord": "geheim", "nested": {"ip": "10.0.0.1"}, "ok": True})
    assert out == {"token": "***", "wachtwoord": "***", "nested": {"ip": "[ip-privé]"}, "ok": True}
    assert len(redact_log_text("z " * 2500)) == 2000
    assert len(redact_log_value(list(range(100)))) == 50


def test_hub_events_zelfde_vingerafdruk_voor_probleem_en_herstel() -> None:
    f = classify(
        ev(
            APP_ID,
            "monitoring.source.failed",
            {"naam": "Kuma", "reden": "api_key_geweigerd"},
            ("monitor_source", "s1"),
            "outbox",
        )
    )
    r = classify(ev(APP_ID, "monitoring.source.recovered", {"naam": "Kuma"}, ("monitor_source", "s1"), "outbox"))
    assert f and r and f.rol == "probleem" and r.rol == "herstel" and f.vingerafdruk == r.vingerafdruk
    other = classify(ev(APP_ID, "monitoring.source.recovered", {}, ("monitor_source", "s2"), "outbox"))
    assert other and other.vingerafdruk != f.vingerafdruk
    a = classify(
        ev(
            APP_ID,
            "alert.instance.fired",
            {
                "regel_id": "r",
                "onderwerp_type": "app",
                "onderwerp_id": "1",
                "ernst": "kritiek",
                "regel_sleutel": "app-down",
            },
            stroom="outbox",
        )
    )
    b = classify(
        ev(
            APP_ID,
            "alert.instance.resolved",
            {"regel_id": "r", "onderwerp_type": "app", "onderwerp_id": "1"},
            stroom="outbox",
        )
    )
    assert a and b and a.vingerafdruk == b.vingerafdruk and a.meldt is False and a.ernst == "kritiek"
    assert a.soort == "alert.app-down"
    bg = classify(ev(APP_ID, "auth.break_glass.used", {}, ("user", "u1"), "outbox"))
    assert bg and bg.ernst == "kritiek" and bg.meldt_elke_keer
    # Een dienst kan zich niet als de Hub voordoen: zelfde event-type via de inbox valt onder de algemene regel.
    spoof = classify(ev("home-control-hub", "auth.break_glass.used", {}, ("user", "u1")))
    assert spoof is None


def test_algemene_regels_en_onbekend() -> None:
    crash = classify(ev("mediaguard", "app.process.crashed"))
    rec = classify(ev("mediaguard", "app.process.recovered"))
    assert crash and rec and crash.ernst == "kritiek" and crash.vingerafdruk == rec.vingerafdruk
    assert classify(ev("mediaguard", "media.download.failed")).ernst == "waarschuwing"  # type: ignore[union-attr]
    assert classify(ev("mediaguard", "media.download.failed", {"severity": "critical"})).ernst == "kritiek"  # type: ignore[union-attr]
    assert classify(ev("mediaguard", "media.item.added")) is None
    unknown = classify(ev("x", "app.health.changed", {"status": "unknown"}))
    assert unknown and unknown.rol == "info"
    down = classify(ev("x", "app.health.changed", {"status": "down"}))
    assert down and down.rol == "probleem" and down.ernst == "kritiek"
    long = classify(ev("x", "app.job.failed", {"naam": "A" * 500 + " token=geheim1234"}))
    assert long and len(long.titel) < 260 and "geheim1234" not in long.titel


def test_sso_events_van_home_control_hub() -> None:
    hch = "home-control-hub"
    sync = classify(ev(hch, "sso.authentik_sync.failed", {"reason": "token_geweigerd"}))
    assert sync and sync.rol == "probleem" and sync.soort == "sso.authentik_sync"
    rood = classify(ev(hch, "sso.authentik_upgrade_gate.evaluated", {"outcome": "rood"}))
    ok = classify(ev(hch, "sso.authentik_upgrade_gate.evaluated", {"outcome": "ok_lokaal"}))
    onb = classify(ev(hch, "sso.authentik_upgrade_gate.evaluated", {"outcome": "onbekend"}))
    assert rood and ok and onb and (rood.rol, ok.rol, onb.rol) == ("probleem", "herstel", "info")
    afw = classify(ev(hch, "sso.authentik_restore_check.completed", {"outcome": "afwijking"}))
    assert afw and afw.ernst == "kritiek" and afw.rol == "probleem"
    an = classify(ev(hch, "sso.anomaly.detected", {"rule_id": "login_storm", "severity": "hoog"}, ("sso_anomaly", "a")))
    assert an and an.ernst == "kritiek"
    assert classify(ev(hch, "sso.access.revoked", {}, ("authentik_user", "leon"))) is None
