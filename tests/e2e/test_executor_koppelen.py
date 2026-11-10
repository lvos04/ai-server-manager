"""Dienst-E2E: executor koppelt met de **echte** Hub-API (contract 1.2 §3.3, §3.9, §4.3–§4.7; Sim-getest, geen NAS).

Beide draaien als echte HTTP-server (uvicorn op 127.0.0.1): de executor roept de Hub aan met ``http.client`` en de Hub
roept de executor aan met een dienst-JWT. Getest: koppelcode + vingerafdruk via de statuspagina (CSRF + Origin,
throttle), pinning in ``hub-link.json`` (0600), bevestiging met ``services/self``, formulier weg na de eerste koppeling,
inkomende JWT-controle met de vaste redenen, en ontkoppelen via de Hub dat de executor eerlijk weigert (501).
"""

from __future__ import annotations

import json
import re
import stat
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from conftest import idem

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


class Served:
    def __init__(self, app: Any) -> None:
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        deadline = time.monotonic() + 15
        while not self.server.started:
            if time.monotonic() > deadline:
                raise RuntimeError("server start niet")
            time.sleep(0.05)
        port = self.server.servers[0].sockets[0].getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=10)


@pytest.fixture
def hub(app: Any) -> Iterator[Served]:
    s = Served(app)
    yield s
    s.stop()


@pytest.fixture
def executor(tmp_path: Path) -> Iterator[tuple[Any, Any]]:
    from executor.app import create_app
    from executor.config import Settings
    from executor.firststart import ensure_secrets

    settings = Settings(data_dir=tmp_path / "executor", allow_loopback_hub=True)
    ensure_secrets(settings.secrets_dir)
    yield create_app(settings), settings


def _page_client(app: Any) -> Any:
    from fastapi.testclient import TestClient

    return TestClient(app, base_url="http://executor.test")


def _submit(c: Any, hub_url: str, code: str, fingerprint: str, *, origin: str = "http://executor.test") -> Any:
    page = c.get("/")
    m = re.search(r'name="csrf" value="([^"]+)"', page.text)
    csrf = m.group(1) if m else ""
    return c.post(
        "/koppelen",
        data={"csrf": csrf, "hub_url": hub_url, "koppelcode": code, "vingerafdruk": fingerprint},
        headers={"Origin": origin},
    )


def _pairing(admin: Any) -> dict[str, Any]:
    r = admin.post("/api/v1/services/pairing-codes", json={"app_id": "ai-server-manager-executor"})
    assert r.status_code == 201, r.text
    return dict(r.json())


def test_executor_koppelt_met_koppelcode_en_vingerafdruk(
    admin: Any, app: Any, hub: Served, executor: tuple[Any, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    ex_app, ex_settings = executor
    grant = _pairing(admin)
    c = _page_client(ex_app)
    assert "Koppelen met de Hub" in c.get("/").text
    r = _submit(c, hub.url, grant["koppelcode"].lower(), grant["keyset_fingerprint"].replace("-", " "))
    assert r.status_code == 200, r.text
    assert "Gekoppeld met de Hub" in r.text and grant["keyset_fingerprint"] in r.text
    link_file = ex_settings.secrets_dir / "hub-link.json"
    assert stat.S_IMODE(link_file.stat().st_mode) == 0o600
    link = json.loads(link_file.read_text())
    assert link["state"] == "gekoppeld" and link["confirmed_at"] and link["via"] == "koppelcode"
    assert link["pending"] is None and link["last_error"] is None and link["first_linked_at"]
    keyring = app.state.keyring()
    assert [p["kid"] for p in link["pins"]["jwt"]] == [k["kid"] for k in keyring.jwks()["keys"]]
    assert link["pins"]["policy"][0]["jwk"]["x"] == keyring.policy_public_jwk()["x"]
    assert link["pins"]["keyset_fingerprint"] == grant["keyset_fingerprint"]
    # Publieke status: witte lijst, nooit het service-token
    status = c.get("/api/v1/status").json()
    assert status["gekoppeld"] is True and link["service_token"] not in json.dumps(status)
    # De Hub ziet de executor als actief en het token als gebruikt (bevestiging via services/self)
    item = next(s for s in admin.get("/api/v1/services").json()["items"] if s["app_id"] == "ai-server-manager-executor")
    assert item["status"] == "active" and item["tokens"][0]["eerst_gebruikt"]
    # Na de eerste koppeling geen formulier meer (§3.7/§3.9); een POST wordt geweigerd
    page = c.get("/")
    assert 'name="csrf"' not in page.text and "gaat via de Hub" in page.text
    again = c.post("/koppelen", data={"csrf": "x"}, headers={"Origin": "http://executor.test"})
    assert again.status_code == 403  # zonder geldige formuliercode
    # Inkomende JWT's: dienst-JWT van de Hub → 200; service-token → 401 service_token_not_accepted
    sid = link["service_id"]
    jwt_hub, _ = keyring.issue_hub_service_jwt(audience="ai-server-manager-executor", service_id=sid)
    r = c.get("/connector/v1/hub-link", headers={"Authorization": f"Bearer {jwt_hub}"})
    assert r.status_code == 200, r.text
    assert r.json()["pinned_kids"]["jwt"] == [k["kid"] for k in keyring.jwks()["keys"]]
    assert r.json()["rotation_sequence"] == 0 and "service_token" not in r.json()
    r = c.get("/connector/v1/hub-link", headers={"Authorization": f"Bearer {link['service_token']}"})
    assert r.status_code == 401 and r.json()["details"]["reason"] == "service_token_not_accepted"
    viewer, _ = keyring.issue_user_jwt(subject=str(uuid.uuid4()), audience="ai-server-manager-executor",
                                       roles=["viewer"], ttl_seconds=60)  # fmt: skip
    assert c.get("/connector/v1/hub-link", headers={"Authorization": f"Bearer {viewer}"}).status_code == 200
    kind, _ = keyring.issue_user_jwt(subject=str(uuid.uuid4()), audience="ai-server-manager-executor",
                                     roles=["kind"], ttl_seconds=60)  # fmt: skip
    assert c.get("/connector/v1/hub-link", headers={"Authorization": f"Bearer {kind}"}).status_code == 403
    import jwt as pyjwt

    claims = pyjwt.decode(jwt_hub, options={"verify_signature": False})
    unknown = pyjwt.encode(claims, keyring.jwt_signing, algorithm="EdDSA", headers={"kid": "onbekende-kid"})
    r = c.get("/connector/v1/hub-link", headers={"Authorization": f"Bearer {unknown}"})
    assert r.status_code == 401 and r.json()["details"]["reason"] == "unknown_key"  # + poll op de achtergrond
    wrong_aud, _ = keyring.issue_hub_service_jwt(audience="home-control-hub", service_id=sid)
    r = c.get("/connector/v1/hub-link", headers={"Authorization": f"Bearer {wrong_aud}"})
    assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token"
    # Ontkoppelen via de Hub: de executor weigert eerlijk (501, P2) → de Hub trekt niets in
    served_ex = Served(ex_app)
    try:
        from hub.routers import services as services_router

        monkeypatch.setattr(services_router, "service_base_url", lambda db, settings, s: (served_ex.url, None))
        r = admin.post(f"/api/v1/services/{sid}/unlink", headers=idem())
        assert r.status_code == 502 and r.json()["code"] == "unlink_refused" and r.json()["details"]["status"] == 501
    finally:
        served_ex.stop()
    item = next(s for s in admin.get("/api/v1/services").json()["items"] if s["app_id"] == "ai-server-manager-executor")
    assert item["status"] == "active"


def test_verkeerde_vingerafdruk_slaat_niets_op(admin: Any, hub: Served, executor: tuple[Any, Any]) -> None:
    ex_app, ex_settings = executor
    grant = _pairing(admin)
    c = _page_client(ex_app)
    r = _submit(c, hub.url, grant["koppelcode"], "MEGG-8GFG-2E4Y-K2RQ")  # testvector, niet de echte Hub
    assert r.status_code == 400 and "vingerafdruk klopt niet" in r.text
    link = json.loads((ex_settings.secrets_dir / "hub-link.json").read_text())
    assert link["state"] == "nooit_gekoppeld" and link["service_token"] is None and link["pins"] is None
    assert link["pending"] is None and link["last_error"]["code"] == "hub_vingerafdruk_onjuist"
    assert link["hub_url"] is None  # adres van een mislukte poging wordt nergens bewaard
    # Onbereikbare Hub → hub_onbereikbaar, niets opgeslagen; het formulier blijft beschikbaar
    r = _submit(c, "http://127.0.0.1:9", _pairing(admin)["koppelcode"], grant["keyset_fingerprint"])
    assert r.status_code == 400
    link = json.loads((ex_settings.secrets_dir / "hub-link.json").read_text())
    assert link["last_error"]["code"] == "hub_onbereikbaar" and link["state"] == "nooit_gekoppeld"
    # Dezelfde code opnieuw (binnen 60 min, zelfde sleutel, token nooit gebruikt) = toegestane herhaling (§3.6)
    r = _submit(c, hub.url, grant["koppelcode"], grant["keyset_fingerprint"])
    assert r.status_code == 200 and "Gekoppeld met de Hub" in r.text
    assert json.loads((ex_settings.secrets_dir / "hub-link.json").read_text())["confirmed_at"]
    audit = [a["actie"] for a in admin.get("/api/v1/audit").json()["items"]]
    assert "enrollment.replayed" in audit


def test_formulier_beveiliging_en_throttle(admin: Any, hub: Served, executor: tuple[Any, Any]) -> None:
    ex_app, ex_settings = executor
    c = _page_client(ex_app)
    fp = "MEGG-8GFG-2E4Y-K2RQ"
    # Origin ontbreekt of is vreemd → 403 (geen verzoek naar de Hub)
    assert _submit(c, hub.url, "ABCD-EFGH-JKMN", fp, origin="http://aanvaller.test").status_code == 403
    assert c.post("/koppelen", data={"csrf": "x"}).status_code == 403
    # `Origin: null` (andere oorsprong, sandbox of no-referrer) blijft geweigerd: nooit open bij twijfel.
    assert _submit(c, hub.url, "ABCD-EFGH-JKMN", fp, origin="null").status_code == 403
    # De pagina zelf zet same-origin, zodat een browser bij het eigen formulier de echte Origin meestuurt (N-01).
    assert c.get("/").headers["referrer-policy"] == "same-origin"
    # Ongeldige invoer → 422 zonder Hub-aanroep; loopback zonder ontwikkelvlag is in productie verboden
    assert _submit(c, "http://192.0.2.5:30400/pad", "ABCD-EFGH-JKMN", fp).status_code == 422
    assert _submit(c, hub.url, "ABCD-EFGH", fp).status_code == 422
    assert _submit(c, hub.url, "ABCD-EFGH-JKMN", "MEGG").status_code == 422
    # Throttle: 5 pogingen per bron-IP per 15 min (de vorige 3 telden mee) → daarna 429
    assert _submit(c, hub.url, "ABCD-EFGH-JKMN", fp).status_code == 400
    assert _submit(c, hub.url, "ABCD-EFGH-JKMP", fp).status_code == 400
    assert _submit(c, hub.url, "ABCD-EFGH-JKMQ", fp).status_code == 429
    assert json.loads((ex_settings.secrets_dir / "hub-link.json").read_text())["state"] == "nooit_gekoppeld"


def test_koppelen_na_eerste_koppeling_geweigerd_ook_met_geldige_formuliercode(
    admin: Any, app: Any, hub: Served, executor: tuple[Any, Any], clean_db: str
) -> None:
    """§3.7/§3.9: het koppelformulier bestaat alleen zolang de executor nooit gekoppeld is. Wie vóór de koppeling een
    geldige formuliercode (CSRF-cookie) ophaalde, kan daarna niet alsnog naar een andere Hub koppelen — ook niet na
    ontkoppelen of intrekken; de Hub krijgt dan geen enroll-verzoek."""
    import psycopg

    ex_app, ex_settings = executor
    late = _page_client(ex_app)
    m = re.search(r'name="csrf" value="([^"]+)"', late.get("/").text)
    assert m is not None
    stale_csrf = m.group(1)  # cookie + formuliercode van vóór de koppeling
    grant = _pairing(admin)
    assert _submit(_page_client(ex_app), hub.url, grant["koppelcode"], grant["keyset_fingerprint"]).status_code == 200
    second = _pairing(admin)
    with psycopg.connect(clean_db) as conn:
        before = conn.execute("SELECT count(*) FROM audit_event WHERE action LIKE 'enrollment.%'").fetchone()
    form = {"csrf": stale_csrf, "hub_url": hub.url, "koppelcode": second["koppelcode"],
            "vingerafdruk": second["keyset_fingerprint"]}  # fmt: skip
    r = late.post("/koppelen", data=form, headers={"Origin": "http://executor.test"})
    assert r.status_code == 409 and "al eens gekoppeld" in r.text
    with psycopg.connect(clean_db) as conn:
        after = conn.execute("SELECT count(*) FROM audit_event WHERE action LIKE 'enrollment.%'").fetchone()
    assert after == before  # geen verzoek naar de Hub
    link_file = ex_settings.secrets_dir / "hub-link.json"
    linked = json.loads(link_file.read_text())
    # Ook na intrekken (first_linked_at blijft staan) geen formulier en geen herkoppelen via de statuspagina.
    from executor.hublink import HubLinkStore

    with HubLinkStore(ex_settings.secrets_dir).update() as link:
        link.update(state="ingetrokken", service_token=None, last_error={"code": "ingetrokken_door_hub", "at": "x"})
    page = late.get("/")
    assert 'name="csrf"' not in page.text and "gaat via de Hub" in page.text
    r = late.post("/koppelen", data=form, headers={"Origin": "http://executor.test"})
    assert r.status_code == 409
    after_revoke = json.loads(link_file.read_text())
    assert after_revoke["first_linked_at"] == linked["first_linked_at"] and after_revoke["state"] == "ingetrokken"
    assert after_revoke["hub_url"] == linked["hub_url"] and after_revoke["pins"] == linked["pins"]


def test_verlopen_executor_koppelcode_wordt_geweigerd(
    admin: Any, hub: Served, executor: tuple[Any, Any], clean_db: str
) -> None:
    """§3.4: de koppelcode van de executor is 30 minuten geldig; daarna 401 invalid_enrollment en niets opgeslagen."""
    import psycopg

    ex_app, ex_settings = executor
    grant = _pairing(admin)
    with psycopg.connect(clean_db, autocommit=True) as conn:
        conn.execute("UPDATE enrollment_grant SET expires_at = now() - interval '1 second'")
    r = _submit(_page_client(ex_app), hub.url, grant["koppelcode"], grant["keyset_fingerprint"])
    assert r.status_code == 400 and "weigerde de koppelcode" in r.text
    link = json.loads((ex_settings.secrets_dir / "hub-link.json").read_text())
    assert link["state"] == "nooit_gekoppeld" and link["last_error"]["code"] == "hub_weigerde"
    assert link["service_token"] is None and link["first_linked_at"] is None
