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
- Een te laat afgeleverd verzoek (vervaltijd vanaf ``timestamp_utc`` verstreken) wordt geen voorstel meer.
- Elke weigering of fout staat in de audit (EX45), alleen met codes en ID's: geen vrije tekst of waarden van de flow.
  Een onverwachte fout is nooit stil: ``uitkomst_onbekend`` in de audit, er is niets voorgesteld.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hub import audit
from hub.actions import service
from hub.config import Settings
from hub.errors import HubError
from hub.events.envelope import EventEnvelope
from hub.keys import KeyRing
from hub.models import ActionRequest
from hub.timeutil import utcnow
from hub.vault import Vault

log = logging.getLogger("hub.flows")

FLOW_EVENT = "flow.action.requested"
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
    evidence_ids: list[Annotated[StrictStr, Field(min_length=1, max_length=128)]] = Field(max_length=20)
    expires_in_seconds: StrictInt = Field(ge=MIN_GELDIG_S, le=86400)
    owner: StrictStr = Field(min_length=1, max_length=200)
    flow: FlowInfo
    trigger_event_id: uuid.UUID | None
    origin_chain: list[Annotated[StrictStr, Field(pattern=FLOW_ACTOR_RE)]] = Field(max_length=16)
    risk_claim_genegeerd: StrictBool


def request_id_voor(source_app: str, action_request_id: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(FLOW_NS, f"{source_app}:{action_request_id}")


def _weiger(db: Session, env: EventEnvelope, code: str, **details: Any) -> None:
    """Een flowverzoek dat geen voorstel werd: vastgelegd in de audit (alleen codes en ID's) en gecommit."""
    flow = env.actor.type == "flow"
    audit.record(
        db,
        actor_type="flow" if flow else "service",
        actor_id=env.actor.id if flow else env.source_app,
        action="action.flow_request.refused",
        target_type="event",
        target_id=str(env.event_id),
        details={"code": code, "event_type": env.event_type, "bron": env.source_app, **details},
        trace_id=str(env.trace_id),
    )
    db.commit()


def _velden(exc: ValidationError) -> list[str]:
    """Namen van de foute velden, alleen als het een bekend veld is (een onbekende sleutel is vrije tekst)."""
    bekend = set(FlowVerzoek.model_fields)
    return sorted({str(e["loc"][0]) if e["loc"] and e["loc"][0] in bekend else "onbekend_veld" for e in exc.errors()})


def verwerk(db: Session, settings: Settings, vault: Vault, keyring: KeyRing, env: EventEnvelope) -> None:
    """Een nieuw (niet-dubbel) event uit de inbox; doet niets voor andere events. De inbox heeft het event al
    vastgelegd: wat hier gebeurt, verandert het antwoord aan de bron niet."""
    if env.event_type != FLOW_EVENT or env.source_app != FLOW_BRON:
        return
    try:
        p = FlowVerzoek.model_validate(env.payload)
    except ValidationError as exc:
        _weiger(db, env, "payload_ongeldig", velden=_velden(exc))
        return
    ids = {"action_request_id": str(p.action_request_id), "action_id": p.action_id, "flow_id": str(p.flow.id)}
    eigen = f"flow:{p.flow.id}"
    if (env.actor.type, env.actor.id) != ("flow", eigen) or p.actor.id != eigen or env.entity.type != "flow":
        _weiger(db, env, "actor_past_niet", **ids)
        return
    if env.entity.id != str(p.flow.id):
        _weiger(db, env, "flow_past_niet", **ids)
        return
    now = utcnow()
    resterend = int((env.timestamp_utc + timedelta(seconds=p.expires_in_seconds) - now).total_seconds())
    if resterend < MIN_GELDIG_S:
        _weiger(db, env, "verzoek_verlopen", **ids)
        return
    request_id = request_id_voor(env.source_app, p.action_request_id)
    if db.get(ActionRequest, request_id) is not None:
        return  # al eerder afgeleverd (EX46): één voorstel
    evidence = [f"event:{env.event_id}", *p.evidence_ids][:20]
    try:
        service.voorcontrole(db, p.action_id, p.target, p.parameters)
        service.stel_voor(
            db,
            settings,
            vault,
            None,
            actor=("flow", eigen),
            request_id=request_id,
            action_id=p.action_id,
            target=p.target,
            parameters=p.parameters,
            reason=p.reason.strip() or p.action_id,
            risk_claim=None,  # een flow claimt niets; de risk_claim van de flow telt nooit (EX18)
            evidence_ids=evidence,
            expected_version=p.expected_version,
            expires_in_seconds=min(resterend, p.expires_in_seconds),
            keyring=keyring,
            trace_id=str(env.trace_id),
        )
        db.commit()
    except service.Bewaard:
        db.commit()  # beleid weigert: rij ``geweigerd`` en ``action.proposal.refused`` met actor flow (EX45)
    except HubError as exc:
        db.rollback()
        if exc.code != "verzoek_bestaat_al":
            _weiger(db, env, exc.code, **ids)
    except IntegrityError:
        db.rollback()  # gelijktijdige levering van hetzelfde verzoek: de ander maakte het voorstel
        if db.get(ActionRequest, request_id) is None:
            _weiger(db, env, "uitkomst_onbekend", **ids)
    except Exception as exc:
        db.rollback()
        # alleen de soort fout: de tekst van een databasefout kan waarden van de flow bevatten
        log.error("flowverzoek %s niet verwerkt: %s", env.event_id, type(exc).__name__)
        _weiger(db, env, "uitkomst_onbekend", **ids)
