"""Dienst-E2E voor acties (contract 1.3 §8; B01-007, B01-003, B02-005/006; Sim-getest).

De **echte** Hub-API stelt voor, classificeert, laat goedkeuren, ondertekent en roept de **echte** executor-app aan;
die controleert zelf opnieuw en schrijft naar de fake TrueNAS. Geen echte NAS: alles hier is Sim-getest.
"""

from __future__ import annotations

import copy
import threading
import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from actiehelpers import (
    Served,
    Stack,
    app_target,
    audit_acties,
    bouw_stack,
    haal,
    hashes,
    keur_goed,
    schrijfaanroepen,
    stel_voor,
    voer_uit,
)
from conftest import idem, login_as, make_user
from executorhelpers import write_nas
from fakes.fake_truenas import FakeTrueNAS
from policyhelpers import DIGEST, DIGEST_B, install_params

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
REPO = "ghcr.io/voorbeeld/demo-app"
GEHEIM = "waarde-alleen-voor-de-app-417"


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def stack(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Stack]:
    s = bouw_stack(admin=admin, app=app, nas=nas, worker_once=worker_once, tmp_path=tmp_path, monkeypatch=monkeypatch)
    yield s
    s.stop()


def _codes(voorstel: dict[str, Any]) -> list[str]:
    return [b["code"] for b in voorstel["blokkades"]]


def _geblokkeerd(r: Any, code: str) -> None:
    assert r.status_code == 409 and r.json()["code"] == "actie_geblokkeerd", r.text
    assert code in [b["code"] for b in r.json()["details"]["blokkades"]], r.text


def _rij(app: Any, request_id: str) -> Any:
    from hub.models import ActionRequest

    with app.state.sessionmaker() as db:
        return db.get(ActionRequest, uuid.UUID(request_id))


# ---------------------------------------------------------------------- R1: zonder goedkeuring
def test_r1_herstart_zonder_goedkeuring_met_readback(stack: Stack) -> None:
    admin, nas = stack.admin, stack.nas
    r = stel_voor(admin, "app.restart", app_target("my-house"), risk_claim="R0")
    assert r.status_code == 201, r.text
    v = r.json()
    # EX18: de claim wordt bewaard en genegeerd; het beleid bepaalt R1.
    assert v["risk_class"] == "R1" and v["risk_claim"] == "R0" and v["risk_claim_genegeerd"] is True
    assert v["status"] == "klaar" and v["goedkeuring_nodig"] is False and v["blokkades"] == []
    assert v["preview"]["wijziging"] == {"soort": "restart", "app": "my-house", "verwacht": {"staat": "RUNNING"}}
    assert schrijfaanroepen(nas) == []  # een voorstel wijzigt niets
    # Goedkeuren van een R1-actie bestaat niet.
    r = keur_goed(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    r = voer_uit(admin, v)
    assert r.status_code == 200, r.text
    uit = r.json()
    assert uit["status"] == "uitgevoerd" and uit["resultaat"]["status"] == "uitgevoerd"
    assert uit["resultaat"]["before_hash"] and uit["resultaat"]["after_hash"]
    assert uit["resultaat"]["methode"] == "app.redeploy" and uit["goedkeuring"] is None
    assert schrijfaanroepen(nas) == ["app.redeploy"]
    assert haal(admin, v)["status"] == "uitgevoerd"
    acties = audit_acties(stack.app)
    for verwacht in ("action.proposal.created", "action.execution.started", "action.execution.succeeded"):
        assert verwacht in acties
    # Tweede keer uitvoeren kan niet: de status past niet meer en TrueNAS krijgt niets.
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    assert schrijfaanroepen(nas) == ["app.redeploy"]
    # Anti-flap: binnen de afkoeltijd wordt dezelfde app niet nog eens herstart, door wie ook.
    r = stel_voor(admin, "app.restart", app_target("my-house"))
    assert r.status_code == 201 and "cooldown" in _codes(r.json()), r.text
    _geblokkeerd(voer_uit(admin, r.json()), "cooldown")
    assert schrijfaanroepen(nas) == ["app.redeploy"]


def test_operator_voert_r1_uit_kijker_niet(stack: Stack) -> None:
    make_user(stack.admin, "oscar", "operator")
    make_user(stack.admin, "vera", "viewer")
    oscar, vera = login_as(stack.app, "oscar"), login_as(stack.app, "vera")
    assert stel_voor(vera, "app.stop", app_target("my-house")).status_code == 403
    r = stel_voor(oscar, "app.stop", app_target("my-house"))
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["actor"] == {"type": "user", "id": "oscar"} and v["risk_class"] == "R1"
    assert vera.get(f"/api/v1/actions/{v['request_id']}").status_code == 200  # lezen mag
    assert voer_uit(vera, v).status_code == 403
    r = voer_uit(oscar, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert stack.nas.app("my-house")["state"] == "STOPPED"
    # Een voorstel namens iemand anders bestaat niet.
    r = stel_voor(oscar, "app.start", app_target("my-house"), actor={"type": "user", "id": "beheerder"})
    assert r.status_code == 422 and r.json()["code"] == "actor_past_niet", r.text
    r = stel_voor(oscar, "app.start", app_target("my-house"), actor={"type": "ai", "id": "oscar"})
    assert r.status_code == 422 and r.json()["code"] == "actor_past_niet", r.text


def test_kritieke_app_is_r2_ook_als_de_aanvrager_r0_claimt(stack: Stack) -> None:
    nas = stack.nas
    kritiek = copy.deepcopy(nas.app("my-house"))
    kritiek["name"] = kritiek["id"] = "adguard-home"
    nas.data["app.query"].append(kritiek)
    r = stel_voor(stack.admin, "app.restart", app_target("adguard-home"), risk_claim="R0")
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["risk_class"] == "R2" and v["goedkeuring_nodig"] is True and v["status"] == "wacht_op_goedkeuring"
    assert v["preview"]["kritiek"] is True and v["risk_claim_genegeerd"] is True
    r = voer_uit(stack.admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_nodig", r.text
    assert schrijfaanroepen(nas) == []


# ---------------------------------------------------------------------- R2: installeren en verwijderen (B01-003)
def test_installeren_met_goedkeuring_en_verwijderen_zonder_dataverlies(stack: Stack) -> None:
    admin, nas = stack.admin, stack.nas
    make_user(admin, "oscar", "operator")
    oscar = login_as(stack.app, "oscar")
    envs = [{"name": "APP_MODE", "value": "prod"}, {"name": "PROEF_INSTELLING", "value": GEHEIM}]
    r = stel_voor(oscar, "app.install", app_target("demo-app"), install_params("demo-app", envs=envs))
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["risk_class"] == "R2" and v["status"] == "wacht_op_goedkeuring" and v["blokkades"] == []
    w = v["preview"]["wijziging"]
    assert w["installatiemethode"].startswith("standaard Custom App") and w["custom_compose"] is False
    assert w["image"]["digest"] == DIGEST if isinstance(w["image"], dict) else DIGEST in str(w["image"])
    assert w["omgevingsvariabelen"] == ["APP_MODE", "PROEF_INSTELLING"] and w["privileged"] is False
    assert "blijven staan" in v["preview"]["dataretentie"]
    # Waarden van omgevingsvariabelen staan nergens in het antwoord, de lijst of de audit.
    assert GEHEIM not in r.text and GEHEIM not in admin.get("/api/v1/actions").text
    assert GEHEIM not in admin.get("/api/v1/audit", params={"limit": 200}).text
    assert "one_time_nonce" not in r.text

    # Zonder goedkeuring gebeurt er niets; een operator kan niet goedkeuren.
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_nodig", r.text
    assert keur_goed(oscar, v).status_code == 403
    # Goedkeuren kan alleen voor precies de preview die de beheerder zag.
    r = keur_goed(admin, v, preview_hash="sha256:" + "0" * 64)
    assert r.status_code == 409 and r.json()["code"] == "preview_gewijzigd", r.text
    assert r.json()["details"]["gewijzigd"] == ["preview_hash"]
    assert haal(admin, v)["goedkeuring"] is None
    r = keur_goed(admin, v)
    assert r.status_code == 200, r.text
    g = r.json()["goedkeuring"]
    assert r.json()["status"] == "goedgekeurd" and g["approved_by"] == "beheerder" and g["gebruikt_op"] is None
    assert {k: g[k] for k in hashes(v)} == hashes(v) and "one_time_nonce" not in r.text
    from asm_policy.execreq import parse_ts

    assert timedelta(0) < parse_ts(g["expires_at"]) - parse_ts(g["approved_at"]) <= timedelta(minutes=15)
    assert schrijfaanroepen(nas) == []

    # R2 uitvoeren: alleen een beheerder.
    r = voer_uit(oscar, v)
    assert r.status_code == 403 and schrijfaanroepen(nas) == [], r.text
    r = voer_uit(admin, v)
    assert r.status_code == 200, r.text
    uit = r.json()
    assert uit["status"] == "uitgevoerd" and uit["resultaat"]["methode"] == "app.create"
    assert uit["goedkeuring"]["gebruikt_op"] and GEHEIM not in r.text
    # Precies een standaard Custom App (ix-app-waarden); nooit een compose-veld.
    assert len(nas.created) == 1
    body = nas.created[0]
    assert set(body) == {"app_name", "custom_app", "catalog_app", "train", "version", "values"}
    assert body["custom_app"] is False and body["catalog_app"] == "ix-app" and body["values"]["envs"] == envs
    assert "app.create(custom_compose)" not in nas.mutations and "compose" not in str(body)
    assert schrijfaanroepen(nas) == ["app.create"]
    # EX20: de goedkeuring is één keer bruikbaar.
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    assert schrijfaanroepen(nas) == ["app.create"]
    # Nog eens installeren over de bestaande app heen kan niet.
    r = stel_voor(admin, "app.install", app_target("demo-app"), install_params("demo-app"))
    assert r.status_code == 409 and r.json()["code"] == "doel_bestaat_al", r.text

    # Verwijderen = alleen de containers; datasets, snapshots en images blijven staan.
    datasets = sorted(nas.datasets())
    snapshots = copy.deepcopy(nas.data["snapshots"])
    r = stel_voor(admin, "app.uninstall", app_target("demo-app"))
    assert r.status_code == 201, r.text
    u = r.json()
    assert u["risk_class"] == "R2" and u["status"] == "wacht_op_goedkeuring"
    assert u["preview"]["wijziging"] == {
        "soort": "verwijderen",
        "app": "demo-app",
        "alleen_containers": True,
        "remove_ix_volumes": False,
        "remove_images": False,
    }
    assert keur_goed(admin, u).status_code == 200
    r = voer_uit(admin, u)
    assert r.status_code == 200 and r.json()["resultaat"]["methode"] == "app.delete", r.text
    assert nas.deleted == [("demo-app", {"remove_images": False, "remove_ix_volumes": False})]
    assert sorted(nas.datasets()) == datasets and nas.data["snapshots"] == snapshots
    assert schrijfaanroepen(nas) == ["app.create", "app.delete"]
    assert "pool.dataset.delete" not in nas.mutations


@pytest.mark.parametrize(
    ("wijziging", "plek"),
    [
        ({"custom_compose_config": {"services": {}}}, "app_create"),
        ({"custom_compose_config_string": "services: {}"}, "app_create"),
        ({"custom_app": True}, "app_create"),
        ({"privileged": True}, "values"),
        ({"host_network": True}, "values"),
        ({"image": {"repository": REPO, "tag": "latest"}}, "values"),
    ],
)
def test_compose_latest_en_gevaarlijke_waarden_worden_al_bij_het_voorstel_geweigerd(
    stack: Stack, wijziging: dict[str, Any], plek: str
) -> None:
    params = install_params("demo-app")
    doel = params["app_create"] if plek == "app_create" else params["app_create"]["values"]
    doel.update(wijziging)
    r = stel_voor(stack.admin, "app.install", app_target("demo-app"), params)
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert r.json()["details"]["fouten"]
    assert stack.admin.get("/api/v1/actions").json()["items"] == [] and schrijfaanroepen(stack.nas) == []


def test_kluisverwijzingen_bij_installeren_eerlijk_nog_niet_beschikbaar(stack: Stack) -> None:
    envs = [{"name": "API_SLEUTEL", "value": "vault://app/demo-app/api-sleutel"}]
    r = stel_voor(stack.admin, "app.install", app_target("demo-app"), install_params("demo-app", envs=envs))
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"]["reden"] == "vault_verwijzingen" and schrijfaanroepen(stack.nas) == []


def _tabellen_met(app: Any, waarde: str) -> list[str]:
    """Alle tabellen van de Hub-database waarin ``waarde`` ergens in een rij staat."""
    from sqlalchemy import text

    with app.state.sessionmaker() as db:
        tabellen = [str(r[0]) for r in db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))]
        return sorted(
            t
            for t in tabellen
            if db.execute(
                text(f'SELECT count(*) FROM "{t}" x WHERE x::text LIKE :w'),  # noqa: S608 - namen uit pg_tables
                {"w": f"%{waarde}%"},
            ).scalar()
        )


def test_installatiewaarden_blijven_na_afloop_niet_in_de_hub(stack: Stack) -> None:
    """ADR-0030 besluit 28: waarden van omgevingsvariabelen staan nooit in een preview, log of audit. Zolang een
    voorstel open is, bewaart de Hub ze (nodig voor het uitvoeren); na afloop (uitgevoerd, afgewezen, verlopen) staan
    ze nergens meer in de database van de Hub, en dus ook niet in zijn back-up. Alleen hun SHA-256 blijft."""
    from hub.models import ActionRequest
    from hub.timeutil import utcnow

    admin, nas = stack.admin, stack.nas
    geheim = {"uit": "waarde-uitgevoerd-5521", "af": "waarde-afgewezen-5522", "verl": "waarde-verlopen-5523"}

    def voorstel(app_id: str, waarde: str) -> dict[str, Any]:
        envs = [{"name": "APP_MODE", "value": "prod"}, {"name": "PROEF_WACHTWOORD", "value": waarde}]
        r = stel_voor(admin, "app.install", app_target(app_id), install_params(app_id, envs=envs))
        assert r.status_code == 201, r.text
        return dict(r.json())

    a = voorstel("demo-app", geheim["uit"])
    assert _tabellen_met(stack.app, geheim["uit"]) == ["action_request"]
    assert keur_goed(admin, a).status_code == 200
    r = voer_uit(admin, a)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert nas.created[0]["values"]["envs"][1] == {"name": "PROEF_WACHTWOORD", "value": geheim["uit"]}
    b = voorstel("demo-b", geheim["af"])
    r = admin.post(f"/api/v1/actions/{b['request_id']}/reject", json={"reden": "niet nu"}, headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "afgewezen", r.text
    c = voorstel("demo-c", geheim["verl"])
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(c["request_id"]))
        rij.geldig_tot = utcnow() - timedelta(seconds=1)
        db.commit()
    assert haal(admin, c)["status"] == "verlopen"
    for waarde in geheim.values():
        assert _tabellen_met(stack.app, waarde) == [], waarde
    # De hash van de parameters blijft gelijk (preview en audit verwijzen ernaar).
    for v in (a, b, c):
        assert haal(admin, v)["parameters_sha256"] == v["parameters_sha256"]
    assert schrijfaanroepen(nas) == ["app.create"]


# ---------------------------------------------------------------------- goedkeuring: gebonden, eenmalig, tijdelijk
def test_goedkeuring_vervalt_als_het_doel_na_de_goedkeuring_wijzigt(stack: Stack) -> None:
    """EX19: verandert er iets aan een gebonden veld, dan is er niets goedgekeurd."""
    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    assert keur_goed(admin, v).status_code == 200
    nas.app("my-house")["state"] = "STOPPED"  # iemand stopt de app buiten de Hub om
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_vervallen", r.text
    assert {"resource_etag", "preview_hash"} <= set(r.json()["details"]["gewijzigd"])
    assert schrijfaanroepen(nas) == []
    nu = haal(admin, v)
    assert nu["status"] == "wacht_op_goedkeuring" and nu["goedkeuring"]["vervallen_op"]
    assert nu["goedkeuring"]["vervallen_reden"].startswith("gewijzigd:")
    assert nu["resource_etag"] != v["resource_etag"] and nu["preview_hash"] != v["preview_hash"]
    assert "action.approval.lapsed" in audit_acties(stack.app)
    # De oude hashes goedkeuren kan niet meer; de nieuwe preview wel.
    r = keur_goed(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "preview_gewijzigd", r.text
    assert keur_goed(admin, nu).status_code == 200
    r = voer_uit(admin, nu)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert schrijfaanroepen(nas) == ["app.delete"]


def test_doel_wijzigt_tussen_voorstel_en_goedkeuring(stack: Stack) -> None:
    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    nas.app("my-house")["state"] = "STOPPED"
    r = keur_goed(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "preview_gewijzigd", r.text
    assert haal(admin, v)["goedkeuring"] is None and schrijfaanroepen(nas) == []
    # Een voorstel met een verouderde expected_version wordt niet eens aangenomen.
    r = stel_voor(admin, "app.stop", app_target("mediaguard"), expected_version="sha256:" + "0" * 64)
    assert r.status_code == 409 and r.json()["code"] == "doel_gewijzigd", r.text


def test_goedkeuring_is_eenmalig_ook_als_de_status_wordt_teruggezet(stack: Stack) -> None:
    """EX20: zelfs als de status van het verzoek (door een fout of ingreep) weer 'goedgekeurd' wordt, is de
    goedkeuring verbruikt."""
    from hub.models import ActionRequest

    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    assert keur_goed(admin, v).status_code == 200
    origineel = copy.deepcopy(nas.app("my-house"))
    r = voer_uit(admin, v)
    assert r.status_code == 200, r.text
    # De app staat er (buiten de Hub om) weer precies zo en de status wordt teruggezet: alles klopt weer, behalve
    # dat de goedkeuring al verbruikt is.
    nas.data["app.query"].append(origineel)
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(v["request_id"]))
        rij.status = "goedgekeurd"
        db.commit()
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_al_gebruikt", r.text
    assert schrijfaanroepen(nas) == ["app.delete"]


def test_tweede_goedkeuring_op_een_goedgekeurd_voorstel_wordt_geweigerd(stack: Stack) -> None:
    """Een goedgekeurd voorstel is niet nog eens goed te keuren: er blijft precies één goedkeuring. Na het uitvoeren
    zijn goedkeuren en uitvoeren allebei voorbij."""
    from sqlalchemy import select

    from hub.models import Approval

    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    assert keur_goed(admin, v).status_code == 200
    r = keur_goed(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    with stack.app.state.sessionmaker() as db:
        rijen = list(db.scalars(select(Approval).where(Approval.request_id == uuid.UUID(v["request_id"]))))
    assert len(rijen) == 1 and rijen[0].vervallen_op is None and rijen[0].used_at is None
    r = voer_uit(admin, v)
    assert r.status_code == 200, r.text
    for _ in range(2):
        r = keur_goed(admin, v)
        assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
        r = voer_uit(admin, v)
        assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    assert schrijfaanroepen(nas) == ["app.delete"]


def _naar_executor(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Telt de uitvoerverzoeken die de Hub echt naar de executor stuurt (``POST /api/v1/execute``)."""
    from hub import servicecalls

    echte = servicecalls.call
    gezien: list[str] = []

    def call(base_url: str, method: str, path: str, **kw: Any) -> Any:
        if method == "POST" and path == "/api/v1/execute":
            gezien.append(str((kw.get("body") or {}).get("proposal", {}).get("idempotency_key")))
        return echte(base_url, method, path, **kw)

    monkeypatch.setattr(servicecalls, "call", call)
    return gezien


def test_emby_wordt_ook_met_goedkeuring_nooit_aangeraakt(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    """Besluit van de gebruiker (Emby blijft tot hij het zelf verwijdert): een goedkeuring heft de Emby-regel niet op.
    Draait er na de goedkeuring Emby onder dezelfde naam, dan weigert de Hub bij het uitvoeren en gaat er niets naar
    de executor. Een voorstel dat meteen op Emby wijst, is daarna niet goed te keuren en niet uit te voeren."""
    admin, nas = stack.admin, stack.nas
    naar_executor = _naar_executor(monkeypatch)
    app = copy.deepcopy(nas.app("my-house"))
    app["name"] = app["id"] = "mediabak"
    nas.data["app.query"].append(app)
    v = stel_voor(admin, "app.uninstall", app_target("mediabak")).json()
    assert v["status"] == "wacht_op_goedkeuring" and v["blokkades"] == [], v
    assert keur_goed(admin, v).status_code == 200
    emby = "docker.io/emby/embyserver:4.9.1.80"
    app["active_workloads"]["images"] = [emby]
    for c in app["active_workloads"]["container_details"]:
        c["image"] = emby
    r = voer_uit(admin, v)
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    nu = haal(admin, v)
    assert nu["status"] == "geweigerd" and "emby_nooit_door_platform" in _codes(nu), nu
    assert nu["goedkeuring"]["vervallen_reden"] == "geweigerd" and nu["goedkeuring"]["gebruikt_op"] is None
    for _ in range(2):
        r = keur_goed(admin, v)
        assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
        r = voer_uit(admin, v)
        assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    # Meteen op Emby: geweigerd bij het voorstel, en geen weg om het toch goed te keuren of uit te voeren.
    key = str(uuid.uuid4())
    body = {"action_id": "app.uninstall", "target": app_target("mediabak"), "parameters": {}, "reason": "test"}
    r = admin.post("/api/v1/actions", json=body, headers={"Idempotency-Key": key})
    assert r.status_code == 403 and "emby_nooit_door_platform" in _codes(r.json()["details"]), r.text
    w = haal(admin, key)
    r = admin.post(
        f"/api/v1/actions/{key}/approve",
        json={"preview_hash": "sha256:" + "0" * 64, "resource_etag": "x", "policy_hash": w["policy_hash"]},
        headers=idem(),
    )
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    r = voer_uit(admin, key)
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    assert naar_executor == [] and schrijfaanroepen(nas) == []


# ---------------------------------------------------------------------- gestopte apps: dicht bij twijfel
EMBY_IMAGE = "docker.io/emby/embyserver:4.9.1.80"
GESTOPT = [
    pytest.param("mediaserver", EMBY_IMAGE, "emby", "emby_nooit_door_platform", id="catalogusapp-emby"),
    pytest.param("mediaserver", EMBY_IMAGE, "ix-app", "doel_niet_herkenbaar", id="custom-app-met-emby-image"),
    pytest.param(
        "media-guard", "ghcr.io/lvos04/mediaguard-core:1.2.2", "ix-app", "doel_niet_herkenbaar", id="mediaguard"
    ),
    pytest.param("jellyleon", "ghcr.io/lvos04/jelly-leon:10.11.0", "ix-app", "doel_niet_herkenbaar", id="jelly-leon"),
]
APP_ACTIES = [
    ("app.uninstall", {}),
    ("app.update", {"catalog_version": "1.4.15"}),
    ("app.rollback", {"catalog_version": "1.4.13"}),
    ("app.start", {}),
    ("app.restart", {}),
    ("app.stop", {}),
]


def _gestopte_app(nas: FakeTrueNAS, naam: str, image: str, catalogus: str) -> None:
    """Een gestopte app zoals TrueNAS hem toont: lege ``active_workloads``, dus geen image te zien."""
    from fakes.fake_truenas import _app, _image

    app = _app(naam, "STOPPED", image, 30500, 8096, f"/mnt/testpool/apps/{naam}", "/config", catalog_app=catalogus)
    assert app["active_workloads"]["images"] == []
    nas.data["app.query"].append(app)
    nas.data["app.image.query"].append(_image(image))


@pytest.mark.parametrize(("naam", "image", "catalogus", "code"), GESTOPT)
def test_gestopte_beschermde_app_onder_een_andere_naam_wordt_nooit_aangeraakt(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, naam: str, image: str, catalogus: str, code: str
) -> None:
    """HARDE EIS: TrueNAS toont bij een gestopte app geen image. Een gestopte Emby, MediaGuard of Jelly Leon onder een
    andere appnaam is dan alleen te herkennen aan de catalogusapp (``metadata.name``); lukt ook dat niet, dan kan het
    platform niet uitsluiten dat het een beschermde app is en weigert het elke actie op die app (dicht bij twijfel).
    Niets gaat naar de executor en TrueNAS krijgt geen enkele schrijfaanroep."""
    admin, nas = stack.admin, stack.nas
    naar_executor = _naar_executor(monkeypatch)
    _gestopte_app(nas, naam, image, catalogus)
    for action_id, params in APP_ACTIES:
        key = str(uuid.uuid4())
        body = {"action_id": action_id, "target": app_target(naam), "parameters": params, "reason": "test"}
        r = admin.post("/api/v1/actions", json=body, headers={"Idempotency-Key": key})
        assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", (action_id, r.text)
        assert code in _codes(r.json()["details"]), (action_id, r.text)
        assert haal(admin, key)["status"] == "geweigerd"
        r = voer_uit(admin, key)
        assert r.status_code == 409 and r.json()["code"] == "status_past_niet", (action_id, r.text)
    assert naar_executor == [] and schrijfaanroepen(nas) == []
    gestopt = nas.app(naam)
    assert gestopt is not None and gestopt["state"] == "STOPPED"


def test_gestopte_custom_app_kan_niet_via_het_platform_starten_een_catalogusapp_wel(stack: Stack) -> None:
    """Tegenproef bij de vorige test. Een Custom App die het platform zelf stopte, toont daarna geen image meer: wat
    erin draait is niet vast te stellen, dus starten via het platform wordt geweigerd. Een gestopte catalogusapp is
    te herkennen aan zijn catalogusnaam (hier ``jellyfin``) en start gewoon (R1)."""
    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.stop", app_target("my-house")).json()
    assert voer_uit(admin, v).status_code == 200 and nas.app("my-house")["state"] == "STOPPED"
    r = stel_voor(admin, "app.start", app_target("my-house"))
    assert r.status_code == 403 and "doel_niet_herkenbaar" in _codes(r.json()["details"]), r.text
    assert schrijfaanroepen(nas) == ["app.stop"]
    r = stel_voor(admin, "app.start", app_target("jellyfin"))
    assert r.status_code == 201 and r.json()["risk_class"] == "R1" and r.json()["blokkades"] == [], r.text
    r = voer_uit(admin, r.json())
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert nas.app("jellyfin")["state"] == "RUNNING" and schrijfaanroepen(nas) == ["app.stop", "app.start"]


def _gelijktijdig(eerste: Any, tweede: Any, moment: Any) -> tuple[Any, Any]:
    """Draai ``eerste()``. Precies vóór de flush waarop ``moment(session)`` waar is, start ``tweede()`` in een eigen
    draad (V-044). Is de tweede binnen 3 s klaar, dan was hij eerst; anders wacht hij op een vergrendeling van de
    eerste en loopt de eerste door. Zo is de volgorde bepaald, niet toevallig."""
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    uitslag: dict[str, Any] = {}
    draden: list[threading.Thread] = []

    def bij_flush(session: Any, _ctx: Any, _instances: Any) -> None:
        if draden or not moment(session):
            return
        t = threading.Thread(target=lambda: uitslag.__setitem__("tweede", tweede()), daemon=True)
        draden.append(t)
        t.start()
        t.join(timeout=3)

    event.listen(Session, "before_flush", bij_flush)
    try:
        r1 = eerste()
    finally:
        event.remove(Session, "before_flush", bij_flush)
    assert draden, "het moment voor de tweede aanroep is nooit bereikt"
    draden[0].join(timeout=60)
    assert not draden[0].is_alive() and "tweede" in uitslag
    return r1, uitslag["tweede"]


@pytest.mark.parametrize(("action_id", "methode"), [("app.restart", "app.redeploy"), ("app.uninstall", "app.delete")])
def test_gelijktijdig_uitvoeren_gaat_maar_een_keer_naar_de_executor(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, action_id: str, methode: str
) -> None:
    """V-044 en EX20: twee beheerders voeren tegelijk hetzelfde voorstel uit (R1 zonder, R2 met goedkeuring). Precies
    één uitvoering bereikt de executor; de andere krijgt een 409 van de Hub zelf."""
    from hub.models import ActionRequest

    admin, nas = stack.admin, stack.nas
    tweede = login_as(stack.app, "beheerder")
    v = stel_voor(admin, action_id, app_target("my-house")).json()
    if v["goedkeuring_nodig"]:
        assert keur_goed(admin, v).status_code == 200
    naar_executor = _naar_executor(monkeypatch)
    rid = v["request_id"]
    r1, r2 = _gelijktijdig(
        lambda: voer_uit(admin, v),
        lambda: voer_uit(tweede, v),
        lambda s: any(isinstance(o, ActionRequest) and str(o.id) == rid for o in s.dirty),
    )
    uitslagen = sorted([r1, r2], key=lambda r: r.status_code)
    assert [r.status_code for r in uitslagen] == [200, 409], [r1.text, r2.text]
    assert uitslagen[1].json()["code"] in ("goedkeuring_al_gebruikt", "status_past_niet"), uitslagen[1].text
    assert naar_executor == [rid] and schrijfaanroepen(nas) == [methode]
    assert haal(admin, v)["status"] == "uitgevoerd"


def test_afkoeltijd_geldt_ook_voor_twee_voorstellen_tegelijk(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    """V-044 voor de anti-flap: twee aparte voorstellen om dezelfde app te herstarten, tegelijk uitgevoerd. De
    afkoeltijd per (actie, doel) laat er precies één door; de andere is geblokkeerd en bereikt de executor niet."""
    from hub.models import ActionRequest

    admin, nas = stack.admin, stack.nas
    tweede = login_as(stack.app, "beheerder")
    a = stel_voor(admin, "app.restart", app_target("my-house")).json()
    b = stel_voor(admin, "app.restart", app_target("my-house")).json()
    assert a["status"] == b["status"] == "klaar" and a["blokkades"] == b["blokkades"] == []
    naar_executor = _naar_executor(monkeypatch)
    rid = a["request_id"]
    r1, r2 = _gelijktijdig(
        lambda: voer_uit(admin, a),
        lambda: voer_uit(tweede, b),
        lambda s: any(isinstance(o, ActionRequest) and str(o.id) == rid for o in s.dirty),
    )
    uitslagen = sorted([r1, r2], key=lambda r: r.status_code)
    assert [r.status_code for r in uitslagen] == [200, 409], [r1.text, r2.text]
    assert uitslagen[1].json()["code"] == "actie_geblokkeerd", uitslagen[1].text
    assert "cooldown" in [x["code"] for x in uitslagen[1].json()["details"]["blokkades"]], uitslagen[1].text
    assert len(naar_executor) == 1 and schrijfaanroepen(nas) == ["app.redeploy"]


def test_gelijktijdig_goedkeuren_geeft_een_goedkeuring(stack: Stack) -> None:
    """V-044: twee beheerders keuren tegelijk hetzelfde voorstel goed. Er komt precies één goedkeuring; de tweede
    krijgt 409, net als bij een tweede goedkeuring na elkaar."""
    from sqlalchemy import select

    from hub.models import Approval

    admin = stack.admin
    tweede = login_as(stack.app, "beheerder")
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    rid = v["request_id"]
    r1, r2 = _gelijktijdig(
        lambda: keur_goed(admin, v),
        lambda: keur_goed(tweede, v),
        lambda s: any(isinstance(o, Approval) and str(o.request_id) == rid for o in s.new),
    )
    uitslagen = sorted([r1, r2], key=lambda r: r.status_code)
    assert [r.status_code for r in uitslagen] == [200, 409], [r1.text, r2.text]
    assert uitslagen[1].json()["code"] == "status_past_niet", uitslagen[1].text
    with stack.app.state.sessionmaker() as db:
        rijen = list(db.scalars(select(Approval).where(Approval.request_id == uuid.UUID(rid))))
    assert len(rijen) == 1 and rijen[0].vervallen_op is None, [(a.vervallen_reden, a.used_at) for a in rijen]
    assert voer_uit(admin, v).status_code == 200 and schrijfaanroepen(stack.nas) == ["app.delete"]


def test_verlopen_goedkeuring_telt_niet(stack: Stack) -> None:
    from hub.models import Approval
    from hub.timeutil import utcnow

    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    assert keur_goed(admin, v).status_code == 200
    with stack.app.state.sessionmaker() as db:
        for ap in db.query(Approval).all():
            ap.approved_at = utcnow() - timedelta(minutes=16)
            ap.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_nodig", r.text
    nu = haal(admin, v)
    assert nu["status"] == "wacht_op_goedkeuring" and nu["goedkeuring"]["vervallen_reden"] == "verlopen"
    assert schrijfaanroepen(nas) == [] and "action.approval.expired" in audit_acties(stack.app)


def test_veeg_in_een_leesroute_schrijft_niet_over_een_uitvoering_heen(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ADR-0030 besluit 23: terwijl een uitvoering de rij van het verzoek vasthoudt, verloopt de goedkeuring en vraagt
    iemand de lijst op. De veeg in die leesroute wacht niet op de uitvoering en schrijft er niets overheen: een
    gebruikte goedkeuring is nooit ook "verlopen", en een verzoek verlaat "bezig" alleen via de uitvoerende
    transactie. (De goedkeuring is inmiddels verlopen; de eigen controle van de Hub stuurt dan niets naar de
    executor.)"""
    from sqlalchemy import select, update

    from hub.models import ActionRequest, Approval
    from hub.timeutil import utcnow

    admin, nas = stack.admin, stack.nas
    lezer = login_as(stack.app, "beheerder")
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    assert keur_goed(admin, v).status_code == 200
    naar_executor = _naar_executor(monkeypatch)
    rid = uuid.UUID(v["request_id"])

    def verlopen_en_lijst_lezen() -> Any:
        with stack.app.state.sessionmaker() as db:
            db.execute(
                update(Approval).where(Approval.request_id == rid).values(expires_at=utcnow() - timedelta(seconds=5))
            )
            db.commit()
        return lezer.get("/api/v1/actions")

    r1, r2 = _gelijktijdig(
        lambda: voer_uit(admin, v),
        verlopen_en_lijst_lezen,
        lambda s: any(isinstance(o, ActionRequest) and o.id == rid for o in s.dirty),
    )
    assert r2.status_code == 200, r2.text
    assert r1.status_code == 409 and r1.json()["code"] == "uitvoering_geweigerd", r1.text
    assert r1.json()["details"]["code"] == "goedkeuring_verlopen", r1.text
    with stack.app.state.sessionmaker() as db:
        rijen = list(db.scalars(select(Approval).where(Approval.request_id == rid)))
    assert len(rijen) == 1 and rijen[0].used_at is not None, rijen
    assert rijen[0].vervallen_op is None and rijen[0].vervallen_reden is None, (
        rijen[0].vervallen_op,
        rijen[0].vervallen_reden,
    )
    assert "action.approval.expired" not in audit_acties(stack.app)
    nu = haal(admin, v)
    assert nu["status"] == "mislukt" and nu["resultaat"]["code"] == "goedkeuring_verlopen", nu
    assert naar_executor == [] and schrijfaanroepen(nas) == []


def test_afwijzen_en_verlopen_voorstel(stack: Stack) -> None:
    from hub.models import ActionRequest
    from hub.timeutil import utcnow

    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    r = admin.post(f"/api/v1/actions/{v['request_id']}/reject", json={"reden": "niet nu"}, headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "afgewezen", r.text
    assert keur_goed(admin, v).status_code == 409 and voer_uit(admin, v).status_code == 409
    w = stel_voor(admin, "app.stop", app_target("my-house"), expires_in_seconds=60).json()
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(w["request_id"]))
        rij.geldig_tot = utcnow() - timedelta(seconds=1)
        db.commit()
    r = voer_uit(admin, w)
    assert r.status_code == 409 and r.json()["code"] == "voorstel_verlopen", r.text
    assert haal(admin, w)["status"] == "verlopen" and schrijfaanroepen(nas) == []
    items = admin.get("/api/v1/actions", params={"status": "open"}).json()["items"]
    assert items == []


# ---------------------------------------------------------------------- blokkades op de gemeten toestand
@pytest.mark.parametrize("toestand", ["DEGRADED", "FAULTED", "niet_healthy"])
def test_pool_niet_gezond_blokkeert_opslagmutaties_ook_met_goedkeuring(stack: Stack, toestand: str) -> None:
    """EX11."""
    admin, nas = stack.admin, stack.nas
    # Goedgekeurd terwijl de pool nog gezond was …
    v = stel_voor(admin, "app.install", app_target("demo-app"), install_params("demo-app")).json()
    assert v["blokkades"] == [] and keur_goed(admin, v).status_code == 200
    pool = nas.data["pool.query"][0]
    if toestand == "niet_healthy":
        pool["healthy"] = False
    else:
        pool["status"], pool["healthy"] = toestand, False
    stack.vernieuw()
    # … maar een blokkade geldt óók met goedkeuring.
    _geblokkeerd(voer_uit(admin, v), "pool_niet_gezond")
    snap = stel_voor(
        admin,
        "zfs.snapshot.create",
        {"host_id": "nas-primary", "dataset": "testpool/apps/mediaguard"},
        {"naam": "asm-proef"},
    )
    assert snap.status_code == 201 and "pool_niet_gezond" in _codes(snap.json()), snap.text
    _geblokkeerd(voer_uit(admin, snap.json()), "pool_niet_gezond")
    nieuw = stel_voor(admin, "app.install", app_target("andere-app"), install_params("andere-app")).json()
    assert "pool_niet_gezond" in _codes(nieuw)
    _geblokkeerd(keur_goed(admin, nieuw), "pool_niet_gezond")
    assert schrijfaanroepen(nas) == [] and nas.created == []
    # Geen opslagmutatie en R1: een app herstarten mag nog wel.
    r = voer_uit(admin, stel_voor(admin, "app.restart", app_target("my-house")).json())
    assert r.status_code == 200 and schrijfaanroepen(nas) == ["app.redeploy"], r.text


@pytest.mark.parametrize("backup", ["geen", "oud"])
def test_backup_gate_rood_blokkeert_opslagmutaties(stack: Stack, backup: str) -> None:
    """EX12."""
    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.install", app_target("demo-app"), install_params("demo-app")).json()
    assert keur_goed(admin, v).status_code == 200
    stack.toestand.backup = backup
    _geblokkeerd(voer_uit(admin, v), "backup_gate_rood")
    snap = stel_voor(
        admin,
        "zfs.snapshot.create",
        {"host_id": "nas-primary", "dataset": "testpool/apps/mediaguard"},
        {"naam": "asm-proef"},
    ).json()
    assert _codes(snap) == ["backup_gate_rood"]
    _geblokkeerd(voer_uit(admin, snap), "backup_gate_rood")
    assert schrijfaanroepen(nas) == []
    # Zodra de gate weer groen is, kan het (zelfde goedkeuring: er is niets aan de gebonden velden veranderd).
    stack.toestand.backup = "vers"
    r = voer_uit(admin, v)
    assert r.status_code == 200 and schrijfaanroepen(nas) == ["app.create"], r.text


def test_zonder_geteste_besluiten_geen_r2_en_geen_opslagmutatie(stack: Stack) -> None:
    """De echte toestand zonder testinvoer: besluiten Open, geen geverifieerde Hub-back-up."""
    admin, nas = stack.admin, stack.nas
    stack.toestand.besluiten, stack.toestand.backup = None, "echt"
    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    assert {"backup_gate_rood", "gate_dicht"} <= set(_codes(v))
    _geblokkeerd(keur_goed(admin, v), "backup_gate_rood")
    assert schrijfaanroepen(nas) == []


def test_bijwerken_vraagt_een_geverifieerd_herstelpunt(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    """``requires_backup``: zonder geverifieerd herstelpunt (B12) geen update. App-herstelpunten bestaan in deze
    versie nog niet; het tweede deel gebruikt een **gesimuleerd** herstelpunt om de binding te tonen."""
    from hub.actions import blokkades

    admin, nas = stack.admin, stack.nas
    assert voer_uit(admin, _installeer(stack)).status_code == 200
    nieuw = {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}}
    v = stel_voor(admin, "app.update", app_target("demo-app"), nieuw).json()
    assert v["risk_class"] == "R2" and _codes(v) == ["backup_checkpoint_ontbreekt"]
    _geblokkeerd(keur_goed(admin, v), "backup_checkpoint_ontbreekt")
    # Een herstelpunt dat de aanvrager zelf noemt, is geen bewijs: het veld bestaat niet eens in het voorstel.
    r = stel_voor(admin, "app.update", app_target("demo-app"), {**nieuw, "backup_checkpoint_id": str(uuid.uuid4())})
    assert r.status_code == 422, r.text

    punt = {"id": str(uuid.uuid4())}
    monkeypatch.setattr(blokkades, "verified_checkpoint", lambda db, req: punt["id"])
    v = haal(admin, v)
    r = keur_goed(admin, v)
    assert r.status_code == 200 and r.json()["goedkeuring"]["backup_checkpoint_id"] == punt["id"], r.text
    # Een ander herstelpunt dan bij de goedkeuring: de goedkeuring vervalt.
    eerste, punt["id"] = punt["id"], str(uuid.uuid4())
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_vervallen", r.text
    assert r.json()["details"]["gewijzigd"] == ["backup_checkpoint_id"]
    assert schrijfaanroepen(nas) == ["app.create"]
    punt["id"] = eerste
    v = haal(admin, v)
    assert keur_goed(admin, v).status_code == 200
    r = voer_uit(admin, v)
    assert r.status_code == 200 and r.json()["resultaat"]["methode"] == "app.update", r.text
    naam, opties = nas.updated[-1]
    assert naam == "demo-app" and set(opties) == {"values"} and set(opties["values"]) == {"image"}

    # Terugzetten = app.update met de vorige waarden die de executor bij die wijziging bewaarde.
    vorige = copy.deepcopy(nas.created[0]["values"])
    t = stel_voor(admin, "app.rollback", app_target("demo-app"), {"herstel_van": v["request_id"]}).json()
    assert t["preview"]["wijziging"]["soort"] == "terugzetten" and t["blokkades"] == []
    assert keur_goed(admin, t).status_code == 200
    r = voer_uit(admin, t)
    assert r.status_code == 200 and r.json()["resultaat"]["methode"] == "app.update", r.text
    assert nas.updated[-1] == ("demo-app", {"values": vorige})
    assert schrijfaanroepen(nas) == ["app.create", "app.update", "app.update"]
    assert "app.update(custom_compose)" not in nas.mutations


def _installeer(stack: Stack) -> dict[str, Any]:
    v = stel_voor(stack.admin, "app.install", app_target("demo-app"), install_params("demo-app")).json()
    assert keur_goed(stack.admin, v).status_code == 200
    return dict(v)


def test_noodstop_legt_alle_uitvoering_stil(stack: Stack) -> None:
    admin, nas = stack.admin, stack.nas
    make_user(admin, "oscar", "operator")
    oscar = login_as(stack.app, "oscar")
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = oscar.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "x"}, headers=idem())
    assert r.status_code == 403
    r = admin.put("/api/v1/actions/noodstop", json={"actief": True}, headers=idem())
    assert r.status_code == 422  # een reden is verplicht
    r = admin.put("/api/v1/actions/noodstop", json={"actief": True, "reden": "onderhoud aan de NAS"}, headers=idem())
    assert r.status_code == 200 and r.json()["actief"] is True and r.json()["door"] == "beheerder", r.text
    _geblokkeerd(voer_uit(admin, v), "noodstop_actief")
    assert schrijfaanroepen(nas) == []
    assert admin.get("/api/v1/actions").json()["noodstop"]["actief"] is True
    r = admin.put("/api/v1/actions/noodstop", json={"actief": False}, headers=idem())
    assert r.status_code == 200 and r.json()["actief"] is False
    assert voer_uit(admin, v).status_code == 200 and schrijfaanroepen(nas) == ["app.redeploy"]
    acties = audit_acties(stack.app)
    assert "action.emergency_stop.enabled" in acties and "action.emergency_stop.disabled" in acties


# ---------------------------------------------------------------------- afwijking, onbekende uitkomst
def test_afwijking_stopt_alles_en_wordt_een_incident(stack: Stack, periodic_run: Any) -> None:
    admin, nas = stack.admin, stack.nas
    nas.silent_noop.add("app.stop")  # TrueNAS meldt succes, maar de app draait nog
    v = stel_voor(admin, "app.stop", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    nu = haal(admin, v)
    assert nu["status"] == "afwijking" and nu["resultaat"]["reden"] == "staat_verschilt"
    assert "action.execution.deviated" in audit_acties(stack.app)
    periodic_run("incidenten_bijwerken")
    incidenten = admin.get("/api/v1/incidents").json()["items"]
    afw = [i for i in incidenten if i["soort"] == "actie.afwijking"]
    assert len(afw) == 1 and afw[0]["ernst"] == "kritiek", incidenten
    # De executor voert daarna niets meer uit tot een beheerder hem vrijgeeft; de Hub meldt dat eerlijk.
    w = stel_voor(admin, "app.restart", app_target("mediaguard")).json()
    r = voer_uit(admin, w)
    assert r.status_code == 409 and r.json()["code"] == "uitvoering_geweigerd", r.text
    assert r.json()["details"]["executor"]["code"] == "executor_gestopt"
    assert haal(admin, w)["status"] == "mislukt"
    assert schrijfaanroepen(nas) == ["app.stop"]


def test_executor_onbereikbaar_uitkomst_onbekend_en_ophelderen(stack: Stack, periodic_run: Any) -> None:
    from hub.models import ActionRequest

    admin, nas = stack.admin, stack.nas
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    stack.servers.pop().stop()  # de executor is weg
    r = voer_uit(admin, v)
    assert r.status_code == 502 and r.json()["code"] == "uitkomst_onbekend", r.text
    assert haal(admin, v)["status"] == "onbekend" and schrijfaanroepen(nas) == []
    # Onbekend is geen succes en geen mislukking; niets wordt blind herhaald.
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text
    periodic_run("incidenten_bijwerken")
    soorten = [i["soort"] for i in admin.get("/api/v1/incidents").json()["items"]]
    assert "actie.uitkomst_onbekend" in soorten
    r = admin.post(f"/api/v1/actions/{v['request_id']}/reconcile", headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "uitkomst_onbekend", r.text

    # De executor is terug en kent het verzoek niet. Zolang het verzoek nog geldig kan zijn: onbekend.
    from executor.app import create_app

    terug = Served(create_app(stack.ex_settings))
    stack.servers.append(terug)
    stack.ex_url = terug.url
    r = admin.post(f"/api/v1/actions/{v['request_id']}/reconcile", headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "uitkomst_onbekend", r.text
    # Na de geldigheid van het ondertekende verzoek kan het niet meer worden uitgevoerd: aantoonbaar niet gebeurd.
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(v["request_id"]))
        rij.gestart_op = rij.gestart_op - timedelta(minutes=10)
        db.commit()
    r = admin.post(f"/api/v1/actions/{v['request_id']}/reconcile", headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "mislukt", r.text
    assert r.json()["resultaat"]["code"] == "niet_uitgevoerd" and schrijfaanroepen(nas) == []
    periodic_run("incidenten_bijwerken")
    open_ = [i for i in admin.get("/api/v1/incidents").json()["items"] if i["soort"] == "actie.uitkomst_onbekend"]
    assert all(i["status"] == "opgelost" for i in open_), open_


def test_truenas_weigert_de_schrijfactie_mislukt_zonder_afwijking(stack: Stack) -> None:
    admin, nas = stack.admin, stack.nas
    nas.fail["app.redeploy"] = "proef: redeploy mislukt"
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == 502 and r.json()["code"] == "uitvoering_mislukt", r.text
    assert haal(admin, v)["status"] == "mislukt"
    assert "action.execution.failed" in audit_acties(stack.app)


def test_executor_zonder_schrijfsleutel_voert_niets_uit(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = bouw_stack(
        admin=admin,
        app=app,
        nas=nas,
        worker_once=worker_once,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        schrijfsleutel=False,
    )
    try:
        v = stel_voor(admin, "app.restart", app_target("my-house")).json()
        r = voer_uit(admin, v)
        assert r.status_code in (409, 501), r.text
        assert r.json()["code"] in ("uitvoering_geweigerd", "capability_unavailable"), r.text
        assert haal(admin, v)["status"] == "mislukt" and schrijfaanroepen(nas) == []
    finally:
        s.stop()
