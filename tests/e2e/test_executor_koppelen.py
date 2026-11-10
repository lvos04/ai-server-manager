"""Dienst-E2E: executor koppelt met de **echte** Hub-API (contract 1.3 §3.3, §3.7, §3.9, §4.3–§4.7; Sim-getest).

Beide draaien als echte HTTP-server (uvicorn op 127.0.0.1): de executor roept de Hub aan met ``http.client`` en de Hub
roept de executor aan met een dienst-JWT. Getest: koppelcode + vingerafdruk via de statuspagina (CSRF, exacte Origin,
Sec-Fetch-Site, Host-beperking, elke POST een poging, koppelen bezig, onleesbaar koppelbestand, throttle), pinning in
``hub-link.json`` (0600), bevestiging met ``services/self``, formulier weg na de eerste koppeling, inkomende
JWT-controle met de vaste redenen, en ontkoppelen via de Hub dat de executor eerlijk weigert (501).
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

    return TestClient(app, base_url=BASE)


BASE = "http://executor.local"  # Host onder .local: toegestaan voor formulier-POST's (§3.7 punt 4)


def _submit(
    c: Any,
    hub_url: str,
    code: str,
    fingerprint: str,
    *,
    origin: str = BASE,
    extra: dict[str, str] | None = None,
) -> Any:
    page = c.get("/")
    m = re.search(r'name="csrf" value="([^"]+)"', page.text)
    csrf = m.group(1) if m else ""
    return c.post(
        "/koppelen",
        data={
            "csrf": csrf,
            "hub_adres": hub_url,
            "koppelcode": code,
            "hub_vingerafdruk": fingerprint,
        },
        headers={"Origin": origin, **(extra or {})},
    )


def _pairing(admin: Any) -> dict[str, Any]:
    r = admin.post("/api/v1/services/pairing-codes", json={"app_id": "ai-server-manager-executor"})
    assert r.status_code == 201, r.text
    return dict(r.json())


def test_executor_koppelt_met_koppelcode_en_vingerafdruk(
    admin: Any,
    app: Any,
    hub: Served,
    executor: tuple[Any, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ex_app, ex_settings = executor
    grant = _pairing(admin)
    c = _page_client(ex_app)
    assert "Koppelen met de Hub" in c.get("/").text
    r = _submit(
        c,
        hub.url,
        grant["koppelcode"].lower(),
        grant["keyset_fingerprint"].replace("-", " "),
    )
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
    again = c.post("/koppelen", data={"csrf": "x"}, headers={"Origin": BASE})
    assert again.status_code == 403  # zonder geldige formuliercode
    # Inkomende JWT's: dienst-JWT van de Hub → 200; service-token → 401 service_token_not_accepted
    sid = link["service_id"]
    jwt_hub, _ = keyring.issue_hub_service_jwt(audience="ai-server-manager-executor", service_id=sid)
    r = c.get("/connector/v1/hub-link", headers={"Authorization": f"Bearer {jwt_hub}"})
    assert r.status_code == 200, r.text
    assert r.json()["pinned_kids"]["jwt"] == [k["kid"] for k in keyring.jwks()["keys"]]
    assert r.json()["rotation_sequence"] == 0 and "service_token" not in r.json()
    r = c.get(
        "/connector/v1/hub-link",
        headers={"Authorization": f"Bearer {link['service_token']}"},
    )
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

        monkeypatch.setattr(
            services_router,
            "service_base_url",
            lambda db, settings, s: (served_ex.url, None),
        )
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
    r = _submit(
        c,
        "http://127.0.0.1:9",
        _pairing(admin)["koppelcode"],
        grant["keyset_fingerprint"],
    )
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
    assert (
        _submit(
            _page_client(ex_app),
            hub.url,
            grant["koppelcode"],
            grant["keyset_fingerprint"],
        ).status_code
        == 200
    )
    second = _pairing(admin)
    with psycopg.connect(clean_db) as conn:
        before = conn.execute("SELECT count(*) FROM audit_event WHERE action LIKE 'enrollment.%'").fetchone()
    form = {"csrf": stale_csrf, "hub_adres": hub.url, "koppelcode": second["koppelcode"],
            "hub_vingerafdruk": second["keyset_fingerprint"]}  # fmt: skip
    r = late.post("/koppelen", data=form, headers={"Origin": BASE})
    assert r.status_code == 409 and "al eens gekoppeld" in r.text
    with psycopg.connect(clean_db) as conn:
        after = conn.execute("SELECT count(*) FROM audit_event WHERE action LIKE 'enrollment.%'").fetchone()
    assert after == before  # geen verzoek naar de Hub
    link_file = ex_settings.secrets_dir / "hub-link.json"
    linked = json.loads(link_file.read_text())
    # Ook na intrekken (first_linked_at blijft staan) geen formulier en geen herkoppelen via de statuspagina.
    from executor.hublink import HubLinkStore

    with HubLinkStore(ex_settings.secrets_dir).update() as link:
        link.update(
            state="ingetrokken",
            service_token=None,
            last_error={"code": "ingetrokken_door_hub", "at": "x"},
        )
    page = late.get("/")
    assert 'name="csrf"' not in page.text and "gaat via de Hub" in page.text
    r = late.post("/koppelen", data=form, headers={"Origin": BASE})
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


def _enroll_count(clean_db: str) -> Any:
    import psycopg

    with psycopg.connect(clean_db) as conn:
        return conn.execute("SELECT count(*) FROM audit_event WHERE action LIKE 'enrollment.%'").fetchone()


def test_herkomst_en_host_beperking_negatieve_gevallen(
    admin: Any,
    hub: Served,
    executor: tuple[Any, Any],
    clean_db: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Contract 1.3 §3.7 punten 1–6: elk geweigerd verzoek → 403, gaat niet naar de Hub en telt niet als poging."""
    from fastapi.testclient import TestClient

    ex_app, ex_settings = executor
    grant = _pairing(admin)
    fp = grant["keyset_fingerprint"]
    c = _page_client(ex_app)
    before = _enroll_count(clean_db)
    caplog.set_level("INFO", logger="executor.koppelen")
    # Sec-Fetch-Site: same-site (andere app op hetzelfde NAS-adres) en cross-site → 403.
    for site in ("same-site", "cross-site"):
        r = _submit(c, hub.url, grant["koppelcode"], fp, extra={"Sec-Fetch-Site": site})
        assert r.status_code == 403 and "herkomst_onjuist" in r.text, site
    # Exacte Origin met het schema van dít verzoek: https bij een http-verzoek, of een andere poort → 403.
    assert _submit(c, hub.url, grant["koppelcode"], fp, origin="https://executor.local").status_code == 403
    assert _submit(c, hub.url, grant["koppelcode"], fp, origin="http://executor.local:1").status_code == 403
    # Geen formuliercookie → 403.
    page = c.get("/")
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)
    assert csrf is not None
    bare = _page_client(ex_app)
    r = bare.post("/koppelen", data={"csrf": csrf.group(1)}, headers={"Origin": BASE})
    assert r.status_code == 403 and "formuliercode_onjuist" in r.text
    # Host-beperking (DNS-rebinding): Origin = Host = een publieke naam → 403 host_niet_toegestaan.
    evil = TestClient(ex_app, base_url="http://rebind.example.com:30410")
    r = _submit(evil, hub.url, grant["koppelcode"], fp, origin="http://rebind.example.com:30410")
    assert r.status_code == 403 and "Open deze pagina via het IP-adres van de NAS, of koppel via de Hub" in r.text
    assert "host_niet_toegestaan" in r.text
    # Niets naar de Hub gestuurd, niets veranderd en geen poging geteld: daarna lukt koppelen gewoon.
    assert _enroll_count(clean_db) == before
    assert not (ex_settings.secrets_dir / "hub-link.json").exists()
    ok = _submit(c, hub.url, grant["koppelcode"], fp, extra={"Sec-Fetch-Site": "same-origin"})
    assert ok.status_code == 200 and "Gekoppeld met de Hub" in ok.text
    # Eén logregel per afgehandelde poging, met code en trace-ID; nooit het Hub-adres of de koppelcode.
    lines = [r.getMessage() for r in caplog.records if r.name == "executor.koppelen"]
    assert len(lines) == 7 and all("trace_id=" in line for line in lines)
    assert sum("code=host_niet_toegestaan" in line for line in lines) == 1 and "code=gekoppeld" in lines[-1]
    assert not any(hub.url in line or grant["koppelcode"] in line for line in lines)


def test_elke_post_telt_ook_bij_een_al_gekoppelde_executor(
    admin: Any, hub: Served, executor: tuple[Any, Any], clean_db: str
) -> None:
    """RV7: een POST op een al gekoppelde executor krijgt 409 al_gekoppeld, gaat niet naar de Hub en telt als poging."""
    ex_app, _ = executor
    late = _page_client(ex_app)
    m = re.search(r'name="csrf" value="([^"]+)"', late.get("/").text)
    assert m is not None
    grant = _pairing(admin)
    assert (
        _submit(
            _page_client(ex_app),
            hub.url,
            grant["koppelcode"],
            grant["keyset_fingerprint"],
        ).status_code
        == 200
    )
    before = _enroll_count(clean_db)
    form = {
        "csrf": m.group(1),
        "hub_adres": hub.url,
        "koppelcode": "ABCD-EFGH-JKMN",
        "hub_vingerafdruk": "x",
    }
    codes = [late.post("/koppelen", data=form, headers={"Origin": BASE}).status_code for _ in range(5)]
    assert codes == [
        409,
        409,
        409,
        409,
        429,
    ]  # de eerste geslaagde koppeling telde ook mee (5 per 15 min)
    assert _enroll_count(clean_db) == before


def test_koppelen_bezig_onleesbaar_en_invoer_niet_afkappen(
    admin: Any, hub: Served, executor: tuple[Any, Any], clean_db: str
) -> None:
    from executor.hublink import HubLinkStore, now_iso

    ex_app, ex_settings = executor
    grant = _pairing(admin)
    fp = grant["keyset_fingerprint"]
    c = _page_client(ex_app)
    before = _enroll_count(clean_db)
    # Invoer als geheel: een koppelcode van 33 tekens is te lang, ook als hij na normalisatie klopt (§3.7).
    r = _submit(c, hub.url, grant["koppelcode"] + " " * (33 - len(grant["koppelcode"])), fp)
    assert r.status_code == 422 and 'aria-invalid="true"' in r.text and 'id="koppelcode"' in r.text
    r = _submit(c, hub.url + "/" + "x" * 600, grant["koppelcode"], fp)
    assert r.status_code == 422 and "hooguit 512 tekens" in r.text
    # Koppelen bezig (pending ≠ null): 409 koppelen_bezig, niets naar de Hub, geen formulier op de pagina.
    store = HubLinkStore(ex_settings.secrets_dir)
    with store.update() as link:
        link["pending"] = {"kind": "koppelcode", "secret_sha256": "0" * 64, "hub_url": "x", "started_at": now_iso(),
                           "attempts": 1}  # fmt: skip
    m = re.search(r'name="csrf" value="([^"]+)"', _page_client(ex_app).get("/").text)
    assert m is None and "Koppelen bezig" in c.get("/").text
    r = c.post("/koppelen", data={"csrf": "x"}, headers={"Origin": BASE})
    assert r.status_code == 403  # zonder geldige formuliercode: eerst de herkomst
    cookie_client = _page_client(ex_app)
    with store.update() as link:
        link["pending"] = None
    m = re.search(r'name="csrf" value="([^"]+)"', cookie_client.get("/").text)
    assert m is not None
    with store.update() as link:
        link["pending"] = {"kind": "koppelcode", "secret_sha256": "0" * 64, "hub_url": "x", "started_at": now_iso(),
                           "attempts": 1}  # fmt: skip
    form = {
        "csrf": m.group(1),
        "hub_adres": hub.url,
        "koppelcode": grant["koppelcode"],
        "hub_vingerafdruk": fp,
    }
    r = cookie_client.post("/koppelen", data=form, headers={"Origin": BASE})
    assert r.status_code == 409 and "koppelen_bezig" in r.text
    # Onleesbaar koppelbestand: geen formulier; een POST uit een oud tabblad → 409 koppelstatus_onleesbaar.
    link_file = ex_settings.secrets_dir / "hub-link.json"
    link_file.write_text("{kapot")
    r = cookie_client.post("/koppelen", data=form, headers={"Origin": BASE})
    assert r.status_code == 409 and "koppelstatus_onleesbaar" in r.text and 'name="koppelcode"' not in r.text
    assert link_file.read_text() == "{kapot"  # nooit stil teruggezet
    assert cookie_client.get("/readyz").status_code == 200
    assert _enroll_count(clean_db) == before
