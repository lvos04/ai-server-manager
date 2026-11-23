"""Automatiseringen zonder code, Hub-kant (B01-008; contract 1.3 §7 en §8; EX45, EX46).

De Hub bouwt geen eigen flow-editor: flows leven in Node-RED achter home-control-hub (B11). Vraagt een flow daar een
actie aan, dan stuurt home-control-hub het event ``flow.action.requested`` naar de inbox. Dit bestand maakt er een
gewoon voorstel van met actor ``flow``: dezelfde classificatie, gates, preview, goedkeuring en ondertekende uitvoering
als elk ander voorstel (:func:`hub.actions.service.stel_voor`). Uitvoeren blijft een handeling van een gebruiker
(``/api/v1/actions/{id}/execute``); de Hub voert een flowverzoek nooit vanzelf uit.

Vaste regels:

- Alleen ``home-control-hub`` is eigenaar van het domein ``flow`` (§7); hetzelfde eventtype van een andere bron is
  alleen algemene informatie en wordt nooit een voorstel.
- De payload gaat door een positieve witte lijst (:class:`FlowVerzoek`): elk veld met vaste vorm en type, onbekende
  velden geweigerd. Envelope en payload moeten dezelfde flow en dezelfde actor noemen.
- Koppeling op ID: het voorstel krijgt een vaste ``request_id`` uit (bron, ``action_request_id``). Hetzelfde verzoek
  vijf keer afgeleverd (ook met een nieuw ``event_id``) geeft één voorstel en dus hooguit één uitvoering (EX46).
  Dezelfde sleutel met een andere actor, actie, doel, parameters of reden is een conflict in de audit, nooit stil
  een duplicaat (R-VEILIG-5).
- Ontvangst en verwerking zitten in één transactie (de inbox commit); na een onderbreking geeft herlevering het
  voorstel alsnog (R-VEILIG-4). Reden en bewijs-ID's gaan door een vaste vorm of de redactor (R-VEILIG-1).
- Een te laat afgeleverd verzoek (vervaltijd vanaf ``timestamp_utc`` verstreken) wordt geen voorstel meer.
- Elke weigering of fout staat in de audit (EX45), alleen met codes en ID's: geen vrije tekst of waarden van de flow.
  Een onverwachte fout is nooit stil: ``uitkomst_onbekend`` in de audit, er is niets voorgesteld.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Annotated, Any, Literal

from asm_policy import execreq
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hub import audit
from hub.actions import service
from hub.config import Settings
from hub.errors import HubError
from hub.events.envelope import FLOW_EVENT, EventEnvelope
from hub.keys import KeyRing
from hub.models import ActionRequest
from hub.redact import redact_text
from hub.timeutil import utcnow
from hub.vault import Vault

log = logging.getLogger("hub.flows")

FLOW_BRON = "home-control-hub"
#: vaste naamruimte voor de request_id van een flowverzoek (uuid5 van bron en action_request_id)
FLOW_NS = uuid.UUID("5d0f4c1e-6b7a-4f63-9a51-1f0b8e2c7a40")
FLOW_ACTOR_RE = r"^flow:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
MIN_GELDIG_S = 60  # zelfde ondergrens als een voorstel van een gebruiker (ProposalIn.expires_in_seconds)


class _Strikt(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlowActor(_Strikt):
    type: Literal["flow"]
    id: StrictStr = Field(pattern=FLOW_ACTOR_RE)


class FlowInfo(_Strikt):
    id: uuid.UUID
    label: StrictStr = Field(min_length=1, max_length=200)
    version: StrictInt = Field(ge=0)


class FlowVerzoek(_Strikt):
    """De payload van ``flow.action.requested`` zoals home-control-hub hem stuurt (``automation/actions.py``,
    ``request_action``): een ActionProposal (§8) met de herkomst van de flow."""

    action_request_id: uuid.UUID
    idempotency_key: uuid.UUID
    action_id: StrictStr = Field(min_length=1, max_length=96, pattern=r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+){1,3}$")
    target: dict[str, Any]
    parameters: dict[str, Any]
    reason: StrictStr = Field(min_length=1, max_length=500)
    actor: FlowActor
    expected_version: StrictStr | None = Field(default=None, max_length=300)
    evidence_ids: list[uuid.UUID] = Field(max_length=20)  # event-ID's van de aanleiding (vaste vorm)
    expires_in_seconds: StrictInt = Field(ge=MIN_GELDIG_S, le=86400)
    owner: StrictStr = Field(min_length=1, max_length=200)
    flow: FlowInfo
    trigger_event_id: uuid.UUID | None
    origin_chain: list[Annotated[StrictStr, Field(pattern=FLOW_ACTOR_RE)]] = Field(max_length=16)
    risk_claim_genegeerd: StrictBool


def request_id_voor(source_app: str, action_request_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(FLOW_NS, f"{source_app}:{action_request_id}")


def _weiger(db: Session, env: EventEnvelope, actor: tuple[str, str], code: str, **details: Any) -> None:
    """Een flowverzoek dat geen voorstel werd: in de audit (alleen codes en ID's). ``actor`` is gecontroleerd: de flow
    pas na de actorcontrole, daarvoor de geverifieerde bron (R-VEILIG-2). De inbox commit."""
    audit.record(
        db,
        actor_type=actor[0],
        actor_id=actor[1],
        action="action.flow_request.refused",
        target_type="event",
        target_id=str(env.event_id),
        details={"code": code, "event_type": env.event_type, "bron": env.source_app, **details},
        trace_id=str(env.trace_id),
    )


def _velden(exc: ValidationError) -> list[str]:
    """Namen van de foute velden, alleen als het een bekend veld is (een onbekende sleutel is vrije tekst)."""
    bekend = set(FlowVerzoek.model_fields)
    return sorted({str(e["loc"][0]) if e["loc"] and e["loc"][0] in bekend else "onbekend_veld" for e in exc.errors()})


def _zelfde(bestaand: ActionRequest, actor: tuple[str, str], p: FlowVerzoek, reden: str) -> bool:
    """Is het bestaande voorstel onder deze sleutel dezelfde aanvraag? Vergeleken wordt wat onveranderlijk is
    bewaard: actor, actie, doel (bij een weigering de veilige velden), reden en de canonieke parameterhash."""
    try:
        psha: str | None = execreq.parameters_sha256(p.parameters)
    except (TypeError, ValueError):
        psha = None
    doel = service.veilig_doel(p.target) if bestaand.status == "geweigerd" else p.target
    return (
        (bestaand.actor_type, bestaand.actor_id, bestaand.action_id) == (*actor, p.action_id)
        and bestaand.target == doel
        and bestaand.reden == reden
        and (bestaand.preview or {}).get("parameters_sha256") == psha
    )


def verwerk(db: Session, settings: Settings, vault: Vault, keyring: KeyRing, env: EventEnvelope) -> None:
    """Een nieuw (niet-dubbel) event uit de inbox; doet niets voor andere events. Loopt in de transactie van de inbox
    (die commit); het voorstel zelf in een savepoint, zodat een fout alleen het voorstel terugdraait."""
    if env.event_type != FLOW_EVENT or env.source_app != FLOW_BRON:
        return
    bron = ("service", FLOW_BRON)  # geverifieerd: source_app is gelijk aan de app van het service-token
    try:
        p = FlowVerzoek.model_validate(env.payload)
    except ValidationError as exc:
        _weiger(db, env, bron, "payload_ongeldig", velden=_velden(exc))
        return
    ids = {"action_request_id": str(p.action_request_id), "action_id": p.action_id, "flow_id": str(p.flow.id)}
    eigen = f"flow:{p.flow.id}"
    if (env.actor.type, env.actor.id) != ("flow", eigen) or p.actor.id != eigen or env.entity.type != "flow":
        _weiger(db, env, bron, "actor_past_niet", **ids)
        return
    flow = ("flow", eigen)
    if env.entity.id != str(p.flow.id):
        _weiger(db, env, flow, "flow_past_niet", **ids)
        return
    now = utcnow()
    resterend = int((env.timestamp_utc + timedelta(seconds=p.expires_in_seconds) - now).total_seconds())
    if resterend < MIN_GELDIG_S:
        _weiger(db, env, flow, "verzoek_verlopen", **ids)
        return
    request_id = request_id_voor(env.source_app, p.action_request_id)
    reden = redact_text(p.reason.strip()) or p.action_id

    def al_bekend() -> bool:
        bestaand = db.get(ActionRequest, request_id, populate_existing=True)
        if bestaand is None:
            return False
        if not _zelfde(bestaand, flow, p, reden):
            _weiger(db, env, flow, "idempotentie_conflict", request_id=str(request_id), **ids)
        return True  # al eerder afgeleverd (EX46): één voorstel

    if al_bekend():
        return
    evidence = [f"event:{env.event_id}", *map(str, p.evidence_ids)][:20]
    sp = db.begin_nested()
    try:
        service.voorcontrole(db, p.action_id, p.target, p.parameters)
        service.stel_voor(
            db,
            settings,
            vault,
            None,
            actor=flow,
            request_id=request_id,
            action_id=p.action_id,
            target=p.target,
            parameters=p.parameters,
            reason=reden,
            risk_claim=None,  # een flow claimt niets; de risk_claim van de flow telt nooit (EX18)
            evidence_ids=evidence,
            expected_version=p.expected_version,
            expires_in_seconds=min(resterend, p.expires_in_seconds),
            keyring=keyring,
            trace_id=str(env.trace_id),
        )
        sp.commit()
    except service.Bewaard:
        sp.commit()  # beleid weigert: rij ``geweigerd`` en ``action.proposal.refused`` met actor flow (EX45)
    except HubError as exc:
        sp.rollback()
        if exc.code != "verzoek_bestaat_al" or not al_bekend():
            _weiger(db, env, flow, exc.code, **ids)
    except IntegrityError:
        sp.rollback()  # gelijktijdige levering van hetzelfde verzoek: de ander maakte het voorstel
        if not al_bekend():
            _weiger(db, env, flow, "uitkomst_onbekend", **ids)
    except Exception as exc:
        sp.rollback()
        # alleen de soort fout: de tekst van een databasefout kan waarden van de flow bevatten
        log.error("flowverzoek %s niet verwerkt: %s", env.event_id, type(exc).__name__)
        _weiger(db, env, flow, "uitkomst_onbekend", **ids)
