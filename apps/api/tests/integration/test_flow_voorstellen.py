"""Automatiseringen zonder code, Hub-kant (B01-008; EX45, EX46 Hub-deel; contract 1.3 §7 en §8).

``flow.action.requested`` van een nagebootste home-control-hub wordt een gewoon voorstel met actor ``flow``. Zonder
executor: classificatie, weigeringen en audit. De uitvoering staat in ``tests/e2e/test_flow_acties.py``. Sim-getest.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from actiehelpers import HOST, Stack, app_target, bouw_stack, haal, stel_voor
from conftest import enroll_body, idem
from executorhelpers import write_nas
from fakes.fake_truenas import FakeTrueNAS
from flowhelpers import flow_audit, flow_event, flow_request_id, koppel_hch

from hub.models import ActionRequest, InboxEvent
from hub.timeutil import iso, utcnow

pytestmark = pytest.mark.integration


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def stack(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Stack:
    return bouw_stack(
        admin=admin,
        app=app,
        nas=nas,
        worker_once=worker_once,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        met_executor=False,
    )


@pytest.fixture
def hch(stack: Stack) -> Any:
    return koppel_hch(stack.admin, stack.app)


def _stuur(hch: Any, ev: dict[str, Any]) -> Any:
    return hch.post("/api/v1/events/inbox", json=ev)


def _rijen(app: Any) -> list[ActionRequest]:
    from sqlalchemy import select

    with app.state.sessionmaker() as db:
        return list(db.scalars(select(ActionRequest)))


def _geweigerd(hch: Any, app: Any, ev: dict[str, Any], code: str) -> dict[str, Any]:
    """Het event is ontvangen, er is geen voorstel, en de weigering staat met deze code in de audit."""
    r = _stuur(hch, ev)
    assert r.status_code == 202 and r.json()["status"] == "accepted", r.text
    assert _rijen(app) == []
    regels = [a for a in flow_audit(app) if a["action"] == "action.flow_request.refused"]
    assert [a["details"]["code"] for a in regels] == [code], regels
    assert regels[0]["target"] == ev["event_id"]
    return regels[0]


# ---------------------------------------------------------------------- bouwpunt 2: een gewoon voorstel
def test_flowverzoek_wordt_voorstel_met_actor_flow_en_dezelfde_classificatie(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"))
    r = _stuur(hch, ev)
    assert r.status_code == 202 and r.json()["status"] == "accepted", r.text
    v = haal(stack.admin, flow_request_id(ev))
    assert v["actor"] == ev["actor"] and v["actor"]["type"] == "flow"
    assert (v["status"], v["risk_class"], v["goedkeuring_nodig"]) == ("klaar", "R1", False)
    assert v["risk_claim"] is None and f"event:{ev['event_id']}" in v["evidence_ids"]
    # Dezelfde classificatie als een voorstel van een beheerder voor dezelfde actie.
    mens = stel_voor(stack.admin, "app.restart", app_target("my-house")).json()
    assert (mens["risk_class"], mens["rule_ids"], mens["policy_hash"]) == (
        v["risk_class"],
        v["rule_ids"],
        v["policy_hash"],
    )
    gemaakt = [a for a in flow_audit(stack.app) if a["action"] == "action.proposal.created"]
    assert [a["actor"] for a in gemaakt] == [f"flow:{ev['actor']['id']}"]  # actor_type:actor_id


def test_r2_van_een_flow_wacht_op_menselijke_goedkeuring(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.stop", app_target("my-house"))  # Custom App: R2 (STOP-EENRICHTING)
    assert _stuur(hch, ev).status_code == 202
    v = haal(stack.admin, flow_request_id(ev))
    assert (v["status"], v["risk_class"], v["goedkeuring_nodig"]) == ("wacht_op_goedkeuring", "R2", True)
    # Zonder goedkeuring wordt er niets uitgevoerd.
    r = stack.admin.post(f"/api/v1/actions/{v['request_id']}/execute", headers=idem())
    assert r.status_code >= 400 and haal(stack.admin, v["request_id"])["status"] == "wacht_op_goedkeuring", r.text


# ---------------------------------------------------------------------- bouwpunt 3: idempotentie (EX46)
def test_vijf_keer_hetzelfde_event_geeft_een_voorstel(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"))
    antwoorden = [_stuur(hch, ev) for _ in range(5)]
    assert [a.status_code for a in antwoorden] == [202, 200, 200, 200, 200]
    assert [a.json()["status"] for a in antwoorden] == ["accepted"] + ["duplicate"] * 4
    # Ook een nieuwe aflevering met een nieuw event_id van hetzelfde actieverzoek geeft geen tweede voorstel.
    opnieuw = {**ev, "event_id": str(uuid.uuid4()), "source_event_id": "2"}
    assert _stuur(hch, opnieuw).json()["status"] == "accepted"
    rijen = _rijen(stack.app)
    assert [str(r.id) for r in rijen] == [flow_request_id(ev)]
    assert [a["action"] for a in flow_audit(stack.app)] == ["action.proposal.created"]


# ---------------------------------------------------------------------- bouwpunt 4 en 5: weigeren en auditbaar (EX45)
def test_dataset_verwijderen_via_flow_geweigerd_en_in_audit(stack: Stack, hch: Any) -> None:
    ev = flow_event("pool.dataset.delete", {"host_id": HOST, "dataset": "tank/media"})
    assert _stuur(hch, ev).status_code == 202
    v = haal(stack.admin, flow_request_id(ev))
    assert v["status"] == "geweigerd" and v["actor"]["type"] == "flow"
    assert "actie_verboden_destructief" in [b["code"] for b in v["blokkades"]]
    regels = [a for a in flow_audit(stack.app) if a["action"] == "action.proposal.refused"]
    assert [a["actor"] for a in regels] == [f"flow:{ev['actor']['id']}"]
    assert regels[0]["details"]["code"] == "actie_geweigerd"
    # Ook een beheerder kan dit geweigerde voorstel niet meer uitvoeren.
    r = stack.admin.post(f"/api/v1/actions/{v['request_id']}/execute", headers=idem())
    assert r.status_code >= 400 and haal(stack.admin, v["request_id"])["status"] == "geweigerd"


def test_actie_boven_de_rechten_van_een_flow_geweigerd(stack: Stack, hch: Any) -> None:
    """``ai_mag_voorstellen: false``: alleen een mens mag dit voorstellen; een flow niet."""
    ev = flow_event("sso.sessions.revoke", {"user": "test-gebruiker"})
    assert _stuur(hch, ev).status_code == 202
    v = haal(stack.admin, flow_request_id(ev))
    assert v["status"] == "geweigerd" and "alleen_beheerder" in [b["code"] for b in v["blokkades"]]
    assert "ACTOR:alleen_mens" in v["rule_ids"]


@pytest.mark.parametrize(
    ("action_id", "target", "parameters", "code"),
    [
        ("app.shell.exec", app_target("my-house"), {}, "actie_verboden_shell"),
        ("docker.run", app_target("my-house"), {}, "actie_verboden_shell"),
        ("app.restart", app_target("my-house"), {"notitie": "boiler aan"}, "boiler_verboden"),
        ("app.restart", app_target("boiler"), {}, "boiler_verboden"),
    ],
)
def test_geen_shell_en_geen_boiler_via_een_flow(
    stack: Stack, hch: Any, action_id: str, target: dict[str, Any], parameters: dict[str, Any], code: str
) -> None:
    ev = flow_event(action_id, target, parameters)
    assert _stuur(hch, ev).status_code == 202
    v = haal(stack.admin, flow_request_id(ev))
    assert v["status"] == "geweigerd" and code in [b["code"] for b in v["blokkades"]], v
    assert [a["action"] for a in flow_audit(stack.app)] == ["action.proposal.refused"]


def test_onbekende_actie_geweigerd_en_in_audit(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.verplaats", app_target("my-house"))
    assert _stuur(hch, ev).status_code == 202
    v = haal(stack.admin, flow_request_id(ev))
    assert v["status"] == "geweigerd" and v["resultaat"]["code"] == "actie_niet_toegestaan"


# ---------------------------------------------------------------------- B11-002: niets verdwijnt stil
def test_onbekende_schemaversie_is_een_zichtbare_fout(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"), schema_version="2.0")
    r = _stuur(hch, ev)
    assert r.status_code == 422, r.text
    assert "body.schema_version" in {f["veld"] for f in r.json()["details"]["fouten"]}
    from sqlalchemy import func, select

    with stack.app.state.sessionmaker() as db:
        assert db.scalar(select(func.count()).select_from(InboxEvent)) == 0
    assert _rijen(stack.app) == []


@pytest.mark.parametrize(
    "wijzig",
    [
        {"risk_claim": "R0"},  # onbekend veld
        {"risk_claim_genegeerd": "true"},  # tekst in plaats van een echte boolean
        {"expires_in_seconds": "900"},
        {"action_request_id": "geen-uuid"},
        {"actor": {"type": "user", "id": "beheerder"}},
    ],
)
def test_payload_buiten_de_witte_lijst_geweigerd_en_in_audit(stack: Stack, hch: Any, wijzig: dict[str, Any]) -> None:
    ev = flow_event("app.restart", app_target("my-house"))
    ev["payload"].update(wijzig)
    regel = _geweigerd(hch, stack.app, ev, "payload_ongeldig")
    assert regel["details"]["velden"] and set(regel["details"]["velden"]) <= {
        "onbekend_veld",
        "risk_claim_genegeerd",
        "expires_in_seconds",
        "action_request_id",
        "actor",
    }


def test_envelope_en_payload_moeten_dezelfde_flow_noemen(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"))
    ev["actor"] = {"type": "flow", "id": f"flow:{uuid.uuid4()}"}
    _geweigerd(hch, stack.app, ev, "actor_past_niet")


def test_entity_moet_de_flow_zijn(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"))
    ev["entity"] = {"type": "flow", "id": str(uuid.uuid4())}
    _geweigerd(hch, stack.app, ev, "flow_past_niet")


def test_te_laat_afgeleverd_verzoek_wordt_geen_voorstel(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"), timestamp_utc=iso(utcnow() - timedelta(hours=2)))
    _geweigerd(hch, stack.app, ev, "verzoek_verlopen")


def test_schemafout_in_de_parameters_is_zichtbaar(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"), {"grace_seconds": "lang"})
    regel = _geweigerd(hch, stack.app, ev, "parameters_ongeldig")
    assert regel["details"]["action_request_id"] == ev["payload"]["action_request_id"]
    assert "lang" not in str(regel["details"])  # geen waarden van de flow in de audit


def test_flow_event_van_een_andere_bron_wordt_geen_voorstel(stack: Stack) -> None:
    """Het domein ``flow`` is van home-control-hub (§7); een andere dienst kan er geen voorstel mee maken."""
    from fastapi.testclient import TestClient

    tok = stack.admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "mediaguard"}).json()
    c = TestClient(stack.app, base_url="https://testserver")
    svc = c.post("/api/v1/services/enroll", json=enroll_body("mediaguard", token=tok["enrollment_token"])).json()
    ev = flow_event("app.restart", app_target("my-house"), source_app="mediaguard")
    r = c.post("/api/v1/events/inbox", json=ev, headers={"Authorization": f"Bearer {svc['service_token']}"})
    assert r.status_code == 202, r.text
    assert _rijen(stack.app) == [] and flow_audit(stack.app) == []


# ---------------------------------------------------------------------- herstel R-VEILIG (S-P2-140)
MARKERING = "voorbeeldmarkering"  # synthetisch; de gewone redactor herkent "Bearer <markering>"


def _zet(app: Any, model: Any, sleutel: Any, **waarden: Any) -> None:
    """Boots een regel van vóór het herstel na (alleen testgegevens)."""
    with app.state.sessionmaker() as db:
        rij = db.get(model, sleutel)
        for k, v in waarden.items():
            setattr(rij, k, v)
        db.commit()


def test_r_veilig_1_weigering_bewaart_en_toont_alleen_veilige_velden(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.voorbeeld", {"app_id": "my-house", "toelichting": f"Bearer {MARKERING}"})
    ev["payload"]["reason"] = f"Flow: Bearer {MARKERING}"
    assert _stuur(hch, ev).status_code == 202
    v = haal(stack.admin, flow_request_id(ev))
    assert v["status"] == "geweigerd" and v["target"] == {"app_id": "my-house"}
    assert MARKERING not in str(v)
    (rij,) = _rijen(stack.app)
    assert MARKERING not in str((rij.target, rij.reden, rij.evidence_ids))
    # Een bestaande regel van vóór het herstel wordt bij het lezen ook geschoond.
    vuil = f"Bearer {MARKERING}"
    _zet(stack.app, ActionRequest, rij.id, target={"toelichting": vuil}, reden=vuil, evidence_ids=[vuil])
    assert MARKERING not in str(haal(stack.admin, flow_request_id(ev)))
    # Een bewijs-ID buiten de vaste vorm (event-ID) wordt geen voorstel.
    ander = flow_event("app.restart", app_target("my-house"), seq=2)
    ander["payload"]["evidence_ids"] = [f"Bearer {MARKERING}"]
    r = _stuur(hch, ander)
    assert r.status_code == 202 and len(_rijen(stack.app)) == 1
    regels = [a for a in flow_audit(stack.app) if a["action"] == "action.flow_request.refused"]
    assert [a["details"]["velden"] for a in regels] == [["evidence_ids"]]


def test_r_veilig_2_audit_noemt_de_geverifieerde_bron_bij_een_ongeldige_flow_id(hch: Any, stack: Stack) -> None:
    ev = flow_event("app.restart", app_target("my-house"))
    ev["actor"]["id"] = "gewone vrije proeftekst"
    regel = _geweigerd(hch, stack.app, ev, "actor_past_niet")
    assert regel["actor"] == "service:home-control-hub" and regel["target"] == ev["event_id"]
    assert "vrije proeftekst" not in str(flow_audit(stack.app))


def test_r_veilig_3_inbox_bewaart_en_toont_alleen_de_witte_lijst(stack: Stack, hch: Any) -> None:
    ev = flow_event("app.restart", app_target("my-house"))
    ev["payload"]["extra_proefveld"] = "gewone vrije proeftekst"
    _geweigerd(hch, stack.app, ev, "payload_ongeldig")
    (item,) = stack.admin.get("/api/v1/events").json()["items"]
    assert set(item["payload"]) == {
        "action_request_id",
        "action_id",
        "trigger_event_id",
        "expires_in_seconds",
        "inhoud_sha256",
    }
    from sqlalchemy import select

    with stack.app.state.sessionmaker() as db:
        rij = db.scalars(select(InboxEvent)).one()
        assert "proeftekst" not in str(rij.payload) and "Flow: test" not in str(rij.payload)
    # Een bestaande regel met de volledige payload wordt bij het lezen gefilterd.
    _zet(stack.app, InboxEvent, rij.seq, payload=ev["payload"])
    (item,) = stack.admin.get("/api/v1/events").json()["items"]
    assert "proeftekst" not in str(item["payload"]) and "target" not in item["payload"]


def test_r_veilig_4_herlevering_na_onderbreking_geeft_een_voorstel(
    stack: Stack, hch: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hub.actions import flows

    ev = flow_event("app.restart", app_target("my-house"))

    def onderbreek(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("gesimuleerde onderbreking")

    with monkeypatch.context() as tijdelijk:
        tijdelijk.setattr(flows, "verwerk", onderbreek)
        with pytest.raises(RuntimeError):
            _stuur(hch, ev)
    from sqlalchemy import func, select

    with stack.app.state.sessionmaker() as db:
        assert db.scalar(select(func.count()).select_from(InboxEvent)) == 0  # niets half vastgelegd
    r = _stuur(hch, ev)
    assert (r.status_code, r.json()["status"]) == (202, "accepted")
    assert [str(r.id) for r in _rijen(stack.app)] == [flow_request_id(ev)]
    assert [a["action"] for a in flow_audit(stack.app)] == ["action.proposal.created"]


def test_r_veilig_5_hergebruikt_bronvolgnummer_is_een_zichtbaar_conflict(stack: Stack, hch: Any) -> None:
    eerste = flow_event("app.restart", app_target("my-house"), seq=1)
    tweede = flow_event("app.restart", app_target("my-house"), seq=1)  # teruggezette outbox-teller
    assert _stuur(hch, eerste).status_code == 202
    r = _stuur(hch, tweede)
    assert (r.status_code, r.json()["code"]) == (409, "bron_id_conflict"), r.text
    assert [str(x.id) for x in _rijen(stack.app)] == [flow_request_id(eerste)]
    audit = stack.admin.get("/api/v1/audit", params={"actie": "event.inbox.conflict"}).json()["items"]
    assert [a["doel_id"] for a in audit] == [tweede["event_id"]]
    # Dezelfde aanvraag-ID met een andere actie: conflict in de audit, het bestaande voorstel blijft gelijk.
    ander = flow_event(
        "app.stop",
        app_target("my-house"),
        flow_id=uuid.UUID(eerste["entity"]["id"]),
        action_request_id=uuid.UUID(eerste["payload"]["action_request_id"]),
        seq=3,
    )
    (voor,) = _rijen(stack.app)
    assert _stuur(hch, ander).status_code == 202
    (rij,) = _rijen(stack.app)
    assert (rij.action_id, rij.status, rij.actor_id) == ("app.restart", voor.status, voor.actor_id)
    regels = [a for a in flow_audit(stack.app) if a["action"] == "action.flow_request.refused"]
    assert [a["details"]["code"] for a in regels] == ["idempotentie_conflict"]


def test_r_veilig_5_gelijktijdige_levering_geeft_een_voorstel(stack: Stack) -> None:
    from concurrent.futures import ThreadPoolExecutor

    eerste = flow_event("app.restart", app_target("my-house"))
    tweede = {**eerste, "event_id": str(uuid.uuid4()), "source_event_id": "2"}
    with koppel_hch(stack.admin, stack.app) as zender, ThreadPoolExecutor(max_workers=2) as pool:
        codes = list(pool.map(lambda e: zender.post("/api/v1/events/inbox", json=e).status_code, [eerste, tweede]))
    assert codes == [202, 202]
    assert [str(r.id) for r in _rijen(stack.app)] == [flow_request_id(eerste)]
    assert [a["action"] for a in flow_audit(stack.app)] == ["action.proposal.created"]
