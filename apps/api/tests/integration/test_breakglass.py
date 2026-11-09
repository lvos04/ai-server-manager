"""Noodlogin (contract 1.2 §4.1): TOTP verplicht, alleen privé-bronadressen, sessie ≤ 60 min, audit + event,
rotatieplicht, rate-limit per (account, bron-IP), zelftest zonder mutatie, geen 'OIDC verplicht' zonder noodaccount."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any

import psycopg
import pytest
from conftest import STRONG_PASSWORD

from hub import breakglass
from hub.timeutil import utcnow

pytestmark = pytest.mark.integration

NOOD_PW = "Paraplu-Vuurtoren-Lang-Genoeg-2026!"


def _client(app: Any, ip: str) -> Any:
    from fastapi.testclient import TestClient

    return TestClient(app, base_url="https://testserver", client=(ip, 40000))


def _fresh_step() -> None:
    """Niet vlak voor een TOTP-tijdstapgrens beginnen: de tests rekenen op dezelfde stap binnen enkele seconden."""
    left = 30 - time.time() % 30
    if left < 6:
        time.sleep(left + 0.2)


def _setup(admin: Any) -> dict[str, Any]:
    _fresh_step()
    r = admin.post(
        "/api/v1/auth/break-glass/setup",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "username": "nood", "password": NOOD_PW, "sessieduur_minuten": 60},
    )
    assert r.status_code == 201, r.text
    assert r.headers["Cache-Control"] == "no-store"
    return r.json()


def _code(secret: str, offset: int = 0) -> str:
    return breakglass.totp_at(secret, breakglass.time_step(utcnow()) + offset)


def _login(app: Any, ip: str, totp: str, password: str = NOOD_PW) -> Any:
    return _client(app, ip).post(
        "/api/v1/auth/break-glass/login", json={"username": "nood", "password": password, "totp": totp}
    )


def test_instellen_bevestigen_en_inloggen(admin: Any, app: Any, clean_db: str) -> None:
    from sqlalchemy.orm import Session

    st = admin.get("/api/v1/auth/break-glass").json()
    assert st["noodaccount"] is None and st["werkend"] is False and st["oidc_verplicht_mogelijk"] is False
    created = _setup(admin)
    secret = created["totp"]["geheim"]
    assert created["noodaccount"]["break_glass"] is True and created["noodaccount"]["role"] == "admin"
    st = admin.get("/api/v1/auth/break-glass").json()
    assert st["noodaccount"]["totp_wacht_op_bevestiging"] is True and st["werkend"] is False
    # Geheim staat versleuteld in de vault, nooit leesbaar in de database
    with psycopg.connect(clean_db) as conn:
        dump = str(conn.execute("SELECT * FROM app_user").fetchall()) + str(
            conn.execute("SELECT * FROM vault_secret").fetchall()
        )
    assert secret not in dump
    # Voor bevestiging kan de noodlogin niet
    assert _login(app, "192.168.1.20", _code(secret)).status_code == 401
    assert admin.post("/api/v1/auth/break-glass/confirm", json={"totp": "000000"}).status_code == 401
    r = admin.post("/api/v1/auth/break-glass/confirm", json={"totp": _code(secret)})
    assert r.status_code == 200, r.text
    assert r.json()["werkend"] is True and r.json()["oidc_verplicht_mogelijk"] is True
    # Gewone login met het noodaccount kan nooit (TOTP is verplicht)
    plain = _client(app, "192.168.1.20").post("/api/v1/auth/login", json={"username": "nood", "password": NOOD_PW})
    assert plain.status_code == 401
    # Een al gebruikte code (tijdstap van de bevestiging) wordt geweigerd; de volgende code werkt.
    assert _login(app, "192.168.1.20", _code(secret)).status_code == 401
    ok = _login(app, "192.168.1.20", _code(secret, 1))
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["noodlogin"] is True and body["user"]["break_glass"] is True
    left = datetime.fromisoformat(body["sessie_verloopt_op"].replace("Z", "+00:00")) - utcnow()
    assert timedelta(minutes=59) < left <= timedelta(minutes=60)
    with psycopg.connect(clean_db) as conn:
        ev = conn.execute("SELECT event_type, classification FROM event_outbox").fetchall()
        audit = [r[0] for r in conn.execute("SELECT action FROM audit_event").fetchall()]
        sess = conn.execute("SELECT break_glass, expires_at - created_at FROM web_session WHERE break_glass").fetchall()
    assert ("auth.break_glass.used", "sensitive") in ev
    assert "auth.break_glass.used" in audit and "auth.break_glass_login" in audit
    assert len(sess) == 1 and sess[0][1] <= timedelta(minutes=60)
    st = admin.get("/api/v1/auth/break-glass").json()["noodaccount"]
    assert st["rotatie_vereist"] is True and st["laatst_gebruikt"]
    # Noodaccount wijzigt zijn wachtwoord alleen via roteren
    nood = _client(app, "192.168.1.20")
    nood.cookies.update(ok.cookies)
    nood.headers["X-CSRF-Token"] = body["csrf_token"]
    pw = nood.post("/api/v1/auth/password", json={"huidig_wachtwoord": NOOD_PW, "nieuw_wachtwoord": NOOD_PW + "x"})
    assert pw.status_code == 409 and pw.json()["code"] == "use_break_glass_rotate"
    # Rotatieplicht: roteren + bevestigen wist de plicht
    rot = admin.post(
        "/api/v1/auth/break-glass/rotate",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "nieuw_wachtwoord": NOOD_PW + "-nieuw"},
    )
    assert rot.status_code == 200, rot.text
    new_secret = rot.json()["totp"]["geheim"]
    assert new_secret != secret
    assert admin.get("/api/v1/auth/break-glass").json()["werkend"] is False  # nieuwe TOTP nog niet bevestigd
    assert admin.post("/api/v1/auth/break-glass/confirm", json={"totp": _code(new_secret)}).status_code == 200
    st = admin.get("/api/v1/auth/break-glass").json()["noodaccount"]
    assert st["rotatie_vereist"] is False and st["herbevestiging_nodig"] is False
    with Session(app.state.engine) as db:
        breakglass.assert_oidc_required_allowed(db)  # werkend noodaccount: 'OIDC verplicht' mag (B13)


def test_alleen_prive_bronadres_en_rate_limit_per_account_en_ip(admin: Any, app: Any) -> None:
    secret = _setup(admin)["totp"]["geheim"]
    assert admin.post("/api/v1/auth/break-glass/confirm", json={"totp": _code(secret)}).status_code == 200
    # Publiek adres: geweigerd, ook met juiste gegevens
    r = _login(app, "203.0.113.7", _code(secret, 1))
    assert r.status_code == 403 and r.json()["code"] == "source_not_private"
    assert _login(app, "127.0.0.1", _code(secret, 1)).status_code == 403
    # Vijf foute pogingen vanaf één LAN-adres blokkeren alleen dat adres, niet het account
    for _ in range(5):
        assert _login(app, "192.168.1.66", "000000", password="fout-wachtwoord-x").status_code == 401
    blocked = _login(app, "192.168.1.66", _code(secret, 1))
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) >= 1
    assert _login(app, "10.0.0.8", _code(secret, 1)).status_code == 200
    # Fout wachtwoord met juiste code, of juist wachtwoord met foute code: altijd dezelfde 401
    assert _login(app, "10.0.0.9", _code(secret, 1), password="x" * 25).json()["code"] == "invalid_credentials"


def test_zelftest_zonder_mutatie_toont_bron_ip(admin: Any, app: Any, clean_db: str) -> None:
    r = admin.post("/api/v1/auth/break-glass/selftest")
    assert r.status_code == 200, r.text
    checks = {c["naam"]: c for c in r.json()["controles"]}
    assert r.json()["resultaat"] == "niet_ok" and checks["noodaccount"]["status"] == "fout"
    assert checks["bereik_binnen"]["status"] == "ok" and checks["bereik_buiten"]["adres"] == "192.0.2.10"
    assert checks["bron_ip"]["adres"] == "testclient" and checks["bron_ip"]["prive"] is False
    secret = _setup(admin)["totp"]["geheim"]
    admin.post("/api/v1/auth/break-glass/confirm", json={"totp": _code(secret)})
    with psycopg.connect(clean_db) as conn:
        before = conn.execute("SELECT count(*) FROM audit_event").fetchone()
    r = admin.post("/api/v1/auth/break-glass/selftest")
    assert r.json()["resultaat"] == "ok"
    with psycopg.connect(clean_db) as conn:
        assert conn.execute("SELECT count(*) FROM audit_event").fetchone() == before  # geen mutatie
    gw = breakglass.selftest  # Docker-gateway als bron: waarschuwing, de harde controles blijven ok
    from sqlalchemy.orm import Session

    with Session(app.state.engine) as db:
        res = gw(db, "172.17.0.1")
    bron = next(c for c in res["controles"] if c["naam"] == "bron_ip")
    assert bron["lijkt_docker_gateway"] is True and bron["status"] == "waarschuwing" and res["resultaat"] == "ok"


def test_negatieve_gevallen_instellen(admin: Any, app: Any) -> None:
    from sqlalchemy.orm import Session

    with Session(app.state.engine) as db, pytest.raises(Exception, match="noodaccount"):
        breakglass.assert_oidc_required_allowed(db)
    base = {"huidig_wachtwoord": STRONG_PASSWORD, "username": "nood", "password": NOOD_PW}
    assert admin.post("/api/v1/auth/break-glass/setup", json={**base, "huidig_wachtwoord": "fout"}).status_code == 401
    r = admin.post("/api/v1/auth/break-glass/setup", json={**base, "password": "kort-maar-19-tekens"})
    assert r.status_code == 422 and r.json()["code"] == "weak_password"
    r = admin.post("/api/v1/auth/break-glass/setup", json={**base, "password": "nood-nood-nood-nood-nood"})
    assert r.status_code == 422
    assert admin.post("/api/v1/auth/break-glass/setup", json={**base, "sessieduur_minuten": 241}).status_code == 422
    assert admin.post("/api/v1/auth/break-glass/setup", json={**base, "sessieduur_minuten": 4}).status_code == 422
    rot = {"huidig_wachtwoord": STRONG_PASSWORD, "nieuw_wachtwoord": NOOD_PW}
    assert admin.post("/api/v1/auth/break-glass/rotate", json=rot).status_code == 404
    _setup(admin)
    assert admin.post("/api/v1/auth/break-glass/setup", json=base).status_code == 409
    # Het noodaccount blijft admin
    users = admin.get("/api/v1/users").json()["items"]
    nood = next(u for u in users if u["username"] == "nood")
    from conftest import idem

    r = admin.patch(f"/api/v1/users/{nood['id']}", json={"role": "viewer"}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "break_glass_stays_admin"
