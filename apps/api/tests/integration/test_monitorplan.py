"""Monitorplan per app (C1.3-ASM-20, contract 1.3 §9): plan uit register + manifest, alleen handmatig bevestigen door
een beheerder, bevestiging gebonden aan de inhoud. De Hub maakt geen monitors aan in Uptime Kuma (Sim-getest; de
fake appstore is geen bewijs voor de echte appstore of Uptime Kuma)."""

from __future__ import annotations

import hashlib
import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from asm_policy.canonical import canonical_sha256
from conftest import idem, login_as, make_user
from fakes.fake_appstore import FakeAppstore
from sqlalchemy import select

from hub.monitoring import monitorplan
from hub.monitoring.monitorplan import uit_manifest

pytestmark = pytest.mark.integration

MANIFEST = {
    "app_id": "gotify",
    "healthcheck": {
        "type": "http",
        "port": "web",
        "monitor": {"pad": "/health", "verwachte_status": 200, "timeout_s": 5, "interval_s": 60},
    },
    "network": {"ports": [{"name": "web", "container_port": 80, "host_port": {"param": "p"}, "protocol": "tcp"}]},
}
SHA = canonical_sha256(MANIFEST)
PLAN = "/api/v1/monitoring/monitorplan"


def _bronblok(app: Any) -> dict[str, Any]:
    return monitorplan.gecontroleerd_manifest(MANIFEST, SHA, "gotify", app.state.keyring().identity)


def _app(app: Any, naam: str, appstore: dict[str, Any], host_poort: int = 30080) -> str:
    from hub.models import CatalogApp

    with app.state.sessionmaker() as db:
        row = CatalogApp(
            runtime_id=naam,
            naam=naam,
            app_id=naam,
            adaptertype="alleen_truenas",
            soort="derde",
            installatiewijze="custom_app",
            poorten=[{"container_poort": 80, "host_poort": host_poort, "host_ip": "0.0.0.0", "protocol": "tcp"}],
            appstore=appstore,
        )
        db.add(row)
        db.commit()
        return str(row.id)


def _poort(app: Any, app_id: str, host_poort: int) -> None:
    from hub.models import CatalogApp

    with app.state.sessionmaker() as db:
        row = db.get(CatalogApp, uuid.UUID(app_id))
        assert row is not None
        row.poorten = [{"container_poort": 80, "host_poort": host_poort, "host_ip": "0.0.0.0", "protocol": "tcp"}]
        db.commit()


def _d03(admin: Any) -> None:
    r = admin.put("/api/v1/decisions/D03/waarde", json={"waarde": {"nas_adres": "127.0.0.1", "https_poort": 443}},
                  headers=idem())  # fmt: skip
    assert r.status_code == 200, r.text


def _plan(client: Any) -> dict[str, dict[str, Any]]:
    r = client.get(PLAN)
    assert r.status_code == 200, r.text
    assert "geen monitors aan in Uptime Kuma" in r.json()["uitleg"]
    return {i["app"]["naam"]: i for i in r.json()["items"]}


def test_plan_bevestigen_en_inhoudsbinding(admin: Any, app: Any) -> None:
    gotify = _app(app, "gotify", {"status": "gekoppeld", "monitor": _bronblok(app)})
    zonder = _app(app, "zonder", {"status": "gekoppeld", "monitor": uit_manifest({"healthcheck": {}}, SHA)})
    _app(app, "vreemd", {"status": "niet_in_appstore"})
    _app(app, "vervalst", {"status": "gekoppeld", "monitor": {**uit_manifest(MANIFEST, SHA), "host_poort": "1"}})

    plan = _plan(admin)
    assert plan["gotify"]["stand"] == "onvolledig" and plan["gotify"]["reden"] == "nas_adres_onbekend"
    _d03(admin)
    plan = _plan(admin)
    g = plan["gotify"]
    assert g["stand"] == "voorgesteld" and g["bewaakt"] is False and g["bewaking"] == "niet bewaakt"
    assert g["controle"] == {
        "soort": "http",
        "adres": "http://127.0.0.1:30080/health",
        "verwachte_status": 200,
        "timeout_s": 5,
        "interval_s": 60,
    }
    # Negatief: zonder healthcheck.monitor een regel 'ontbreekt', nooit een stille 'gezond'.
    assert (plan["zonder"]["stand"], plan["zonder"]["reden"]) == ("ontbreekt", "monitor_ontbreekt")
    assert (plan["vreemd"]["stand"], plan["vreemd"]["reden"]) == ("ontbreekt", "niet_in_appstore")
    assert plan["vervalst"]["stand"] == "ontbreekt"  # opgeslagen blok buiten de witte lijst telt niet
    assert all(not r["bewaakt"] and r["controle"] is None for n, r in plan.items() if n != "gotify")

    sha = g["plan_sha256"]
    pad = f"{PLAN}/{gotify}/bevestiging"
    # Negatief: alleen een beheerder bevestigt; een operator mag het plan wel zien.
    make_user(admin, "op-mp", "operator")
    make_user(admin, "kijker-mp", "viewer")
    op = login_as(app, "op-mp")
    assert op.post(pad, json={"plan_sha256": sha, "bevestigd": True}, headers=idem()).status_code == 403
    assert _plan(op)["gotify"]["stand"] == "voorgesteld"
    assert login_as(app, "kijker-mp").get(PLAN).status_code == 403

    for fout in ({"plan_sha256": sha, "bevestigd": False}, {"plan_sha256": sha, "bevestigd": "true"},
                 {"plan_sha256": sha, "bevestigd": 1}, {"plan_sha256": sha}, {"plan_sha256": "x", "bevestigd": True},
                 {"plan_sha256": sha, "bevestigd": True, "notitie": "vrije tekst"}):  # fmt: skip
        assert admin.post(pad, json=fout, headers=idem()).status_code == 422, fout
    r = admin.post(pad, json={"plan_sha256": "sha256:" + "0" * 64, "bevestigd": True}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "plan_gewijzigd"
    r = admin.post(f"{PLAN}/{zonder}/bevestiging", json={"plan_sha256": sha, "bevestigd": True}, headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "plan_niet_bevestigbaar"
    assert admin.post(f"{PLAN}/{uuid.uuid4()}/bevestiging", json={"plan_sha256": sha, "bevestigd": True},
                      headers=idem()).status_code == 404  # fmt: skip

    sleutel = idem()
    r = admin.post(pad, json={"plan_sha256": sha, "bevestigd": True}, headers=sleutel)
    assert r.status_code == 201, r.text
    assert r.json()["stand"] == "handmatig bevestigd" and r.json()["bewaakt"] is True
    assert r.json()["bevestiging"]["door"] == "beheerder"
    # Zelfde sleutel, andere inhoud: zichtbaar conflict, geen tweede bevestiging.
    r2 = admin.post(pad, json={"plan_sha256": "sha256:" + "1" * 64, "bevestigd": True}, headers=sleutel)
    assert r2.status_code != 201
    assert _plan(admin)["gotify"]["stand"] == "handmatig bevestigd"

    from hub.models import AuditEvent

    with app.state.sessionmaker() as db:
        ev = db.scalars(select(AuditEvent).where(AuditEvent.action == "monitoring.monitorplan.bevestigd")).all()
    assert len(ev) == 1 and ev[0].target_id == gotify
    assert ev[0].details == {"app_id": gotify, "plan_sha256": sha, "soort_bewijs": "handmatig bevestigd"}

    # Een andere hostpoort is een ander plan: de oude bevestiging geldt niet meer en een vertraagde bevestiging van
    # het oude plan wordt geweigerd.
    _poort(app, gotify, 30081)
    g2 = _plan(admin)["gotify"]
    assert g2["stand"] == "voorgesteld" and g2["bewaakt"] is False and g2["bevestiging_verouderd"] is True
    r = admin.post(pad, json={"plan_sha256": sha, "bevestigd": True}, headers=idem())
    assert r.status_code == 409 and r.json()["details"]["plan_sha256"] == g2["plan_sha256"]
    # Terug naar de oude poort: alleen de laatste bevestiging telt, en die hoort bij dit plan.
    _poort(app, gotify, 30080)
    assert _plan(admin)["gotify"]["stand"] == "handmatig bevestigd"


def test_gezondheid_zonder_bevestigde_monitor_is_niet_gezond(
    app: Any, admin: Any, settings: Any, monkeypatch: Any
) -> None:
    """De gate in ``app_health``: een verder gezonde app telt zonder bevestigde monitor als onbekend (niet bewaakt)."""
    from hub.models import CatalogApp
    from hub.monitoring import appstatus

    gotify = _app(app, "gotify", {"status": "gekoppeld", "monitor": _bronblok(app)})
    _d03(admin)
    monkeypatch.setattr(appstatus, "evaluate", lambda *_a, **_k: {"status": "healthy", "reason_code": None})
    monkeypatch.setattr(appstatus, "truenas_component", lambda *_a: None)
    inv = {"identiteit_sinds": {}}
    with app.state.sessionmaker() as db:
        row = db.get(CatalogApp, uuid.UUID(gotify))
        h = appstatus.app_health(db, settings, row, inv)
    assert (h["status"], h["reason_code"], h["oorzaak"]) == ("unknown", "niet_bewaakt", "monitorplan")
    assert "niet als gezond" in h["melding"]
    sha = _plan(admin)["gotify"]["plan_sha256"]
    r = admin.post(f"{PLAN}/{gotify}/bevestiging", json={"plan_sha256": sha, "bevestigd": True}, headers=idem())
    assert r.status_code == 201, r.text
    with app.state.sessionmaker() as db:
        row = db.get(CatalogApp, uuid.UUID(gotify))
        assert appstatus.app_health(db, settings, row, inv)["status"] == "healthy"


def test_manifest_uit_de_appstore_alleen_met_nagerekende_hash(app: Any, settings: Any) -> None:
    from hub.catalog.appstore import fetch_monitor

    keyring = app.state.keyring()
    svc = SimpleNamespace(id=uuid.uuid4())
    store = FakeAppstore(keyring.jwt_signing.public_key(), service_id=str(svc.id)).start()
    try:
        vid = str(uuid.uuid4())
        versie = {"id": vid, "app_id": "gotify", "manifest_sha256": SHA, "manifest": MANIFEST}
        store.routes = {f"/catalog/v1/versions/{vid}": versie}
        entry = {"app_id": "gotify", "latest_version": {"id": vid, "manifest_sha256": SHA}}

        blok = fetch_monitor(store.url, keyring, svc, settings, entry, None)
        assert monitorplan.normaliseer(blok) == uit_manifest(MANIFEST, SHA) and blok["status"] == "ok"
        # Bewezen herkomst: geen nieuwe opvraag. Met een gewijzigde drempel moet de bron opnieuw worden gelezen.
        aantal = len(store.paths())
        assert fetch_monitor(store.url, keyring, svc, settings, entry, {"monitor": blok}) == blok
        assert len(store.paths()) == aantal
        gewijzigd = {**blok, "monitor": {**blok["monitor"], "interval_s": 61}}
        assert fetch_monitor(store.url, keyring, svc, settings, entry, {"monitor": gewijzigd}) == blok
        assert len(store.paths()) == aantal + 1

        for pad in ("/health?weergave=proeftekst", "/health#proeftekst"):
            hc = MANIFEST["healthcheck"]
            manifest = {**MANIFEST, "healthcheck": {**hc, "monitor": {**hc["monitor"], "pad": pad}}}
            sha = canonical_sha256(manifest)
            store.routes = {f"/catalog/v1/versions/{vid}": {**versie, "manifest": manifest, "manifest_sha256": sha}}
            bron = {**entry, "latest_version": {"id": vid, "manifest_sha256": sha}}
            assert fetch_monitor(store.url, keyring, svc, settings, bron, None) == {
                "status": "ongeldig",
                "reden": "monitor_ongeldig",
                "manifest_sha256": sha,
            }

        anders = {**MANIFEST, "healthcheck": {**MANIFEST["healthcheck"], "monitor": {"pad": "/x"}}}
        store.routes = {f"/catalog/v1/versions/{vid}": {**versie, "manifest": anders}}  # hash klopt niet meer
        assert fetch_monitor(store.url, keyring, svc, settings, entry, None) == {
            "status": "onbekend",
            "reden": "manifest_ongeldig",
        }
        store.routes = {f"/catalog/v1/versions/{vid}": {**versie, "app_id": "andere-app"}}
        assert fetch_monitor(store.url, keyring, svc, settings, entry, None)["reden"] == "manifest_ongeldig"
        andere_app = {**MANIFEST, "app_id": "andere-app"}
        andere_sha = canonical_sha256(andere_app)
        store.routes = {
            f"/catalog/v1/versions/{vid}": {**versie, "manifest": andere_app, "manifest_sha256": andere_sha}
        }
        andere_entry = {**entry, "latest_version": {"id": vid, "manifest_sha256": andere_sha}}
        assert fetch_monitor(store.url, keyring, svc, settings, andere_entry, None)["reden"] == "manifest_ongeldig"
        store.routes = {f"/catalog/v1/versions/{vid}": 404}
        assert fetch_monitor(store.url, keyring, svc, settings, entry, None)["reden"] == "manifest_ongeldig"
        geen_id = {"app_id": "gotify", "latest_version": {"manifest_sha256": SHA}}
        assert fetch_monitor(store.url, keyring, svc, settings, geen_id, None)["reden"] == "versie_onbekend"
        store.offline()
        assert fetch_monitor(store.url, keyring, svc, settings, entry, None)["reden"] == "manifest_onbereikbaar"
        assert (
            fetch_monitor(store.url, keyring, svc, settings, entry, {"monitor": gewijzigd})["reden"]
            == "manifest_onbereikbaar"
        )
    finally:
        store.stop()


def test_opgeslagen_monitor_moet_bij_het_manifest_en_de_app_horen(admin: Any, app: Any) -> None:
    from hub.models import CatalogApp

    _d03(admin)
    goed = _bronblok(app)
    bron = {"status": "gekoppeld", "app_id": "gotify", "manifest_sha256": SHA, "monitor": goed}
    ref = _app(app, "gotify", bron)
    sha = _plan(admin)["gotify"]["plan_sha256"]
    assert sha
    pad = f"{PLAN}/{ref}/bevestiging"
    body = {"bevestigd": True, "plan_sha256": sha}
    assert admin.post(pad, headers=idem(), json=body).status_code == 201
    for invoer in (
        {**bron, "monitor": {**goed, "monitor": {**goed["monitor"], "interval_s": 61}}},
        {**bron, "monitor": {**goed, "manifest_sha256": None}},
        {**bron, "monitor": {k: v for k, v in goed.items() if k != "bronbewijs"}},
        {**bron, "manifest_sha256": canonical_sha256({})},
        {k: v for k, v in bron.items() if k != "manifest_sha256"},
        {k: v for k, v in bron.items() if k != "app_id"},
        {**bron, "app_id": "andere-app"},
    ):
        with app.state.sessionmaker.begin() as db:
            db.get(CatalogApp, uuid.UUID(ref)).appstore = invoer
        regel = _plan(admin)["gotify"]
        assert (regel["stand"], regel["controle"], regel["plan_sha256"], regel["bewaakt"]) == (
            "ontbreekt",
            None,
            None,
            False,
        )
        assert admin.post(pad, headers=idem(), json=body).json()["code"] == "plan_niet_bevestigbaar"
    _app(app, "andere-app", {**bron, "app_id": "andere-app"})
    assert _plan(admin)["andere-app"]["stand"] == "ontbreekt"


@pytest.mark.parametrize("achtervoegsel", ["?weergave=proeftekst", "#proeftekst"])
def test_oud_monitoradres_in_appdetail_en_herhaalantwoord(admin: Any, app: Any, achtervoegsel: str) -> None:
    from hub import audit
    from hub.catalog.appstore import sync_appstore
    from hub.models import AuditEvent, CatalogApp, IdempotencyRecord

    _d03(admin)
    goed = _bronblok(app)
    bron = {"status": "gekoppeld", "app_id": "gotify", "manifest_sha256": SHA, "monitor": goed}
    ref = _app(app, "gotify", bron)
    sha = _plan(admin)["gotify"]["plan_sha256"]
    pad = f"{PLAN}/{ref}/bevestiging"
    body = {"bevestigd": True, "plan_sha256": sha}
    sleutel = idem()
    eerste = admin.post(pad, headers=sleutel, json=body)
    assert eerste.status_code == 201 and eerste.json()["controle"]
    assert admin.post(pad, headers=sleutel, json=body).json() == eerste.json()
    oud = {**goed["monitor"], "pad": goed["monitor"]["pad"] + achtervoegsel}
    vorige_bron = {**bron, "monitor": {**goed, "monitor": oud}}
    ontvangst_id = uuid.UUID(sleutel["Idempotency-Key"])
    with app.state.sessionmaker.begin() as db:
        rec = db.scalars(select(IdempotencyRecord).where(IdempotencyRecord.key == ontvangst_id)).one()
        controle = {**rec.response_body["controle"], "adres": rec.response_body["controle"]["adres"] + achtervoegsel}
        # Oude, intern consistente bevestiging: ook het oorspronkelijke verzoek hoort bij dit oude adres.
        oude_sha = canonical_sha256({"app": ref, "controle": controle})
        oud_verzoek = {**body, "plan_sha256": oude_sha}
        canoniek = json.dumps(oud_verzoek, sort_keys=True, separators=(",", ":"))
        rec.request_hash = hashlib.sha256(f"{pad}\n{canoniek}".encode()).hexdigest()
        rec.response_body = {
            **rec.response_body,
            "controle": controle,
            "plan_sha256": oude_sha,
            "bevestiging": {**rec.response_body["bevestiging"], "plan_sha256": oude_sha},
        }
        audit.record(
            db,
            actor_type="user",
            actor_id="test",
            action=monitorplan.BEVESTIGING_ACTIE,
            target_type="catalog_app",
            target_id=ref,
            details={"plan_sha256": oude_sha, "controle": controle},
        )

    make_user(admin, "kijker-monitor", "viewer")
    with login_as(app, "kijker-monitor") as kijker:
        for cache in (vorige_bron, {"status": "unknown", "laatst_bekend": vorige_bron}):
            with app.state.sessionmaker.begin() as db:
                db.get(CatalogApp, uuid.UUID(ref)).appstore = cache
            detail = kijker.get(f"/api/v1/apps/{ref}")
            assert detail.status_code == 200 and "proeftekst" not in detail.text
            assert _plan(admin)["gotify"]["stand"] == "ontbreekt"

    with app.state.sessionmaker.begin() as db:
        assert sync_appstore(db, app.state.settings, app.state.keyring())["status"] == "unknown"
        bewaard = db.get(CatalogApp, uuid.UUID(ref)).appstore["laatst_bekend"]["monitor"]
        assert bewaard == {"status": "ongeldig", "reden": "monitor_ongeldig"}
    herhaald = admin.post(pad, headers=sleutel, json=oud_verzoek)
    assert herhaald.status_code == 201 and herhaald.headers["Idempotent-Replay"] == "true"
    assert herhaald.json()["stand"] == "ontbreekt" and not herhaald.json()["bewaakt"]
    assert "proeftekst" not in herhaald.text
    with app.state.sessionmaker() as db:
        rec = db.scalars(select(IdempotencyRecord).where(IdempotencyRecord.key == ontvangst_id)).one()
        assert rec.response_body == herhaald.json()
        regels = db.scalars(select(AuditEvent).where(AuditEvent.action == monitorplan.BEVESTIGING_ACTIE)).all()
        assert len(regels) == 2
        assert audit.verify(db)["status"] == "intact"
    zichtbaar = admin.get("/api/v1/audit", params={"actie": monitorplan.BEVESTIGING_ACTIE})
    assert zichtbaar.status_code == 200 and "proeftekst" not in zichtbaar.text
    assert [r["details"] for r in zichtbaar.json()["items"]] == [
        {"app_id": ref, "plan_sha256": h, "soort_bewijs": "handmatig bevestigd"} for h in (oude_sha, sha)
    ]
