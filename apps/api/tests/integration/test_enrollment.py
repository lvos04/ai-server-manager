"""Enrollment volgens contract 1.3 §3.3–§3.8: exact schema (``schema_version`` 1.3, ``rotation_sequence``), tolerante
``base_url``, herhaling na herstart, herkoppelen (intrekken bij het eerste gebruik), services/self, rotatie, intrekken.

Positieve én negatieve scenario's: elk verboden veld of formaat → 422, elk ongeldig geheim → 401 (één code, geen
orakel), rate-limit → 429 met Retry-After; alleen hashes in de database.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

import psycopg
import pytest
from conftest import enroll_body, idem, service_jwk

pytestmark = pytest.mark.integration

FINGERPRINT = re.compile(r"^[0-9A-HJKMNP-TV-Z]{4}(-[0-9A-HJKMNP-TV-Z]{4}){3}$")


def _token(admin: Any, app_id: str = "jelly-leon-platform") -> str:
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id})
    assert r.status_code == 201, r.text
    return str(r.json()["enrollment_token"])


def _anon(app: Any, ip: str = "192.0.2.50") -> Any:
    from fastapi.testclient import TestClient

    return TestClient(app, base_url="https://testserver", client=(ip, 50000))


B64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def _non_canonical(x: str) -> str:
    return x[:-1] + B64URL[B64URL.index(x[-1]) ^ 1]  # laagste bit van het laatste teken is opvulling


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_enroll_antwoord_volgens_schema_1_3_en_eenmalig(admin: Any, app: Any, clean_db: str) -> None:
    from hub.keys import jwk_thumbprint, keyset_fingerprint

    tok = _token(admin)
    created = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "jelly-leon-platform"}).json()
    assert FINGERPRINT.match(created["keyset_fingerprint"])
    assert created["env"]["HUB_KEY_FINGERPRINT"] == created["keyset_fingerprint"]
    anon = _anon(app)
    jwk = service_jwk()
    r = anon.post(
        "/api/v1/services/enroll", json=enroll_body("jelly-leon-platform", token=tok, jwk=jwk, base_url="http://x:1")
    )
    assert r.status_code == 200, r.text
    assert r.headers["Cache-Control"] == "no-store"
    body = r.json()
    assert set(body) == {
        "schema_version",
        "service_id",
        "app_id",
        "service_token",
        "token_type",
        "hub_issuer",
        "jwks",
        "policy_public_key",
        "keyset_fingerprint",
        "jwks_url",
        "events_inbox_url",
        "key_rotation_url",
        "enrollment_replayed",
        "rotation_sequence",
    }
    assert body["schema_version"] == "1.3" and body["app_id"] == "jelly-leon-platform"
    # Nieuw in 1.3: de reeks van de sleutelrotatie (de Hub roteert nog niet: 0, gelijk aan key-rotations = []).
    assert body["rotation_sequence"] == 0 and type(body["rotation_sequence"]) is int
    assert re.fullmatch(r"svc_[A-Za-z0-9_-]{43}", body["service_token"])
    assert body["token_type"] == "Bearer" and body["hub_issuer"] == "hub" and body["enrollment_replayed"] is False
    assert body["key_rotation_url"] == "/api/v1/auth/key-rotations" and body["jwks_url"] == "/api/v1/auth/jwks"
    for k in [*body["jwks"]["keys"], body["policy_public_key"]]:
        assert (
            k["kty"] == "OKP" and k["crv"] == "Ed25519" and k["use"] == "sig" and k["alg"] == "EdDSA" and "d" not in k
        )
    # De vingerafdruk is zelf te berekenen uit het antwoord (wat elke dienst moet doen, §3.3).
    assert body["keyset_fingerprint"] == keyset_fingerprint(body["jwks"]["keys"], body["policy_public_key"])
    assert body["keyset_fingerprint"] == created["keyset_fingerprint"]
    # Bewaard als {kty, crv, x, kid=thumbprint}
    services = admin.get("/api/v1/services").json()["items"]
    assert services[0]["public_key_jwk"] == {**jwk, "kid": jwk_thumbprint(jwk)}
    assert services[0]["tokens"][0]["laatste4"] == body["service_token"][-4:]
    assert body["service_token"] not in str(services)
    # Bevestigen sluit de herhaling: daarna is hetzelfde token definitief gebruikt.
    me = anon.get("/api/v1/services/self", headers=_bearer(body["service_token"]))
    assert me.status_code == 200, me.text
    assert me.json() == {
        "service_id": body["service_id"],
        "app_id": "jelly-leon-platform",
        "status": "active",
        "version": "0.1.0",
        "enrolled_at": me.json()["enrolled_at"],
        "keyset_fingerprint": body["keyset_fingerprint"],
    }
    again = anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon-platform", token=tok, jwk=jwk))
    assert again.status_code == 401 and again.json()["code"] == "invalid_enrollment"
    with psycopg.connect(clean_db) as conn:
        dump = str(conn.execute("SELECT * FROM service_token").fetchall()) + str(
            conn.execute("SELECT * FROM enrollment_grant").fetchall()
        )
        assert body["service_token"] not in dump and tok not in dump
        assert all(len(row[0]) == 64 for row in conn.execute("SELECT token_hash FROM service_token").fetchall())


def test_toegestane_herhaling_na_herstart_halverwege(admin: Any, app: Any, clean_db: str) -> None:
    anon = _anon(app)
    tok, jwk = _token(admin, "home-control-hub"), service_jwk()
    first = anon.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=tok, jwk=jwk)).json()
    # Dienst crasht vóór het opslaan en probeert opnieuw met hetzelfde token en dezelfde sleutel → 200, nieuw token.
    second = anon.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=tok, jwk=jwk))
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["enrollment_replayed"] is True and body["service_id"] == first["service_id"]
    assert body["service_token"] != first["service_token"]
    assert anon.get("/api/v1/services/self", headers=_bearer(first["service_token"])).status_code == 401
    # Andere sleutel → geen herhaling (401, zelfde code)
    other = anon.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=tok, jwk=service_jwk()))
    assert other.status_code == 401 and other.json()["code"] == "invalid_enrollment"
    # Na bevestiging (token gebruikt) is de herhaling dicht.
    assert anon.get("/api/v1/services/self", headers=_bearer(body["service_token"])).status_code == 200
    closed = anon.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=tok, jwk=jwk))
    assert closed.status_code == 401
    assert anon.get("/api/v1/services/self", headers=_bearer(body["service_token"])).status_code == 200


def test_geen_herhaling_na_verlopen_of_intrekken(admin: Any, app: Any, clean_db: str) -> None:
    anon = _anon(app)
    tok, jwk = _token(admin, "appstore-en-fork"), service_jwk()
    svc = anon.post("/api/v1/services/enroll", json=enroll_body("appstore-en-fork", token=tok, jwk=jwk)).json()
    assert admin.post(f"/api/v1/services/{svc['service_id']}/revoke", headers=idem()).status_code == 200
    assert (
        anon.post("/api/v1/services/enroll", json=enroll_body("appstore-en-fork", token=tok, jwk=jwk)).status_code
        == 401
    )
    tok2, jwk2 = _token(admin, "zoeken-en-persoonlijke-ai"), service_jwk()
    assert (
        anon.post("/api/v1/services/enroll", json=enroll_body("zoeken-en-persoonlijke-ai", token=tok2, jwk=jwk2))
    ).status_code == 200
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE enrollment_grant SET expires_at = now() - interval '1 minute'")
    replay = anon.post("/api/v1/services/enroll", json=enroll_body("zoeken-en-persoonlijke-ai", token=tok2, jwk=jwk2))
    assert replay.status_code == 401


@pytest.mark.parametrize(
    ("change", "veld"),
    [
        ({"extra": 1}, "extra"),
        ({"kind": "token"}, "kind"),
        ({"capabilities": []}, "capabilities"),
        ({"version": ""}, "version"),
        ({"version": "-1"}, "version"),
        ({"version": "1" * 65}, "version"),
        ({"app_id": "Home-Control-Hub"}, "app_id"),
        ({"app_id": "a" * 41}, "app_id"),
        ({"app_id": "eindigt-op-"}, "app_id"),
        # 1.3 §3.3: alleen een ander type dan string/null is een schemafout (nooit de waarde van een string).
        ({"base_url": 5}, "base_url"),
        ({"base_url": ["http://x"]}, "base_url"),
        ({"base_url": {"url": "http://x"}}, "base_url"),
        ({"base_url": True}, "base_url"),
        ({"enrollment_token": "enr_te-kort"}, "enrollment_token"),
        ({"enrollment_token": "svc_" + "A" * 43}, "enrollment_token"),
    ],
)
def test_verzoek_met_fout_veld_geeft_422(admin: Any, app: Any, change: dict[str, Any], veld: str) -> None:
    body = enroll_body("jelly-leon", token=_token(admin, "jelly-leon")) | change
    r = _anon(app).post("/api/v1/services/enroll", json=body)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "validation_error"
    assert any(veld in f["veld"] for f in r.json()["details"]["fouten"]), r.json()


@pytest.mark.parametrize("missing", ["version", "base_url", "public_key_jwk", "app_id"])
def test_verplichte_velden(admin: Any, app: Any, missing: str) -> None:
    body = enroll_body("jelly-leon", token=_token(admin, "jelly-leon"))
    body.pop(missing)
    assert _anon(app).post("/api/v1/services/enroll", json=body).status_code == 422


def test_jwk_strikt(admin: Any, app: Any) -> None:
    anon = _anon(app)
    tok = _token(admin, "jelly-leon")
    good = service_jwk()
    other = service_jwk()
    for bad in (
        {**good, "use": "sig"},  # use/alg: weigeren, niet stil weglaten (contract 1.2 R3)
        {**good, "alg": "EdDSA"},
        {**good, "d": "geheim"},
        {**good, "kid": other["kid"]},  # kid moet de thumbprint zijn
        {**good, "kid": "abc123"},
        {**good, "x": good["x"][:-1]},
        {**good, "x": good["x"] + "A"},
        {**good, "x": _non_canonical(good["x"])},  # zelfde bytes, andere tekst: niet canoniek
        {**good, "crv": "X25519"},
        {**good, "kty": "EC"},
        {"kty": "OKP", "crv": "Ed25519"},
        {**good, "x": 12},
    ):
        r = anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", token=tok, jwk=bad))  # type: ignore[arg-type]
        assert r.status_code == 422, (bad, r.text)
    # kid mag ontbreken; de Hub berekent en bewaart de thumbprint
    no_kid = {k: v for k, v in good.items() if k != "kid"}
    r = anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", token=tok, jwk=no_kid))
    assert r.status_code == 200, r.text
    stored = admin.get("/api/v1/services").json()["items"][0]["public_key_jwk"]
    assert stored == good


def test_precies_een_geheim_en_koppelcodeformaat(admin: Any, app: Any) -> None:
    anon = _anon(app)
    tok = _token(admin, "jelly-leon")
    code = admin.post("/api/v1/services/pairing-codes", json={"app_id": "jelly-leon"}).json()["koppelcode"]
    assert anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon")).status_code == 422
    both = enroll_body("jelly-leon", token=tok, code=code)
    assert anon.post("/api/v1/services/enroll", json=both).status_code == 422
    for bad in ("ABCD-EFGH-JKM", "ABCD-EFGH-JKMNP", "UUUU-UUUU-UUUU", "", "A" * 33):
        r = anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", code=bad))
        assert r.status_code == 422, bad
    # 422 telt niet mee voor de rate-limit en gebruikt de code niet: daarna slaagt hij gewoon (genormaliseerd).
    ok = anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", code=code.lower().replace("-", " ")))
    assert ok.status_code == 200, ok.text


def test_koppelcode_en_executor(admin: Any, app: Any, settings: Any) -> None:
    from hub.timeutil import utcnow

    r = admin.post("/api/v1/services/pairing-codes", json={"app_id": "appstore-en-fork"})
    assert r.status_code == 201 and FINGERPRINT.match(r.json()["keyset_fingerprint"])
    anon = _anon(app)
    code = r.json()["koppelcode"]
    assert anon.post("/api/v1/services/enroll", json=enroll_body("appstore-en-fork", code=code)).status_code == 200
    assert anon.post("/api/v1/services/enroll", json=enroll_body("appstore-en-fork", code=code)).status_code == 401
    # Executor: alleen koppelcode, 30 minuten geldig (contract 1.2 §3.4, §3.9)
    tok = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "ai-server-manager-executor"})
    assert tok.status_code == 422 and tok.json()["code"] == "executor_requires_pairing_code"
    ex = admin.post("/api/v1/services/pairing-codes", json={"app_id": "ai-server-manager-executor"}).json()
    from datetime import datetime

    left = datetime.fromisoformat(ex["verloopt_op"].replace("Z", "+00:00")) - utcnow()
    assert timedelta(minutes=29) < left <= timedelta(minutes=30)
    r = anon.post("/api/v1/services/enroll", json=enroll_body("ai-server-manager-executor", code=ex["koppelcode"]))
    assert r.status_code == 200, r.text
    # De Hub meldt zich niet bij zichzelf aan
    assert admin.post("/api/v1/services/pairing-codes", json={"app_id": "ai-server-manager"}).status_code == 422


def test_verkeerde_app_en_verlopen_token(admin: Any, app: Any, clean_db: str) -> None:
    anon = _anon(app)
    tok = _token(admin, "home-control-hub")
    r = anon.post("/api/v1/services/enroll", json=enroll_body("andere-app", token=tok))
    assert r.status_code == 401 and r.json()["code"] == "invalid_enrollment"
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE enrollment_grant SET expires_at = now() - interval '1 minute'")
    assert anon.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=tok)).status_code == 401
    unknown = "enr_" + "B" * 43
    assert anon.post("/api/v1/services/enroll", json=enroll_body("home-control-hub", token=unknown)).status_code == 401


def test_rate_limit_per_bron_ip_met_retry_after(admin: Any, app: Any) -> None:
    attacker, other = _anon(app, "192.0.2.66"), _anon(app, "192.0.2.67")
    for _ in range(10):
        r = attacker.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", token="enr_" + "C" * 43))
        assert r.status_code == 401
    # 422 telt niet mee, maar ook een geldige poging krijgt nu 429 met Retry-After (nooit eerder opnieuw)
    tok = _token(admin, "jelly-leon")
    r = attacker.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", token=tok))
    assert r.status_code == 429 and r.json()["code"] == "rate_limited"
    assert 1 <= int(r.headers["Retry-After"]) <= 900
    # Een ander bron-IP heeft een eigen teller; een geslaagde enrollment wist die teller.
    assert other.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", token=tok)).status_code == 200


def test_rotatie_oud_token_vervalt_10_min_na_eerste_gebruik(admin: Any, app: Any, clean_db: str, settings: Any) -> None:
    anon = _anon(app)
    svc = anon.post(
        "/api/v1/services/enroll",
        json=enroll_body("zoeken-en-persoonlijke-ai", token=_token(admin, "zoeken-en-persoonlijke-ai")),
    ).json()
    old = svc["service_token"]
    assert anon.get("/api/v1/services/self", headers=_bearer(old)).status_code == 200
    rot = anon.post("/api/v1/services/self/rotate", headers=_bearer(old))
    assert rot.status_code == 200, rot.text
    assert rot.headers["Cache-Control"] == "no-store"
    new = rot.json()["service_token"]
    assert new != old and set(rot.json()) == {"service_id", "service_token", "oude_tokens_geldig_tot"}
    # Dienst crashte vóór het opslaan: oud token werkt nog, maar de Hub vraagt opnieuw rotatie.
    r = anon.get("/connector/v1/discover", headers=_bearer(old))
    assert r.status_code == 200 and r.headers.get("Hub-Token-Rotation") == "required"
    # Herhaalde rotatie trekt het nooit gebruikte nieuwe token in.
    rot2 = anon.post("/api/v1/services/self/rotate", headers=_bearer(old)).json()
    assert anon.get("/api/v1/services/self", headers=_bearer(new)).status_code == 401
    newest = rot2["service_token"]
    with psycopg.connect(clean_db) as conn:
        cap = conn.execute(
            "SELECT expires_at - now() FROM service_token WHERE superseded_at IS NOT NULL AND revoked_at IS NULL"
        ).fetchone()
    assert cap is not None and timedelta(hours=23) < cap[0] <= timedelta(hours=24)  # bovengrens 24 uur
    # Eerste gebruik van het nieuwe token: oud token vervalt 10 minuten later (niet meteen, geen buitensluiten).
    r = anon.get("/api/v1/services/self", headers=_bearer(newest))
    assert r.status_code == 200 and "Hub-Token-Rotation" not in r.headers
    with psycopg.connect(clean_db) as conn:
        left = conn.execute(
            "SELECT expires_at - now() FROM service_token WHERE superseded_at IS NOT NULL AND revoked_at IS NULL"
        ).fetchone()
    assert left is not None and timedelta(minutes=9) < left[0] <= timedelta(minutes=10)
    assert anon.get("/connector/v1/discover", headers=_bearer(old)).status_code == 200
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute(
            "UPDATE service_token SET expires_at = now() - interval '1 second' WHERE superseded_at IS NOT NULL"
        )
    r = anon.get("/connector/v1/discover", headers=_bearer(old))
    assert r.status_code == 401 and r.json()["code"] == "unauthorized"
    assert anon.get("/connector/v1/discover", headers=_bearer(newest)).status_code == 200


def test_rotatie_aanvragen_door_beheerder_geeft_202_zonder_token(admin: Any, app: Any) -> None:
    anon = _anon(app)
    svc = anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", token=_token(admin, "jelly-leon"))).json()
    tok = svc["service_token"]
    assert admin.post(f"/api/v1/services/{svc['service_id']}/rotate").status_code == 400  # Idempotency-Key verplicht
    key = idem()
    r = admin.post(f"/api/v1/services/{svc['service_id']}/rotate", headers=key)
    assert r.status_code == 202, r.text
    assert "service_token" not in r.json() and tok not in r.text and r.json()["status"] == "rotatie_aangevraagd"
    assert admin.post(f"/api/v1/services/{svc['service_id']}/rotate", headers=key).json() == r.json()
    listed = admin.get("/api/v1/services").json()["items"][0]
    assert listed["rotatie"]["aangevraagd_op"] and listed["rotatie"]["aanbevolen"] is False
    res = anon.get("/api/v1/services/self", headers=_bearer(tok))
    assert res.status_code == 200 and res.headers["Hub-Token-Rotation"] == "required"
    new = anon.post("/api/v1/services/self/rotate", headers=_bearer(tok)).json()["service_token"]
    res = anon.get("/api/v1/services/self", headers=_bearer(new))
    assert res.status_code == 200 and "Hub-Token-Rotation" not in res.headers
    assert admin.get("/api/v1/services").json()["items"][0]["rotatie"]["aangevraagd_op"] is None
    assert admin.post("/api/v1/services/00000000-0000-4000-8000-000000000000/rotate", headers=idem()).status_code == 404


def test_rotatie_melding_na_180_dagen(admin: Any, app: Any, clean_db: str) -> None:
    anon = _anon(app)
    anon.post("/api/v1/services/enroll", json=enroll_body("jelly-leon", token=_token(admin, "jelly-leon")))
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE service_token SET created_at = now() - interval '181 days'")
    rot = admin.get("/api/v1/services").json()["items"][0]["rotatie"]
    # Alleen een melding: de Hub roteert nooit zelf (geheimen roteren is R2).
    assert rot["aanbevolen"] is True and rot["token_leeftijd_dagen"] >= 181 and rot["aangevraagd_op"] is None


def test_intrekken_en_herinschrijving(admin: Any, app: Any) -> None:
    anon = _anon(app)
    first = anon.post(
        "/api/v1/services/enroll", json=enroll_body("jelly-leon", token=_token(admin, "jelly-leon"))
    ).json()
    second = anon.post(
        "/api/v1/services/enroll", json=enroll_body("jelly-leon", token=_token(admin, "jelly-leon"))
    ).json()
    assert second["service_id"] == first["service_id"]  # service_id blijft gelijk bij opnieuw koppelen
    # 1.3 §3.6: het oude token blijft geldig tot het eerste gebruik van het nieuwe (geen Hub-Token-Rotation).
    old = anon.get("/connector/v1/discover", headers=_bearer(first["service_token"]))
    assert old.status_code == 200 and "Hub-Token-Rotation" not in old.headers
    assert anon.get("/connector/v1/discover", headers=_bearer(second["service_token"])).status_code == 200
    assert anon.get("/connector/v1/discover", headers=_bearer(first["service_token"])).status_code == 401
    r = admin.post(f"/api/v1/services/{second['service_id']}/revoke", headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "revoked"
    r = anon.get("/api/v1/services/self", headers=_bearer(second["service_token"]))
    assert r.status_code == 401 and r.json()["code"] == "unauthorized"


@pytest.mark.parametrize(
    ("base_url", "bewaard", "genegeerd"),
    [
        ("http://192.0.2.5:30401", "http://192.0.2.5:30401", False),
        ("https://hch.lan/pad/", "https://hch.lan/pad", False),
        (None, None, False),
        ("ftp://x", None, True),
        ("http://x/?q=1", None, True),
        ("http://127.1:30401", None, True),
        ("http://2130706433", None, True),
        ("http://127.0.0.1:30401", None, True),
        ("http://169.254.169.254", None, True),
        ("http://user:pw@nas:1", None, True),
        ("http://nas:1/" + "p" * 600, None, True),
        ("geen url", None, True),
        (" http://192.0.2.5:1", None, True),
    ],
)
def test_base_url_nooit_reden_voor_weigering(
    admin: Any, app: Any, base_url: str | None, bewaard: str | None, genegeerd: bool
) -> None:
    """C1.3-ASM-02: een base_url die niet aan §3.3 voldoet → null + waarschuwing in de Hub-UI, nooit 422."""
    body = enroll_body("home-control-hub", token=_token(admin, "home-control-hub"), base_url=base_url)
    r = _anon(app).post("/api/v1/services/enroll", json=body)
    assert r.status_code == 200, r.text
    item = next(i for i in admin.get("/api/v1/services").json()["items"] if i["app_id"] == "home-control-hub")
    assert item["base_url"] == bewaard and item["base_url_genegeerd"] is genegeerd


def test_herkoppelen_trekt_oude_tokens_pas_in_bij_eerste_gebruik_en_nieuw_vervalt_na_60_min(
    admin: Any, app: Any, clean_db: str
) -> None:
    """§3.6 (1.3): een mislukte herkoppeling (de dienst weigert het antwoord, bv. verkeerde vingerafdruk) breekt een
    bestaande koppeling niet: het nieuwe token vervalt na 60 min ongebruikt en de oude blijven geldig."""
    anon = _anon(app)
    first = anon.post(
        "/api/v1/services/enroll", json=enroll_body("appstore-en-fork", token=_token(admin, "appstore-en-fork"))
    ).json()
    assert anon.get("/api/v1/services/self", headers=_bearer(first["service_token"])).status_code == 200
    second = anon.post(
        "/api/v1/services/enroll", json=enroll_body("appstore-en-fork", token=_token(admin, "appstore-en-fork"))
    ).json()
    item = next(i for i in admin.get("/api/v1/services").json()["items"] if i["app_id"] == "appstore-en-fork")
    nieuw = next(t for t in item["tokens"] if t["laatste4"] == second["service_token"][-4:])
    assert nieuw["verloopt"] is not None and nieuw["geldig"] is True  # termijn van 60 min tot het eerste gebruik
    # Het nieuwe token blijft ongebruikt: na 60 min vervalt het; het oude werkt gewoon door.
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute(
            "UPDATE service_token SET expires_at = now() - interval '1 second' WHERE last4 = %s",
            (second["service_token"][-4:],),
        )
    assert anon.get("/api/v1/services/self", headers=_bearer(second["service_token"])).status_code == 401
    assert anon.get("/api/v1/services/self", headers=_bearer(first["service_token"])).status_code == 200
    # Een geslaagde herkoppeling: bij het eerste gebruik van het nieuwe token vervallen de oude direct.
    third = anon.post(
        "/api/v1/services/enroll", json=enroll_body("appstore-en-fork", token=_token(admin, "appstore-en-fork"))
    ).json()
    assert anon.get("/api/v1/services/self", headers=_bearer(third["service_token"])).status_code == 200
    assert anon.get("/api/v1/services/self", headers=_bearer(first["service_token"])).status_code == 401
    item = next(i for i in admin.get("/api/v1/services").json()["items"] if i["app_id"] == "appstore-en-fork")
    actief = [t for t in item["tokens"] if t["geldig"]]
    assert [t["laatste4"] for t in actief] == [third["service_token"][-4:]] and actief[0]["verloopt"] is None
    # Intrekken door de beheerder blijft direct (§3.8).
    admin.post(f"/api/v1/services/{third['service_id']}/revoke", headers=idem())
    assert anon.get("/api/v1/services/self", headers=_bearer(third["service_token"])).status_code == 401


def test_oude_installatie_roteert_zonder_het_wachtende_token_in_te_trekken(admin: Any, app: Any) -> None:
    anon = _anon(app)
    first = anon.post(
        "/api/v1/services/enroll", json=enroll_body("jelly-leon-platform", token=_token(admin, "jelly-leon-platform"))
    ).json()
    second = anon.post(
        "/api/v1/services/enroll", json=enroll_body("jelly-leon-platform", token=_token(admin, "jelly-leon-platform"))
    ).json()
    rot = anon.post("/api/v1/services/self/rotate", headers=_bearer(first["service_token"]))
    assert rot.status_code == 200
    # Het nieuwe token uit de herkoppeling is niet ingetrokken door de rotatie van de oude installatie.
    assert anon.get("/api/v1/services/self", headers=_bearer(second["service_token"])).status_code == 200
    # En nu het in gebruik is, vervallen alle andere (ook het net geroteerde token van de oude installatie).
    assert anon.get("/api/v1/services/self", headers=_bearer(rot.json()["service_token"])).status_code == 401
