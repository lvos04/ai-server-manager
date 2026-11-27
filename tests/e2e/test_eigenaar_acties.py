"""Dienst-E2E voor acties via de eigenaar-connector (contract 1.3 §6 en §8, tweede tabel; S-P2-080; Sim-getest).

De **echte** Hub-API stelt ``sso.sessions.revoke`` en ``sso.oidc.hub.register`` voor met het voorstel van de eigenaar
(``POST /connector/v1/propose``), laat goedkeuren, ondertekent het ``ExecutionRequest`` en stuurt het naar
``POST /connector/v1/apply`` van de eigenaar. De eigenaar is de fake :class:`fakes.fake_eigenaar.FakeEigenaar`
(testgegevens): die controleert zelf opnieuw en antwoordt daarna, zoals de echte eigenaar nu,
``501 capability_unavailable``. De echte proef met home-control-hub volgt in S-P2-340.
"""

from __future__ import annotations

import copy
import hashlib
import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from actiehelpers import HOST, Stack, bouw_stack, haal, keur_goed, schrijfaanroepen, stel_voor, voer_uit
from asm_policy import execreq
from asm_policy.canonical import canonical_sha256
from conftest import enroll_body, idem
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from executorhelpers import write_nas
from fakes.fake_eigenaar import APP_ID, FakeEigenaar
from fakes.fake_http import Reply
from fakes.fake_truenas import FakeTrueNAS

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
DOEL = {"host_id": HOST, "app_id": APP_ID}
SESSIES = {"usernames": ["testgebruiker"], "all_users": False}


class Keten:
    def __init__(self, stack: Stack, eigenaar: FakeEigenaar, service_id: str) -> None:
        self.stack, self.eigenaar, self.service_id = stack, eigenaar, service_id

    def apply_paden(self) -> list[str]:
        return [p for p in self.eigenaar.paths() if p == "/connector/v1/apply"]

    def direct_apply(self, body: dict[str, Any]) -> httpx.Response:
        """Een verzoek rechtstreeks aan de eigenaar, met een geldige dienst-JWT van de Hub."""
        bearer, _ = self.stack.app.state.keyring().issue_hub_service_jwt(audience=APP_ID, service_id=self.service_id)
        return httpx.post(
            f"{self.eigenaar.url}/connector/v1/apply",
            json=body,
            headers={"Authorization": f"Bearer {bearer}", "Idempotency-Key": str(uuid.uuid4())},
        )


@pytest.fixture
def keten(
    admin: Any,
    app: Any,
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Keten]:
    from fastapi.testclient import TestClient

    from hub.actions.beleid import get_policy

    nas: FakeTrueNAS = write_nas().start()
    stack = bouw_stack(
        admin=admin,
        app=app,
        nas=nas,
        worker_once=worker_once,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    keys = app.state.keyring()
    tok = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": APP_ID}).json()["enrollment_token"]
    r = TestClient(app, base_url="https://testserver").post(
        "/api/v1/services/enroll", json=enroll_body(APP_ID, token=tok)
    )
    assert r.status_code == 200, r.text
    eigenaar = FakeEigenaar(
        keys.jwt_signing.public_key(),
        keys.policy_signing.public_key(),
        get_policy(),
        r.json()["service_id"],
    ).start()
    # In productie komen de adressen uit de inventaris (app.query + D03); hier zijn het de testservers.
    urls = {APP_ID: eigenaar.url, "ai-server-manager-executor": stack.ex_url}
    monkeypatch.setattr(
        "hub.actions.service.service_base_url",
        lambda db, s, svc: (urls[svc.app_id], None),
    )
    try:
        yield Keten(stack, eigenaar, r.json()["service_id"])
    finally:
        eigenaar.stop()
        stack.stop()
        nas.stop()


def _bewaarde_preview(keten: Keten, v: dict[str, Any]) -> Any:
    from hub.models import ActionRequest

    with keten.stack.app.state.sessionmaker() as db:
        return db.get(ActionRequest, uuid.UUID(v["request_id"])).preview  # type: ignore[union-attr]


def _voorstel(keten: Keten, action_id: str = "sso.sessions.revoke", **meer: Any) -> dict[str, Any]:
    r = stel_voor(keten.stack.admin, action_id, DOEL, SESSIES, **meer)
    assert r.status_code == 201, r.text
    return dict(r.json())


def test_intrekken_gaat_ondertekend_naar_de_eigenaar_die_zelf_controleert(keten: Keten) -> None:
    admin = keten.stack.admin
    v = _voorstel(keten, risk_claim="R0")
    # EX18: de claim telt niet; het beleid zegt R2 met goedkeuring. De goedkeuring bindt het voorstel van de eigenaar.
    assert v["risk_class"] == "R2" and v["status"] == "wacht_op_goedkeuring" and v["blokkades"] == [], v
    eigen = next(iter(keten.eigenaar.voorstellen.values()))
    # De goedkeuring bindt de hele getoonde preview (diff én de hash van de eigenaar), niet het vluchtige voorstel-ID.
    assert v["preview"]["wijziging"]["preview_hash_eigenaar"] == "sha256:" + eigen["preview_hash"]
    assert v["preview_hash"] == canonical_sha256(_bewaarde_preview(keten, v))
    assert v["resource_etag"] == "sha256:" + keten.eigenaar.etag
    assert "voorstel_id" not in v["preview"]["wijziging"]
    assert v["preview"]["wijziging"]["diff"] == eigen["diff"]
    assert voer_uit(admin, v).json()["code"] == "goedkeuring_nodig"
    assert keten.apply_paden() == []
    r = keur_goed(admin, v)
    assert r.status_code == 200 and r.json()["status"] == "goedgekeurd", r.text
    r = voer_uit(admin, v)
    # De eigenaar controleerde alles en heeft de SSO-uitvoering nog niet: eerlijk capability_unavailable.
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"]["eigenaar"]["code"] == "capability_unavailable"
    assert keten.apply_paden() == ["/connector/v1/apply"] and len(keten.eigenaar.geaccepteerd) == 1
    verzoek = keten.eigenaar.geaccepteerd[0]
    assert verzoek["approval"]["preview_hash"] == "sha256:" + eigen["preview_hash"]
    assert verzoek["proposal"]["expected_version"] == v["resource_etag"]
    assert haal(admin, v)["status"] == "mislukt"
    assert schrijfaanroepen(keten.stack.nas) == []  # de executor en TrueNAS kregen niets


def test_apply_zonder_geldige_handtekening_weigert_de_eigenaar(keten: Keten) -> None:
    v = _voorstel(keten)
    assert keur_goed(keten.stack.admin, v).status_code == 200
    assert voer_uit(keten.stack.admin, v).status_code == 501
    goed = keten.eigenaar.geaccepteerd[0]
    keys = keten.stack.app.state.keyring()

    def opnieuw(wijzig: Any, sleutel: Any = None) -> httpx.Response:
        body = copy.deepcopy(goed)
        body.pop("signature", None)
        wijzig(body)
        body["nonce"] = str(uuid.uuid4())
        return keten.direct_apply(execreq.sign(body, sleutel or keys.policy_signing))

    # Gewijzigd na het ondertekenen.
    vervalst = copy.deepcopy(goed)
    vervalst["proposal"]["parameters"] = {"usernames": [], "all_users": True}
    r = keten.direct_apply(vervalst)
    assert r.status_code == 403 and r.json()["code"] == "handtekening_ongeldig", r.text
    # Zonder handtekening.
    zonder = {k: w for k, w in goed.items() if k != "signature"}
    r = keten.direct_apply(zonder)
    assert r.status_code == 422 and r.json()["code"] == "execution_request_ongeldig", r.text
    # Ondertekend met een andere sleutel dan de gepinde policy-sleutel.
    r = opnieuw(lambda b: None, Ed25519PrivateKey.generate())
    assert r.status_code == 403 and r.json()["code"] == "handtekening_ongeldig", r.text
    # Geldig ondertekend, maar namens de AI: de eigenaar rekent zelf en weigert (de AI mag dit niet voorstellen).
    r = opnieuw(lambda b: b["proposal"].update(actor={"type": "ai", "id": "hub-ai"}))
    assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    # Geldig ondertekend, maar een MediaGuard-actie: gereserveerd tot BG-05.
    r = opnieuw(lambda b: b["proposal"].update(action_id="mediaguard.wanted.search"))
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert len(keten.eigenaar.geaccepteerd) == 1


def test_de_ai_kan_sso_registratie_niet_voorstellen(keten: Keten) -> None:
    for action_id in ("sso.oidc.hub.register", "sso.sessions.revoke"):
        r = stel_voor(keten.stack.admin, action_id, DOEL, SESSIES, actor={"type": "ai", "id": "hub-ai"})
        assert r.status_code == 422 and r.json()["code"] == "actor_past_niet", r.text
    assert keten.eigenaar.paths() == []
    from asm_policy.engine import classify

    from hub.actions.beleid import get_policy

    cls = classify(get_policy(), action_id="sso.oidc.hub.register", target=DOEL, parameters={}, actor_type="ai")
    assert cls.geweigerd


def test_registratie_vraagt_een_back_up_en_blijft_zonder_bewijs_geblokkeerd(keten: Keten) -> None:
    v = _voorstel(keten, "sso.oidc.hub.register")
    assert v["preview"]["requires_backup"] is True and v["preview"]["wijziging"]["requires_backup"] is True
    assert [b["code"] for b in v["blokkades"]] == ["backup_checkpoint_ontbreekt"], v
    r = keur_goed(keten.stack.admin, v)
    assert r.status_code == 409 and r.json()["code"] == "actie_geblokkeerd", r.text
    details = [d for b in r.json()["details"]["blokkades"] for d in b["details"]]
    assert "backupbewijs_eigenaar_ontbreekt" in details, r.text
    assert keten.apply_paden() == []


def test_eigenaar_zonder_apply_route_geeft_capability_unavailable(keten: Keten) -> None:
    keten.eigenaar.apply_route = False
    v = _voorstel(keten)
    assert keur_goed(keten.stack.admin, v).status_code == 200
    r = voer_uit(keten.stack.admin, v)
    assert r.status_code == 501 and r.json()["code"] == "capability_unavailable", r.text
    assert r.json()["details"]["http_status"] == 404
    assert haal(keten.stack.admin, v)["status"] == "mislukt"


def test_uitgevoerd_zonder_bewijs_is_geen_succes(keten: Keten) -> None:
    keten.eigenaar.apply_reply = Reply(200, {"status": "uitgevoerd"})
    v = _voorstel(keten)
    assert keur_goed(keten.stack.admin, v).status_code == 200
    r = voer_uit(keten.stack.admin, v)
    assert r.status_code == 502 and r.json()["code"] == "uitkomst_onbekend", r.text
    assert haal(keten.stack.admin, v)["status"] == "onbekend"
    # De eigenaar heeft geen journaal voor de Hub: ophelderen kan niet, er wordt niets herhaald.
    r = keten.stack.admin.post(f"/api/v1/actions/{v['request_id']}/reconcile", headers=idem())
    assert r.status_code == 409 and r.json()["details"]["journaal"] == "geen_journaal_eigenaar", r.text
    assert len(keten.apply_paden()) == 1


def test_gewijzigde_toestand_bij_de_eigenaar_laat_de_goedkeuring_vervallen(keten: Keten) -> None:
    v = _voorstel(keten)
    assert keur_goed(keten.stack.admin, v).status_code == 200
    keten.eigenaar.etag = "f" * 64
    r = voer_uit(keten.stack.admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_vervallen", r.text
    assert keten.apply_paden() == []


@pytest.mark.parametrize(
    ("antwoord", "status", "code"),
    [
        (Reply(404, {"detail": "Not Found"}), 501, "capability_unavailable"),
        (
            Reply(422, {"code": "parameters_ongeldig", "message": "Nee.", "details": {}}),
            409,
            "eigenaar_weigerde_voorstel",
        ),
        (Reply(201, {"proposal_id": "geen-uuid", "preview_hash": "x"}), 409, "doel_onbekend"),
        (Reply(503, {"code": "authentik_onbereikbaar"}), 409, "doel_onbekend"),
    ],
)
def test_onbruikbaar_voorstel_van_de_eigenaar_wordt_niets(
    keten: Keten, antwoord: Reply, status: int, code: str
) -> None:
    keten.eigenaar.propose_reply = antwoord
    r = stel_voor(keten.stack.admin, "sso.sessions.revoke", DOEL, SESSIES)
    assert r.status_code == status and r.json()["code"] == code, r.text


def test_eigenaar_niet_gekoppeld(keten: Keten) -> None:
    from sqlalchemy import update

    from hub.models import Service

    with keten.stack.app.state.sessionmaker() as db:
        db.execute(update(Service).where(Service.app_id == APP_ID).values(status="revoked"))
        db.commit()
    r = stel_voor(keten.stack.admin, "sso.sessions.revoke", DOEL, SESSIES)
    assert r.status_code == 409 and r.json()["code"] == "eigenaar_niet_gekoppeld", r.text
    assert keten.eigenaar.paths() == []


# ------------------------------------------------------------------ S-P2-080 herstel R-VEILIG-1 t/m -5
def _goedgekeurd(keten: Keten) -> dict[str, Any]:
    v = _voorstel(keten)
    assert keur_goed(keten.stack.admin, v).status_code == 200
    return v


def _ontvangst(v: dict[str, Any]) -> dict[str, Any]:
    """Een volledig 200-antwoord van de eigenaar op apply (§6: resultaat met readback + before/after-hash)."""
    return {
        "request_id": v["request_id"],
        "action_id": v["action_id"],
        "target": v["target"],
        "status": "uitgevoerd",
        "methode": v["action_id"],
        "before_hash": "sha256:" + "1" * 64,
        "after_hash": "sha256:" + "2" * 64,
        "policy_hash": v["policy_hash"],
        "uitgevoerd_op": "2026-11-22T10:00:00Z",
        "resource_etag": v["resource_etag"],
        "readback": {"ingetrokken_sessies": 0, "gelezen": True},
        "waarschuwingen": [],
    }


def _events(keten: Keten, soort: str, request_id: str) -> list[Any]:
    from sqlalchemy import select

    from hub.models import OutboxEvent

    with keten.stack.app.state.sessionmaker() as db:
        rijen = db.scalars(select(OutboxEvent).where(OutboxEvent.event_type == soort)).all()
        return [e for e in rijen if (e.payload or {}).get("request_id") == request_id]


@pytest.mark.parametrize("toestand", ["volledig", "zonder_readback", "readback_lijst", "ander_verzoek", "andere_actie"])
def test_uitgevoerd_alleen_met_readback_van_dit_verzoek(keten: Keten, toestand: str) -> None:
    """R-VEILIG-2: zonder bruikbare readback, of met bewijs van een ander verzoek, is de uitkomst onbekend."""
    v = _goedgekeurd(keten)
    antwoord = _ontvangst(v)
    if toestand == "zonder_readback":
        del antwoord["readback"]
    elif toestand == "readback_lijst":
        antwoord["readback"] = []
    elif toestand == "ander_verzoek":
        antwoord["request_id"] = str(uuid.uuid4())
    elif toestand == "andere_actie":
        antwoord["action_id"] = "sso.oidc.hub.register"
    keten.eigenaar.apply_reply = Reply(200, antwoord)
    r = voer_uit(keten.stack.admin, v)
    status = haal(keten.stack.admin, v)["status"]
    if toestand == "volledig":
        assert (r.status_code, status) == (200, "uitgevoerd"), r.text
        return
    assert (r.status_code, r.json()["code"], status) == (502, "uitkomst_onbekend", "onbekend"), r.text
    assert _events(keten, "action.run.succeeded", v["request_id"]) == []


@pytest.mark.parametrize("wijziging", ["diff", "preview_hash", "resource_etag"])
def test_goedkeuren_bindt_de_inhoud_van_het_getoonde_voorstel(keten: Keten, wijziging: str) -> None:
    """R-VEILIG-1: ook een andere diff onder dezelfde hash van de eigenaar geeft 409 en een nieuwe preview."""
    v = _voorstel(keten)
    tweede = copy.deepcopy(next(iter(keten.eigenaar.voorstellen.values())))
    if wijziging == "diff":
        tweede["diff"] = [{"operation": "ongewijzigd", "aantal": 0}]
    else:
        tweede[wijziging] = hashlib.sha256(wijziging.encode()).hexdigest()
    keten.eigenaar.propose_reply = Reply(201, tweede)
    r = keur_goed(keten.stack.admin, v)
    assert r.status_code == 409 and r.json()["code"] == "preview_gewijzigd", r.text
    nu = haal(keten.stack.admin, v)
    assert nu["goedkeuring"] is None and nu["preview_hash"] != v["preview_hash"]
    assert keten.apply_paden() == []


def test_andere_diff_na_goedkeuring_laat_de_goedkeuring_vervallen(keten: Keten) -> None:
    """R-VEILIG-1 bij uitvoeren: verandert de inhoud na de goedkeuring, dan vervalt die en gaat er niets naar apply."""
    v = _goedgekeurd(keten)
    tweede = copy.deepcopy(next(iter(keten.eigenaar.voorstellen.values())))
    tweede["diff"] = [{"operation": "alles_intrekken"}]
    keten.eigenaar.propose_reply = Reply(201, tweede)
    r = voer_uit(keten.stack.admin, v)
    assert r.status_code == 409 and r.json()["code"] == "goedkeuring_vervallen", r.text
    assert "preview_hash" in r.json()["details"]["gewijzigd"]
    assert keten.apply_paden() == []


@pytest.mark.parametrize(
    ("status", "body", "verwacht"),
    [
        (501, {"detail": "Not Implemented"}, (501, "capability_unavailable", "mislukt")),
        (504, {"code": "gateway_timeout"}, (502, "uitkomst_onbekend", "onbekend")),
        (503, {"code": "authentik_onbereikbaar"}, (502, "uitkomst_onbekend", "onbekend")),
        (500, {"code": "interne_fout"}, (502, "uitkomst_onbekend", "onbekend")),
        (409, {"code": "goedkeuring_past_niet"}, (409, "uitvoering_geweigerd", "mislukt")),
    ],
)
def test_alleen_een_expliciete_weigering_is_mislukt(
    keten: Keten, status: int, body: dict[str, Any], verwacht: tuple[int, str, str]
) -> None:
    """R-VEILIG-4 en -5: een onzekere 5xx is onbekend; een 501 zonder code is capability_unavailable."""
    v = _goedgekeurd(keten)
    keten.eigenaar.apply_reply = Reply(status, body)
    r = voer_uit(keten.stack.admin, v)
    assert (r.status_code, r.json()["code"], haal(keten.stack.admin, v)["status"]) == verwacht, r.text
    # Eenmalig: een tweede poging stuurt niets meer naar de eigenaar.
    assert voer_uit(keten.stack.admin, v).status_code == 409
    assert len(keten.apply_paden()) == 1


@pytest.mark.parametrize("soort", ["readback", "foutdetails"])
def test_geheimen_van_de_eigenaar_worden_gemaskeerd_voor_opslag(keten: Keten, soort: str) -> None:
    """R-VEILIG-3: een geneste client_secret uit readback of foutdetails staat nergens: antwoord, leesroute, opslag
    en een herhaling met dezelfde Idempotency-Key."""
    from hub.models import ActionRequest

    v = _goedgekeurd(keten)
    markering = uuid.uuid4().hex
    if soort == "readback":
        antwoord = _ontvangst(v)
        antwoord["readback"] = {
            "ingetrokken_sessies": 0,
            "gelezen": True,
            "client": {"client_secret": markering},
        }
        keten.eigenaar.apply_reply = Reply(200, antwoord)
    else:
        keten.eigenaar.apply_reply = Reply(
            409,
            {
                "code": "geweigerd",
                "details": {"fouten": [{"client_secret": markering}]},
            },
        )
    kop = idem()
    r = keten.stack.admin.post(f"/api/v1/actions/{v['request_id']}/execute", headers=kop)
    assert r.status_code == (200 if soort == "readback" else 409), r.text
    herhaling = keten.stack.admin.post(f"/api/v1/actions/{v['request_id']}/execute", headers=kop)
    assert herhaling.headers.get("Idempotent-Replay") == "true"
    with keten.stack.app.state.sessionmaker() as db:
        opslag = json.dumps(db.get(ActionRequest, uuid.UUID(v["request_id"])).resultaat)  # type: ignore[union-attr]
    gezien = {
        "antwoord": r.text,
        "herhaling": herhaling.text,
        "leesroute": json.dumps(haal(keten.stack.admin, v)),
        "opslag": opslag,
    }
    assert [k for k, tekst in gezien.items() if markering in tekst] == []
    assert "***" in opslag


# ------------------------------------------------------------------ S-P2-140b: automation.flows.restore (B11-005)
FLOWBRON = {**DOEL, "resource": "node_red"}
MOMENTOPNAME = {"snapshot_id": "0b1c2d3e-4f50-4617-8899-aabbccddeeff"}
EIGENAARSAANVRAGEN = [
    pytest.param("automation.flows.restore", FLOWBRON, MOMENTOPNAME, id="flow"),
    pytest.param("sso.sessions.revoke", DOEL, SESSIES, id="sessies"),
]


def _herstelbewijs(v: dict[str, Any]) -> dict[str, Any]:
    antwoord = _ontvangst(v)
    antwoord["readback"] = {
        **MOMENTOPNAME,
        "gelezen": True,
        "gelijk_aan_momentopname": True,
        "checksum_sha256": antwoord["after_hash"].removeprefix("sha256:"),
    }
    return antwoord


@pytest.mark.parametrize(("actie", "doel", "parameters"), EIGENAARSAANVRAGEN)
@pytest.mark.parametrize("veld", ["resource", "parameters", "andere_host", "host_null", "zonder_host", "standaardhost"])
def test_eigenaarsvoorstel_hoort_bij_de_aanvraag(
    keten: Keten, actie: str, doel: dict[str, str], parameters: dict[str, Any], veld: str
) -> None:
    antwoord = keten.eigenaar._propose({"action_id": actie, "target": dict(doel), "parameters": parameters}).body
    if veld == "resource":
        antwoord["target"]["resource"] = "andere_bron"
    elif veld == "parameters":
        # Ook een verschil in JSON-type telt: false is geen 0.
        antwoord["parameters"] = (
            {"snapshot_id": str(uuid.uuid4())}
            if actie == "automation.flows.restore"
            else {**parameters, "all_users": 0}
        )
    elif veld == "zonder_host":
        del antwoord["target"]["host_id"]
    elif veld == "standaardhost":
        doel = {k: v for k, v in doel.items() if k != "host_id"}
    else:
        antwoord["target"]["host_id"] = None if veld == "host_null" else "andere_host"
    keten.eigenaar.propose_reply = Reply(201, antwoord)
    r = stel_voor(keten.stack.admin, actie, doel, parameters)
    if veld in ("zonder_host", "standaardhost"):
        assert (r.status_code, r.json()["status"]) == (201, "wacht_op_goedkeuring")
    else:
        assert (r.status_code, r.json().get("code")) == (409, "doel_onbekend")
        assert "preview" not in r.json()
    assert not keten.apply_paden()


def _controleer_onbekende_uitkomst(keten: Keten, v: dict[str, Any]) -> None:
    admin = keten.stack.admin
    r = voer_uit(admin, v)
    bewaard = haal(admin, v)
    assert (r.status_code, r.json().get("code"), bewaard["status"]) == (502, "uitkomst_onbekend", "onbekend")
    assert bewaard["goedkeuring"]["gebruikt_op"] is not None
    assert not _events(keten, "action.run.succeeded", v["request_id"])
    assert voer_uit(admin, v).status_code == 409
    assert len(keten.apply_paden()) == 1 and not schrijfaanroepen(keten.stack.nas)


@pytest.mark.parametrize(("actie", "doel", "parameters"), EIGENAARSAANVRAGEN)
def test_onbevestigde_502_van_de_eigenaar(
    keten: Keten, actie: str, doel: dict[str, str], parameters: dict[str, Any]
) -> None:
    admin = keten.stack.admin
    v = stel_voor(admin, actie, doel, parameters).json()
    assert keur_goed(admin, v).status_code == 200
    keten.eigenaar.apply_reply = Reply(502, {"code": "uitvoering_mislukt"})
    _controleer_onbekende_uitkomst(keten, v)


@pytest.mark.parametrize(
    ("veld", "waarde"),
    [
        ("gelezen", False),
        ("gelezen", 1),
        ("gelijk_aan_momentopname", False),
        ("snapshot_id", None),
        ("snapshot_id", "00000000-0000-0000-0000-000000000001"),
        ("checksum_sha256", "a" * 64),
    ],
    ids=["ongelezen", "geen_boolean", "afwijkend", "snapshot_ontbreekt", "andere_snapshot", "andere_checksum"],
)
def test_flowherstel_vergt_bewijs_van_de_gevraagde_momentopname(keten: Keten, veld: str, waarde: Any) -> None:
    admin = keten.stack.admin
    v = stel_voor(admin, "automation.flows.restore", FLOWBRON, MOMENTOPNAME).json()
    assert keur_goed(admin, v).status_code == 200
    antwoord = _herstelbewijs(v)
    if waarde is None:
        del antwoord["readback"][veld]
    else:
        antwoord["readback"][veld] = waarde
    keten.eigenaar.apply_reply = Reply(200, antwoord)
    _controleer_onbekende_uitkomst(keten, v)


@pytest.mark.parametrize(
    "readback",
    [
        {},
        {"ingetrokken_sessies": 0},
        {"ingetrokken_sessies": False},
        {"ingetrokken_sessies": -1},
        {"ingetrokken_sessies": 0, "gelezen": False},
    ],
    ids=["leeg", "leesbewijs_ontbreekt", "boolean", "negatief", "ongelezen"],
)
def test_sessies_intrekken_vergt_een_teruggelezen_aantal(keten: Keten, readback: dict[str, Any]) -> None:
    v = _goedgekeurd(keten)
    keten.eigenaar.apply_reply = Reply(200, {**_ontvangst(v), "readback": readback})
    _controleer_onbekende_uitkomst(keten, v)


def test_flowherstel_voorstel_goedkeuring_ondertekend_verzoek_met_de_juiste_vorm(keten: Keten) -> None:
    """Positief: voorstel bij de eigenaar → menselijke goedkeuring (R2) → ondertekend ExecutionRequest naar
    ``/connector/v1/apply`` met precies het Hub-doel en ``{snapshot_id}``; uitgevoerd alleen met readback van dit
    verzoek."""
    admin = keten.stack.admin
    r = stel_voor(admin, "automation.flows.restore", FLOWBRON, MOMENTOPNAME, risk_claim="R0")
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["risk_class"] == "R2" and v["status"] == "wacht_op_goedkeuring" and v["blokkades"] == [], v
    assert v["preview"]["requires_backup"] is False
    assert voer_uit(admin, v).json()["code"] == "goedkeuring_nodig"
    assert keur_goed(admin, v).status_code == 200
    keten.eigenaar.apply_reply = Reply(200, _herstelbewijs(v))
    r = voer_uit(admin, v)
    assert r.status_code == 200 and haal(admin, v)["status"] == "uitgevoerd", r.text
    assert len(_events(keten, "action.run.succeeded", v["request_id"])) == 1
    [verzoek] = keten.eigenaar.geaccepteerd
    voorstel = verzoek["proposal"]
    assert (voorstel["action_id"], voorstel["target"], voorstel["parameters"]) == (
        "automation.flows.restore",
        FLOWBRON,
        MOMENTOPNAME,
    )
    assert voorstel["actor"]["type"] == "user" and verzoek["approval"]["risk_class"] == "R2"
    assert verzoek["approval"]["preview_hash"].startswith("sha256:") and verzoek["signature"]
    assert schrijfaanroepen(keten.stack.nas) == []


@pytest.mark.parametrize(
    ("target", "parameters"),
    [
        pytest.param(FLOWBRON, {**MOMENTOPNAME, "flows": []}, id="extra_parameter"),
        pytest.param(FLOWBRON, {"snapshot_id": "laatste"}, id="geen_uuid"),
        pytest.param(FLOWBRON, {}, id="zonder_snapshot_id"),
        pytest.param(DOEL, MOMENTOPNAME, id="zonder_flowbron"),
        pytest.param({**FLOWBRON, "app_id": "my-house"}, MOMENTOPNAME, id="andere_eigenaar"),
        pytest.param({"type": "source", "id": "node_red"}, MOMENTOPNAME, id="doelvorm_van_de_eigenaar"),
    ],
)
def test_flowherstel_met_ander_doel_of_andere_parameters_wordt_niets(
    keten: Keten, target: dict[str, Any], parameters: dict[str, Any]
) -> None:
    r = stel_voor(keten.stack.admin, "automation.flows.restore", target, parameters)
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert keten.eigenaar.paths() == []


def test_de_ai_kan_flowherstel_niet_voorstellen(keten: Keten) -> None:
    r = stel_voor(
        keten.stack.admin, "automation.flows.restore", FLOWBRON, MOMENTOPNAME, actor={"type": "ai", "id": "hub-ai"}
    )
    assert r.status_code == 422 and r.json()["code"] == "actor_past_niet", r.text
    assert keten.eigenaar.paths() == []


def test_flowherstel_ondertekend_met_andere_parameters_of_actor_weigert_de_eigenaar(
    keten: Keten,
) -> None:
    """Ook een geldig ondertekend verzoek met andere parameters, een flow of de AI als actor wordt bij apply
    geweigerd (de eigenaar rekent zelf met hetzelfde beleid)."""
    v = stel_voor(keten.stack.admin, "automation.flows.restore", FLOWBRON, MOMENTOPNAME).json()
    assert keur_goed(keten.stack.admin, v).status_code == 200
    assert voer_uit(keten.stack.admin, v).status_code == 501
    goed = keten.eigenaar.geaccepteerd[0]
    keys = keten.stack.app.state.keyring()

    def opnieuw(wijzig: Any) -> httpx.Response:
        body = copy.deepcopy(goed)
        body.pop("signature", None)
        wijzig(body)
        body["nonce"] = str(uuid.uuid4())
        return keten.direct_apply(execreq.sign(body, keys.policy_signing))

    ander = {"snapshot_id": str(uuid.uuid4())}
    assert opnieuw(lambda b: b["proposal"].update(parameters=ander)).status_code == 409
    assert keten.direct_apply(goed).status_code == 409
    r = opnieuw(lambda b: b["proposal"].update(parameters={**MOMENTOPNAME, "credentials": "x"}))
    assert r.status_code >= 400 and len(keten.eigenaar.geaccepteerd) == 1, r.text
    r = opnieuw(lambda b: b["proposal"].update(target={**FLOWBRON, "app_id": "my-house"}))
    assert r.status_code >= 400 and len(keten.eigenaar.geaccepteerd) == 1, r.text
    for actor in ({"type": "flow", "id": "flow-1"}, {"type": "ai", "id": "hub-ai"}):
        r = opnieuw(lambda b, a=actor: b["proposal"].update(actor=a))
        assert r.status_code == 403 and r.json()["code"] == "actie_geweigerd", r.text
    assert len(keten.eigenaar.geaccepteerd) == 1


def test_flowherstel_bevestigt_de_vooraf_getoonde_checksum(keten: Keten) -> None:
    admin = keten.stack.admin
    v = stel_voor(admin, "automation.flows.restore", FLOWBRON, MOMENTOPNAME).json()
    assert keur_goed(admin, v).status_code == 200
    antwoord = _herstelbewijs(v)
    antwoord["after_hash"] = "sha256:" + "3" * 64
    antwoord["readback"]["checksum_sha256"] = "3" * 64
    keten.eigenaar.apply_reply = Reply(200, antwoord)
    _controleer_onbekende_uitkomst(keten, v)


def test_simulator_weigert_tweede_gebruik_en_vreemde_dienst(keten: Keten) -> None:
    from fakes.fake_http import Seen

    ring = keten.stack.app.state.keyring()
    for sid, toegestaan in [(str(uuid.uuid4()), False), (keten.service_id, True)]:
        bearer, _ = ring.issue_hub_service_jwt(audience=APP_ID, service_id=sid)
        verzoek = Seen(
            "POST",
            "/connector/v1/propose",
            {},
            {"authorization": f"Bearer {bearer}"},
            b"{}",
        )
        assert keten.eigenaar._jwt(verzoek) is toegestaan
        assert not keten.eigenaar._jwt(verzoek)


def test_oidc_voorstel_met_andere_parameters_wordt_geweigerd(keten: Keten) -> None:
    actie = "sso.oidc.hub.register"
    eigen = keten.eigenaar._propose({"action_id": actie, "target": DOEL, "parameters": {}}).body
    eigen["parameters"] = {"andere_instantie": True}
    keten.eigenaar.propose_reply = Reply(201, eigen)
    antwoord = stel_voor(keten.stack.admin, actie, DOEL, {})
    assert (antwoord.status_code, antwoord.json()["code"]) == (409, "doel_onbekend")
    assert not keten.apply_paden()
