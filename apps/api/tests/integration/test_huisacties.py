"""Bewaakt schrijfpad via de gekoppelde Hub, met een verifiërende eigenaar als simulator."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from actiehelpers import ALLE_BESLUITEN, haal, keur_goed, voer_uit
from asm_policy import execreq
from asm_policy.canonical import canonical_sha256
from backupfixtures import groene_appmetingen
from conftest import idem
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hub import outbound
from hub.actions import blokkades, huis, service
from hub.onboarding.gates import GateInputs
from hub.timeutil import utcnow

from .test_adapterkoppelingen import ROUTE, invoer
from .test_adapterkoppelingen import doel as doel
from .test_adapterkoppelingen import huis_simulatie as huis_simulatie

pytestmark = [pytest.mark.integration, pytest.mark.parametrize("doel", ["my_house"], indirect=True)]


def antwoord(status, body):
    return outbound.Response(status, json.dumps(body).encode())


class Eigenaar:
    """Alleen de vaste connectorpaden. Een opdracht telt pas na controle van de gepinde sleutel en de goedkeuring."""

    def __init__(self, pub):
        self.pub = pub
        self.nonces = set()
        self.paden = []
        self.aantal = 0
        self.vorige = None
        self.bewijs = {}
        self.verboden = False
        self.zone_id = str(uuid.uuid4())
        self.voor = {"power": True, "mode": "heat", "target_c": 20, "controls": {"TemUn": 0}}
        self.vernietig_bewijs = False

    def verzoek(self, method, path, opties):
        self.paden.append((method, path))
        if path == "discover":
            assert method == "GET"
            aid = opties["query"]["action_id"]
            veld = huis.HUIS_DOELVELDEN[aid]
            target = {veld: opties["query"]["target_id"]}
            if self.verboden:
                return antwoord(409, {"code": "policy_denied"})
            props = {
                "light.group.set": {"on": {"type": "boolean"}},
                "light.scene.recall": {},
                "zone.resume": {},
                huis.CONCEPT: {"blocks": {"type": "array"}},
                "zone.command": {"target_c": {"type": "integer", "minimum": 16, "maximum": 30}},
            }[aid]
            schema = {
                "type": "object",
                "additionalProperties": False,
                "properties": props,
                "required": list(props),
                "x-max-canonical-bytes": 16_384,
            }
            return antwoord(
                200,
                {
                    "checked_target": target,
                    "actions": [{"action_id": aid, "target_field": veld, "params_schema": schema}],
                },
            )
        if path.startswith("evidence/"):
            assert method == "GET" and path == "evidence/" + self.bewijs["id"]
            bewijs = dict(self.bewijs)
            if self.vernietig_bewijs:
                bewijs["after_hash"] = canonical_sha256({})
            return antwoord(200, bewijs)
        assert method == "POST"
        env = opties["json_body"]
        if self.pub is None:
            return antwoord(501, {"code": "capability_unavailable", "details": {"reason": "hub_keyset_missing"}})
        if not execreq.verify_signature(env, [self.pub]):
            return antwoord(403, {"code": "forbidden"})
        assert not execreq.structure_errors(env)
        assert execreq.parse_ts(env["issued_at"]) <= utcnow() < execreq.parse_ts(env["expires_at"])
        assert env["nonce"] == opties["headers"]["Idempotency-Key"] and env["nonce"] not in self.nonces
        self.nonces.add(env["nonce"])
        prop = env["proposal"]
        aid, target, params = prop["action_id"], prop["target"], prop["parameters"]
        assert target == {huis.HUIS_DOELVELDEN[aid]: self.zone_id}
        assert env["policy_decision"]["risk_class"] == ("R1" if aid.startswith("light.") else "R2")
        if path == "propose":
            assert env["approval"] is None and self.vorige is None
            self.vorige = prop
            if aid in ("light.group.set", "light.scene.recall", "zone.resume"):
                return antwoord(200, {"status": "unavailable", "reason_code": "capability_unavailable"})
            concept = aid == huis.CONCEPT
            before = {"schedule": []} if concept else self.voor
            etag = canonical_sha256(before)
            inhoud = {
                "direction": "apply",
                "action_id": aid,
                "diff": {"before": before, "proposed": params},
                "blast_radius": [target],
                "resource_etag": etag,
                "rollback_recipe": None if concept else {"target_c": 20},
            }
            phash = canonical_sha256(inhoud)
            self.bewijs = {
                "id": str(uuid.uuid4()),
                "action_id": aid,
                "resource_etag": etag,
                "preview_hash": phash,
                "status": "proposed",
                "before": before,
                "before_hash": canonical_sha256(before),
                "before_observed_at": utcnow().isoformat(),
            }
            return antwoord(
                200,
                {
                    **inhoud,
                    "proposal_id": self.bewijs["id"],
                    "preview_hash": phash,
                    "before": before,
                    "concept_only": concept,
                    "status": "proposed",
                    "requires_backup": False,
                    "valid_until": (utcnow() + timedelta(seconds=120)).isoformat(),
                },
            )
        assert path == "apply" and self.vorige is not None
        assert prop["idempotency_key"] == self.vorige["idempotency_key"]
        assert prop["actor"] == self.vorige["actor"] and prop["parameters"] == self.vorige["parameters"]
        ap = env["approval"]
        assert ap["request_id"] == prop["idempotency_key"]
        assert ap["action_scope"] == {"action_id": aid, "target": target, "parameters_sha256": canonical_sha256(params)}
        assert (
            ap["preview_hash"] == self.bewijs["preview_hash"]
            and ap["resource_etag"] == self.bewijs["resource_etag"] == prop["expected_version"]
        )
        self.aantal += 1
        self.bewijs.update(command_id=str(uuid.uuid4()), status="queued")
        return antwoord(
            202, {"evidence_id": self.bewijs["id"], "command_id": self.bewijs["command_id"], "status": "queued"}
        )

    def bevestig(self):
        after = {**self.voor, "target_c": 22}
        self.bewijs.update(
            status="confirmed", after=after, after_hash=canonical_sha256(after), after_observed_at=utcnow().isoformat()
        )


@pytest.fixture
def gekoppeld(admin, app, doel, huis_simulatie, monkeypatch):
    code, toestand, calls = huis_simulatie
    res = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert res.status_code == 201
    link_id = res.json()["id"]
    eigenaar = Eigenaar(app.state.keyring().policy_signing.public_key())
    bestaand = outbound.request

    def transport(base, method, path, **opties):
        if path.startswith("/connector/v1/"):
            assert opties["headers"]["Authorization"] == f"Bearer {toestand['token']}"
            assert opties["policy"].allowed_peer_addresses
            return eigenaar.verzoek(method, path.removeprefix("/connector/v1/"), opties)
        return bestaand(base, method, path, **opties)

    monkeypatch.setattr(outbound, "request", transport)
    now = utcnow()
    poort = GateInputs(
        dict(ALLE_BESLUITEN),
        {"status": "ok", "data": [{"naam": "proef", "status": "ONLINE", "gezond": True}]},
        {"finished_at": now},
        3600,
        True,
        {"status": "ok"},
        now,
        groene_appmetingen(now),
    )
    monkeypatch.setattr(blokkades, "gate_inputs", lambda *_: poort)
    target = {"link_id": link_id, "zone_id": eigenaar.zone_id}
    return eigenaar, target, poort, calls


def voorstel(admin, target, actie="zone.command", params=None):
    return admin.post(
        "/api/v1/actions",
        json={
            "action_id": actie,
            "target": target,
            "risk_claim": "R0",
            "parameters": {"target_c": 22} if params is None else params,
            "reason": "Lokale proef",
        },
        headers=idem(),
    )


def test_ondertekend_voorstel_een_uitvoering_en_bewijs(admin, gekoppeld):
    eigenaar, target, _, _ = gekoppeld
    gemaakt = voorstel(admin, target)
    assert gemaakt.status_code == 201, gemaakt.json()
    plan = gemaakt.json()
    assert (plan["risk_class"], plan["status"]) == ("R2", "wacht_op_goedkeuring")
    assert voer_uit(admin, plan).status_code == 409
    assert keur_goed(admin, plan).status_code == 200
    idem_headers = idem()
    pad = f"/api/v1/actions/{plan['request_id']}"
    eerste = admin.post(pad + "/execute", headers=idem_headers)
    herhaling = admin.post(pad + "/execute", headers=idem_headers)
    assert eerste.status_code == herhaling.status_code == 202 and eerste.json() == herhaling.json()
    assert voer_uit(admin, plan).status_code == 409
    assert eigenaar.aantal == 1 and len(eigenaar.nonces) == 2
    assert eigenaar.paden[-1] == ("GET", f"evidence/{eigenaar.bewijs['id']}")
    eigenaar.bevestig()
    eigenaar.vernietig_bewijs = True
    assert admin.post(pad + "/reconcile", headers=idem()).status_code == 502
    assert haal(admin, plan)["status"] == "onbekend"
    eigenaar.vernietig_bewijs = False
    uit = admin.post(pad + "/reconcile", headers=idem())
    assert uit.status_code == 200 and uit.json()["status"] == "uitgevoerd"
    bewijs = uit.json()["resultaat"]
    assert (bewijs["before"]["target_c"], bewijs["after"]["target_c"]) == ("20", "22")
    assert bewijs["before_hash"] != bewijs["after_hash"] and eigenaar.aantal == 1


def test_concept_heeft_geen_uitvoering(admin, gekoppeld):
    eigenaar, target, _, _ = gekoppeld
    plan = voorstel(admin, target, huis.CONCEPT, {"blocks": []})
    assert plan.status_code == 201 and plan.json()["status"] == "concept"
    assert voer_uit(admin, plan.json()).status_code == 409
    assert not any(path == "apply" for _, path in eigenaar.paden)


@pytest.mark.parametrize(
    ("actie", "params"), [("light.group.set", {"on": True}), ("light.scene.recall", {}), ("zone.resume", {})]
)
def test_lokale_eigenaar_zonder_herstelpad_voert_niets_uit(admin, gekoppeld, actie, params):
    eigenaar, target, _, _ = gekoppeld
    doel = {"link_id": target["link_id"], huis.HUIS_DOELVELDEN[actie]: eigenaar.zone_id}
    res = voorstel(admin, doel, actie, params)
    assert (res.status_code, res.json()["code"]) == (501, "capability_unavailable")
    assert res.json()["details"].get("reason") != "hub_keyset_missing"
    assert eigenaar.paden == [("GET", "discover"), ("POST", "propose")]
    assert eigenaar.aantal == 0


def test_schema_klimaatgate_en_beschermd_doel_voor_ondertekening(admin, gekoppeld, monkeypatch):
    eigenaar, target, poort, calls = gekoppeld

    def geen_handtekening(*_args):
        pytest.fail("Een geweigerd doel of schema mag geen handtekening krijgen.")

    monkeypatch.setattr(execreq, "sign", geen_handtekening)
    aantal = len(calls)
    poort.decisions["D12"] = ("Open", None)
    for actie in ("zone.command", "zone.resume"):
        assert voorstel(admin, target, actie).json()["code"] == "actie_geblokkeerd"
    for naam in ("boiler", "ketel", "water-heater", "warm water"):
        res = voorstel(admin, {"zone_id": naam})
        assert (res.status_code, res.json()["code"]) == (403, "policy_denied")
    assert voorstel(admin, target, "zone.onbekend").status_code == 403
    blokken = [
        {
            "days": list(range(7)),
            "start": f"{i // 60:02}:{i % 60:02}",
            "target_c": 22,
            "mode": "heat",
            "label": "é" * 50,
        }
        for i in range(100)
    ]
    groot = voorstel(admin, target, huis.CONCEPT, {"blocks": blokken})
    assert (groot.status_code, groot.json()["code"]) == (422, "parameters_ongeldig")
    assert groot.json()["details"]["fouten"] == [
        {"veld": "parameters", "code": "te_groot", "fout": "hooguit 16384 bytes"}
    ]
    assert len(calls) == aantal and eigenaar.paden == []
    poort.decisions["D12"] = ("Getest", None)
    assert voorstel(admin, target, params={"target_c": 33}).json()["code"] == "parameters_ongeldig"
    eigenaar.verboden = True
    assert voorstel(admin, target).json()["code"] == "policy_denied"
    assert all(method == "GET" for method, _ in eigenaar.paden)


def test_goedgekeurd_doel_en_ai_blijven_beschermd(admin, app, settings, gekoppeld):
    eigenaar, target, _, _ = gekoppeld
    plan = voorstel(admin, target).json()
    assert keur_goed(admin, plan).status_code == 200
    eigenaar.verboden = True
    voor = len(eigenaar.nonces)
    assert voer_uit(admin, plan).json()["code"] == "policy_denied"
    assert len(eigenaar.nonces) == voor and eigenaar.aantal == 0
    with app.state.sessionmaker() as db, pytest.raises(service.Bewaard, match="Het beleid") as fout:
        service.stel_voor(
            db,
            settings,
            app.state.vault,
            None,
            request_id=uuid.uuid4(),
            action_id="light.group.set",
            target={"group_id": "ketel"},
            parameters={"on": False},
            actor=("ai", "proef"),
            reason="Proef",
            risk_claim="R0",
            evidence_ids=[],
            expected_version=None,
            expires_in_seconds=120,
            trace_id="proef",
            keyring=app.state.keyring(),
        )
    assert fout.value.code == "policy_denied" and len(eigenaar.nonces) == voor


def test_verkeerde_sleutel_ontbrekende_pin_en_rotatie(admin, app, gekoppeld):
    eigenaar, target, _, _ = gekoppeld
    eigenaar.pub = Ed25519PrivateKey.generate().public_key()
    assert voorstel(admin, target).status_code == 403
    eigenaar.pub = None
    res = voorstel(admin, target)
    assert (res.status_code, res.json()["code"]) == (501, "capability_unavailable")
    assert res.json()["details"] == {"reason": "hub_keyset_missing", "href": huis.DIENSTEN}
    assert "Plak eerst de Hub-sleutelset in my_house" in res.json()["message"]
    vingerafdruk = app.state.keyring().keyset_fingerprint()
    res = admin.post("/api/v1/auth/key-rotations", headers=idem())
    assert (res.status_code, res.json()["code"]) == (409, "sleutelrotatie_wacht_op_bevestiging")
    assert app.state.keyring().keyset_fingerprint() == vingerafdruk and eigenaar.aantal == 0
