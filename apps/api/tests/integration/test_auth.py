"""Setupcode → eerste admin, login/logout, CSRF, rollen, rate-limit, sessies, JWKS en dienst-JWT."""

from __future__ import annotations

from typing import Any

import jwt
import pytest
from conftest import STRONG_PASSWORD, idem, login_as, make_user

pytestmark = pytest.mark.integration


def test_setup_status_en_foute_code_met_rate_limit(client: Any, setup_code: str) -> None:
    assert client.get("/api/v1/setup/status").json()["setup_vereist"] is True
    for _ in range(5):
        r = client.post(
            "/api/v1/setup/admin",
            json={"setup_code": "AAAA-BBBB-CCCC", "username": "beheerder", "password": STRONG_PASSWORD},
        )
        assert r.status_code == 401 and r.json()["code"] == "invalid_setup_code"
        assert r.json()["trace_id"]
    r = client.post(
        "/api/v1/setup/admin", json={"setup_code": setup_code, "username": "beheerder", "password": STRONG_PASSWORD}
    )
    assert r.status_code == 429 and r.headers["Retry-After"]


def test_setup_maakt_admin_en_sessie(client: Any, setup_code: str) -> None:
    r = client.post("/api/v1/setup/admin", json={"setup_code": setup_code, "username": "beheerder", "password": "kort"})
    assert r.status_code == 422 and r.json()["code"] == "weak_password"
    r = client.post(
        "/api/v1/setup/admin",
        json={"setup_code": setup_code.lower(), "username": "beheerder", "password": STRONG_PASSWORD},
    )
    assert r.status_code == 200, r.text
    cookie = r.headers.get_list("set-cookie")
    assert any("hub_session=" in c and "HttpOnly" in c and "SameSite=strict" in c and "Secure" in c for c in cookie)
    assert r.json()["user"]["role"] == "admin"
    assert client.get("/api/v1/auth/me").json()["user"]["username"] == "beheerder"
    r = client.post(
        "/api/v1/setup/admin", json={"setup_code": setup_code, "username": "tweede", "password": STRONG_PASSWORD}
    )
    assert r.status_code == 409
    assert client.get("/api/v1/setup/status").json()["setup_vereist"] is False


def test_setupcode_eenmalig_ook_bij_gelijktijdige_verzoeken(
    client: Any, app: Any, settings: Any, setup_code: str
) -> None:
    """Twee verzoeken tegelijk met dezelfde geldige code mogen nooit twee beheerders opleveren.

    Deterministisch: een tweede verbinding houdt de setup-lock vast; het verzoek moet wachten en ná de lock opnieuw
    controleren. Intussen ontstaat (zoals bij een gelijktijdig verzoek) al een beheerder → het verzoek krijgt 409.
    """
    import threading
    import time

    import psycopg
    from conftest import _libpq

    from hub.models import User
    from hub.routers.auth import SETUP_LOCK_KEY
    from hub.security import hash_password

    holder = psycopg.connect(_libpq(settings.database_url))
    holder.execute("SELECT pg_advisory_lock(%s)", (SETUP_LOCK_KEY,))
    result: dict[str, Any] = {}

    def attempt() -> None:
        result["r"] = client.post(
            "/api/v1/setup/admin", json={"setup_code": setup_code, "username": "tweede", "password": STRONG_PASSWORD}
        )

    t = threading.Thread(target=attempt)
    t.start()
    try:
        time.sleep(1.0)
        assert "r" not in result, "het verzoek wachtte niet op de setup-lock"
        with app.state.sessionmaker() as db:
            db.add(User(username="eerste", password_hash=hash_password(STRONG_PASSWORD), role="admin"))
            db.commit()
    finally:
        holder.execute("SELECT pg_advisory_unlock(%s)", (SETUP_LOCK_KEY,))
        holder.close()
        t.join(30)
    assert result["r"].status_code == 409 and result["r"].json()["code"] == "setup_already_done"
    with app.state.sessionmaker() as db:
        from sqlalchemy import func, select

        assert db.scalar(select(func.count()).select_from(User).where(User.role == "admin")) == 1
    # De markering is hersteld: een nieuwe start (hub init) toont geen setupcode meer.
    from hub.firststart import ensure_secrets, setup_pending

    assert setup_pending(settings.secrets_dir) is False
    assert ensure_secrets(settings.secrets_dir, new_setup_code=True).setup_code is None


def test_ontbrekende_setupmarkering_wordt_hersteld(client: Any, app: Any, settings: Any, setup_code: str) -> None:
    """Beheerder bestaat al (bv. stroomuitval vlak na de commit): geen setup meer en geen nieuwe code in de log."""
    from hub.models import User
    from hub.security import hash_password

    with app.state.sessionmaker() as db:
        db.add(User(username="beheerder", password_hash=hash_password(STRONG_PASSWORD), role="admin"))
        db.commit()
    assert client.get("/api/v1/setup/status").json()["setup_vereist"] is False
    r = client.post(
        "/api/v1/setup/admin", json={"setup_code": setup_code, "username": "tweede", "password": STRONG_PASSWORD}
    )
    assert r.status_code == 409
    from hub.firststart import ensure_secrets

    assert ensure_secrets(settings.secrets_dir, new_setup_code=True).setup_code is None


def test_csrf_vereist_voor_mutaties(admin: Any) -> None:
    token = admin.headers.pop("X-CSRF-Token")
    r = admin.post("/api/v1/inventory/refresh", headers=idem())
    assert r.status_code == 403 and r.json()["code"] == "csrf_failed"
    admin.headers["X-CSRF-Token"] = token
    assert admin.post("/api/v1/inventory/refresh", headers=idem()).status_code == 202


def test_rollen_viewer_en_kind(admin: Any, app: Any) -> None:
    make_user(admin, "kijker", "viewer")
    make_user(admin, "kind1", "kind")
    make_user(admin, "operator1", "operator")
    viewer = login_as(app, "kijker")
    assert viewer.get("/api/v1/inventory").status_code == 200
    assert viewer.get("/api/v1/gates").status_code == 200
    r = viewer.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "192.0.2.1"}}, headers=idem())
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    assert viewer.post("/api/v1/inventory/refresh", headers=idem()).status_code == 403
    assert viewer.put("/api/v1/truenas/api-key", json={"api_key": "x" * 20}, headers=idem()).status_code == 403
    assert viewer.get("/api/v1/users").status_code == 403
    assert viewer.get("/api/v1/audit").status_code == 403
    kind = login_as(app, "kind1")
    assert kind.get("/api/v1/inventory").status_code == 403
    assert kind.get("/api/v1/decisions").status_code == 403
    assert kind.get("/api/v1/auth/me").status_code == 200
    op = login_as(app, "operator1")
    assert op.post("/api/v1/inventory/refresh", headers=idem()).status_code == 202
    assert (
        op.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "192.0.2.1"}}, headers=idem()).status_code
        == 403
    )


def test_niet_aangemeld_is_401(client: Any) -> None:
    for path in (
        "/api/v1/inventory",
        "/api/v1/decisions",
        "/api/v1/gates",
        "/api/v1/backups/coverage",
        "/connector/v1/discover",
    ):
        r = client.get(path)
        assert r.status_code == 401 and r.json()["code"] == "unauthorized", path


def test_login_rate_limit_en_logout(admin: Any, app: Any) -> None:
    make_user(admin, "gebruiker", "viewer")
    from fastapi.testclient import TestClient

    c = TestClient(app, base_url="https://testserver")
    for _ in range(5):
        assert c.post("/api/v1/auth/login", json={"username": "gebruiker", "password": "fout"}).status_code == 401
    assert c.post("/api/v1/auth/login", json={"username": "gebruiker", "password": STRONG_PASSWORD}).status_code == 429
    other = login_as(app, "beheerder")
    assert other.post("/api/v1/auth/logout").status_code == 204
    assert other.get("/api/v1/auth/me").status_code == 401


def test_sessie_intrekken_en_wachtwoord_wijzigen(admin: Any, app: Any) -> None:
    second = login_as(app, "beheerder")
    sessions = admin.get("/api/v1/auth/sessions").json()["items"]
    assert len(sessions) == 2
    other_id = next(s["id"] for s in sessions if not s["huidige"])
    assert admin.post(f"/api/v1/auth/sessions/{other_id}/revoke", headers=idem()).status_code == 200
    assert second.get("/api/v1/auth/me").status_code == 401
    third = login_as(app, "beheerder")
    r = admin.post(
        "/api/v1/auth/password",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "nieuw_wachtwoord": "Een-Ander-Sterk-Wachtwoord-7"},
    )
    assert r.status_code == 200
    assert third.get("/api/v1/auth/me").status_code == 401
    assert admin.get("/api/v1/auth/me").status_code == 200


def test_wachtwoord_wijzigen_heeft_rate_limit_op_het_huidige_wachtwoord(admin: Any) -> None:
    for _ in range(5):  # login_max_failures in de testinstellingen
        r = admin.post(
            "/api/v1/auth/password", json={"huidig_wachtwoord": "fout-geraden", "nieuw_wachtwoord": "Iets-Nieuws-1234"}
        )
        assert r.status_code == 401 and r.json()["code"] == "invalid_credentials"
    r = admin.post(
        "/api/v1/auth/password",
        json={"huidig_wachtwoord": STRONG_PASSWORD, "nieuw_wachtwoord": "Een-Ander-Sterk-Wachtwoord-7"},
    )
    assert r.status_code == 429 and r.headers["Retry-After"]
    assert admin.get("/api/v1/auth/me").status_code == 200


def test_laatste_admin_beschermd_en_degraderen_trekt_sessies_in(admin: Any, app: Any) -> None:
    me = admin.get("/api/v1/auth/me").json()["user"]["id"]
    r = admin.patch(f"/api/v1/users/{me}", json={"role": "viewer"}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "last_admin"
    make_user(admin, "operator2", "operator")
    op = login_as(app, "operator2")
    users = {u["username"]: u for u in admin.get("/api/v1/users").json()["items"]}
    assert (
        admin.patch(f"/api/v1/users/{users['operator2']['id']}", json={"disabled": True}, headers=idem()).status_code
        == 200
    )
    assert op.get("/api/v1/auth/me").status_code == 401
    assert "password_hash" not in str(users)


def test_jwks_en_dienst_jwt(admin: Any) -> None:
    jwks = admin.get("/api/v1/auth/jwks").json()
    r = admin.post("/api/v1/auth/service-jwt", json={"audience": "zoeken-en-persoonlijke-ai"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    key = jwt.PyJWK(jwks["keys"][0]).key
    claims = jwt.decode(token, key, algorithms=["EdDSA"], audience="zoeken-en-persoonlijke-ai", issuer="hub")
    assert claims["roles"] == ["admin"] and claims["exp"] - claims["iat"] <= 120
    assert admin.post("/api/v1/auth/service-jwt", json={"audience": "onbekend-iets"}).status_code == 404


def test_gezondheid_en_statuspagina(client: Any) -> None:
    assert client.get("/healthz").json()["status"] == "ok"
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json()["status"] == "ready"
    page = client.get("/")
    assert page.status_code == 200 and "setupcode" in page.text and "TrueNAS → Apps" in page.text
    assert client.get("/healthz").headers["X-Trace-Id"]


def test_uniform_foutformaat(admin: Any) -> None:
    r = admin.get("/api/v1/bestaat-niet")
    assert r.status_code == 404 and set(r.json()) == {"code", "message", "details", "trace_id"}
    r = admin.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "192.0.2.1"}})
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"


def test_verzoek_groter_dan_1_mib_geeft_413_ook_zonder_content_length(admin: Any) -> None:
    big = b'{"waarde": {"nas_adres": "' + b"a" * (1024 * 1024 + 10) + b'"}}'
    # Met Content-Length: direct geweigerd.
    r = admin.put("/api/v1/decisions/D03/waarde", content=big, headers={**idem(), "content-type": "application/json"})
    assert r.status_code == 413 and r.json()["code"] == "payload_too_large"

    # Zonder Content-Length (chunked): tijdens het lezen afgebroken, niet eerst alles in het geheugen.
    def chunks() -> Any:
        for i in range(0, len(big), 64 * 1024):
            yield big[i : i + 64 * 1024]

    r = admin.put(
        "/api/v1/decisions/D03/waarde", content=chunks(), headers={**idem(), "content-type": "application/json"}
    )
    assert r.status_code == 413 and r.json()["code"] == "payload_too_large", r.text
    assert r.json()["trace_id"]
    # Ook op een publieke route (vóór aanmelding).
    r = admin.post("/api/v1/auth/login", content=chunks(), headers={"content-type": "application/json"})
    assert r.status_code == 413
    # Contractformaat §5: details.max_bytes en dezelfde trace_id als de header.
    assert r.json()["details"] == {"max_bytes": 1048576}
    assert r.json()["trace_id"] == r.headers["X-Trace-Id"]
    # Gewone verzoeken blijven werken.
    assert admin.get("/api/v1/decisions/D03").status_code == 200


def test_413_valt_voor_routering_en_aanmelding_ook_chunked(client: Any) -> None:
    """Contract 1.2 §5: de grens zit vóór routering en authenticatie — ook bij een route die de body zelf niet leest,
    zonder aanmelding, of op een pad/methode die niet bestaat (nooit eerst 401/404/405)."""

    def chunks(total: int) -> Any:
        sent = 0
        while sent < total:
            n = min(64 * 1024, total - sent)
            sent += n
            yield b"x" * n

    over = 1024 * 1024 + 1
    for method, path in (
        ("POST", "/api/v1/services/00000000-0000-4000-8000-000000000000/rotate"),  # admin-route zonder body
        ("POST", "/api/v1/auth/logout"),  # route zonder body-parameter
        ("POST", "/api/v1/services/enroll"),  # publieke route met body
        ("POST", "/healthz"),  # methode bestaat niet (anders 405)
        ("PUT", "/api/v1/bestaat-niet"),  # route bestaat niet (anders 404)
    ):
        r = client.request(method, path, content=chunks(over), headers={**idem(), "content-type": "application/json"})
        assert r.status_code == 413, f"{method} {path}: {r.status_code} {r.text[:120]}"
        assert r.json()["code"] == "payload_too_large" and r.json()["details"]["max_bytes"] == 1048576
        # Met een te grote Content-Length: direct, zonder de body te lezen.
        r = client.request(method, path, content=b"x" * over, headers=idem())
        assert r.status_code == 413, f"{method} {path} (Content-Length): {r.status_code}"
    # Precies 1 MiB is toegestaan: dan bepaalt de route het antwoord (hier: geen aanmelding → 401).
    r = client.post(
        "/api/v1/services/00000000-0000-4000-8000-000000000000/rotate",
        content=chunks(1024 * 1024),
        headers={**idem(), "content-type": "application/json"},
    )
    assert r.status_code == 401 and r.json()["code"] == "unauthorized"
