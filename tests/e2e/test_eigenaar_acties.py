"""Dienst-E2E voor acties via de eigenaar-connector (contract 1.3 §6 en §8, tweede tabel; S-P2-080; Sim-getest).

De **echte** Hub-API stelt ``sso.sessions.revoke`` en ``sso.oidc.hub.register`` voor met het voorstel van de eigenaar
(``POST /connector/v1/propose``), laat goedkeuren, ondertekent het ``ExecutionRequest`` en stuurt het naar
``POST /connector/v1/apply`` van de eigenaar. De eigenaar is de fake :class:`fakes.fake_eigenaar.FakeEigenaar`
(testgegevens): die controleert zelf opnieuw en antwoordt daarna, zoals de echte eigenaar nu,
``501 capability_unavailable``. De echte proef met home-control-hub volgt in S-P2-340.
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from actiehelpers import HOST, Stack, bouw_stack, haal, keur_goed, schrijfaanroepen, stel_voor, voer_uit
from asm_policy import execreq
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
def keten(admin: Any, app: Any, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Keten]:
    from fastapi.testclient import TestClient

    from hub.actions.beleid import get_policy

    nas: FakeTrueNAS = write_nas().start()
    stack = bouw_stack(
        admin=admin, app=app, nas=nas, worker_once=worker_once, tmp_path=tmp_path, monkeypatch=monkeypatch
    )
    keys = app.state.keyring()
    eigenaar = FakeEigenaar(keys.jwt_signing.public_key(), keys.policy_signing.public_key(), get_policy()).start()
    tok = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": APP_ID}).json()["enrollment_token"]
    r = TestClient(app, base_url="https://testserver").post(
        "/api/v1/services/enroll", json=enroll_body(APP_ID, token=tok)
    )
    assert r.status_code == 200, r.text
    # In productie komen de adressen uit de inventaris (app.query + D03); hier zijn het de testservers.
    urls = {APP_ID: eigenaar.url, "ai-server-manager-executor": stack.ex_url}
    monkeypatch.setattr("hub.actions.service.service_base_url", lambda db, s, svc: (urls[svc.app_id], None))
    try:
        yield Keten(stack, eigenaar, r.json()["service_id"])
    finally:
        eigenaar.stop()
        stack.stop()
        nas.stop()


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
    assert v["preview_hash"] == "sha256:" + eigen["preview_hash"]
    assert v["resource_etag"] == "sha256:" + keten.eigenaar.etag
    assert v["preview"]["wijziging"]["voorstel_id"] == eigen["proposal_id"]
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
    assert verzoek["approval"]["preview_hash"] == v["preview_hash"]
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
