"""Acties, previews en goedkeuringen (contract 1.3 §8; B01-007, B01-003, B02-005/006; ADR-0030).

Eén weg voor elke wijziging buiten de Hub:

1. ``POST /api/v1/actions`` — een getypt voorstel (``ActionProposal``). De policy-engine bepaalt de risicoklasse;
   ``risk_claim`` uit het voorstel wordt bewaard en genegeerd. Het antwoord bevat de preview en drie hashes.
2. ``POST /api/v1/actions/{id}/approve`` — alleen bij R2/R3, alleen door een beheerder, alleen voor precies de preview
   die hij zag (``preview_hash``, ``resource_etag``, ``policy_hash``). Hooguit 15 minuten geldig, één keer bruikbaar.
3. ``POST /api/v1/actions/{id}/execute`` — de Hub controleert alles opnieuw, ondertekent een ``ExecutionRequest`` en
   stuurt dat naar de executor. De executor controleert zelf nog eens en voert uit met readback.

De Hub heeft geen schrijfsleutel van TrueNAS en geen route om een blokkade weg te klikken. Alleen gebruikerssessies:
voorstellen door diensten, flows of AI krijgen een eigen ingang in een latere fase.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from hub import audit
from hub.actions import beleid, service
from hub.actions import blokkades as blok_mod
from hub.deps import (
    DB,
    Admin,
    Cursor,
    Idem,
    Idempotency,
    Limit,
    Operator,
    SettingsDep,
    Viewer,
    decode_cursor,
    encode_cursor,
    get_keyring,
    get_vault,
)
from hub.errors import HubError, error_body, trace_id_of
from hub.keys import KeyRing
from hub.models import ActionRequest
from hub.timeutil import iso, utcnow
from hub.vault import Vault

router = APIRouter(prefix="/api/v1", tags=["acties en goedkeuringen"])
VaultDep = Annotated[Vault, Depends(get_vault)]
KeyRingDep = Annotated[KeyRing, Depends(get_keyring)]

SHA = r"^sha256:[0-9a-f]{64}$"
StatusFilter = Literal[
    "alle",
    "open",
    "wacht_op_goedkeuring",
    "klaar",
    "goedgekeurd",
    "afgewezen",
    "geweigerd",
    "bezig",
    "uitgevoerd",
    "mislukt",
    "afwijking",
    "onbekend",
    "verlopen",
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ActorIn(Strict):
    type: str = Field(min_length=1, max_length=16)
    id: str = Field(min_length=1, max_length=80)


class ProposalIn(Strict):
    """``ActionProposal`` (contract §8). ``idempotency_key`` staat in de header; in de body mag hij ook, mits gelijk."""

    idempotency_key: uuid.UUID | None = None
    action_id: str = Field(min_length=1, max_length=96, description="Getypte actie uit de allowlist, bv. app.restart.")
    target: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(min_length=1, max_length=500)
    actor: ActorIn | None = Field(default=None, description="Moet passen bij de aangemelde gebruiker.")
    expected_version: str | None = Field(default=None, max_length=300, description="ETag die de aanvrager zag.")
    risk_claim: str | None = Field(default=None, max_length=16, description="Wordt bewaard en genegeerd.")
    evidence_ids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(default_factory=list, max_length=20)
    expires_in_seconds: int = Field(default=3600, ge=60, le=86400)


class ApproveIn(Strict):
    """De drie hashes van de preview die de beheerder zag; wijkt er één af, dan is er niets goedgekeurd."""

    preview_hash: str = Field(pattern=SHA)
    resource_etag: str = Field(min_length=1, max_length=300)
    policy_hash: str = Field(pattern=SHA)


class RejectIn(Strict):
    reden: str = Field(min_length=1, max_length=300)


class NoodstopIn(Strict):
    actief: bool
    reden: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _reden(self) -> NoodstopIn:
        if self.actief and not (self.reden or "").strip():
            raise ValueError("een reden is verplicht bij het inschakelen van de noodstop")
        return self


def _afhandelen(request: Request, idem: Idempotency, werk: Callable[[], tuple[int, dict[str, Any]]]) -> JSONResponse:
    """Idempotent uitvoeren. Een :class:`service.Bewaard`-fout wordt mét de toestandswijziging vastgelegd; elke
    andere fout laat de database ongemoeid."""
    replay = idem.replay()
    if replay is not None:
        return replay
    try:
        status, body = werk()
    except service.Bewaard as exc:
        return idem.save(exc.status, error_body(request, exc.code, exc.message, exc.details))
    return idem.save(status, body)


# ------------------------------------------------------------------ beleid en noodstop
@router.get("/policy", summary="Het risicobeleid: acties, klassen, blokkades en policy_hash (alleen-lezen)")
def get_policy(_: Viewer) -> dict[str, Any]:
    return beleid.weergave(beleid.get_policy())


@router.get("/actions/noodstop", summary="Staat de noodstop aan? (dan voert de Hub geen enkele actie uit)")
def get_noodstop(db: DB, _: Viewer) -> dict[str, Any]:
    return blok_mod.noodstop(db)


@router.put("/actions/noodstop", summary="Noodstop in- of uitschakelen (alleen beheerder)")
def put_noodstop(body: NoodstopIn, request: Request, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    def werk() -> tuple[int, dict[str, Any]]:
        staat = blok_mod.zet_noodstop(
            db, actief=body.actief, reden=(body.reden or "").strip() or None, door=principal.name
        )
        audit.record(
            db,
            actor_type="user",
            actor_id=principal.name,
            action="action.emergency_stop.enabled" if body.actief else "action.emergency_stop.disabled",
            target_type="hub_setting",
            target_id=blok_mod.NOODSTOP_KEY,
            details={"reden": staat["reden"]},
            trace_id=trace_id_of(request),
        )
        return 200, staat

    return _afhandelen(request, idem, werk)


# ------------------------------------------------------------------ voorstellen
@router.post(
    "/actions",
    status_code=201,
    summary="Actie voorstellen: classificatie, preview en hashes (er wordt nog niets uitgevoerd)",
)
def propose(
    body: ProposalIn,
    request: Request,
    db: DB,
    settings: SettingsDep,
    vault: VaultDep,
    principal: Operator,
    idem: Idem,
) -> JSONResponse:
    if body.idempotency_key is not None and body.idempotency_key != idem.key:
        raise HubError(
            422,
            "idempotency_key_past_niet",
            "idempotency_key in het voorstel moet gelijk zijn aan de header Idempotency-Key.",
        )
    if body.actor is not None and (body.actor.type != "user" or body.actor.id != principal.name):
        # Een voorstel namens iemand anders bestaat hier niet: de actor is altijd de aangemelde gebruiker.
        raise HubError(422, "actor_past_niet", "actor in het voorstel past niet bij de aangemelde gebruiker.")

    def werk() -> tuple[int, dict[str, Any]]:
        return 201, service.stel_voor(
            db,
            settings,
            vault,
            principal,
            request_id=idem.key,
            action_id=body.action_id,
            target=body.target,
            parameters=body.parameters,
            reason=body.reason.strip(),
            risk_claim=body.risk_claim,
            evidence_ids=body.evidence_ids,
            expected_version=body.expected_version,
            expires_in_seconds=body.expires_in_seconds,
            trace_id=trace_id_of(request),
        )

    return _afhandelen(request, idem, werk)


@router.get("/actions", summary="Voorstellen en uitvoeringen (nieuwste eerst, cursor)")
def list_actions(
    db: DB,
    _: Viewer,
    limit: Limit = 50,
    cursor: Cursor = None,
    status: StatusFilter = "alle",
    action_id: str | None = Query(default=None, max_length=96),
) -> dict[str, Any]:
    now = utcnow()
    service.veeg(db, now)
    db.commit()
    offset = decode_cursor(cursor) or 0
    stmt = select(ActionRequest)
    if status == "open":
        stmt = stmt.where(ActionRequest.status.in_(service.OPEN))
    elif status != "alle":
        stmt = stmt.where(ActionRequest.status == status)
    if action_id:
        stmt = stmt.where(ActionRequest.action_id == action_id.strip().lower())
    rows = list(
        db.scalars(stmt.order_by(ActionRequest.aangemaakt_op.desc(), ActionRequest.id).offset(offset).limit(limit + 1))
    )
    return {
        "items": [service.weergave(db, r) for r in rows[:limit]],
        "next_cursor": encode_cursor(offset + limit) if len(rows) > limit else None,
        "noodstop": blok_mod.noodstop(db),
        "bijgewerkt_op": iso(now),
    }


@router.get("/actions/{request_id}", summary="Eén voorstel met preview, hashes, blokkades, goedkeuring en uitkomst")
def get_action(request_id: uuid.UUID, db: DB, _: Viewer) -> dict[str, Any]:
    service.veeg(db)
    db.commit()
    return service.weergave(db, service.haal(db, request_id))


# ------------------------------------------------------------------ goedkeuren, afwijzen, uitvoeren
@router.post(
    "/actions/{request_id}/approve",
    summary="R2/R3 goedkeuren voor precies deze preview (beheerder; 15 minuten, één keer bruikbaar)",
)
def approve(
    request_id: uuid.UUID,
    body: ApproveIn,
    request: Request,
    db: DB,
    settings: SettingsDep,
    vault: VaultDep,
    principal: Admin,
    idem: Idem,
) -> JSONResponse:
    def werk() -> tuple[int, dict[str, Any]]:
        return 200, service.keur_goed(
            db,
            settings,
            vault,
            principal,
            service.haal(db, request_id, vergrendel=True),
            preview_hash=body.preview_hash,
            resource_etag=body.resource_etag,
            policy_hash=body.policy_hash,
            trace_id=trace_id_of(request),
        )

    return _afhandelen(request, idem, werk)


@router.post("/actions/{request_id}/reject", summary="Voorstel afwijzen (beheerder); er wordt niets uitgevoerd")
def reject(
    request_id: uuid.UUID, body: RejectIn, request: Request, db: DB, principal: Admin, idem: Idem
) -> JSONResponse:
    def werk() -> tuple[int, dict[str, Any]]:
        return 200, service.wijs_af(
            db,
            principal,
            service.haal(db, request_id, vergrendel=True),
            reden=body.reden.strip(),
            trace_id=trace_id_of(request),
        )

    return _afhandelen(request, idem, werk)


@router.post(
    "/actions/{request_id}/execute",
    summary="Uitvoeren: alles opnieuw controleren, ondertekenen en naar de executor (R2/R3: alleen beheerder)",
)
def execute(
    request_id: uuid.UUID,
    request: Request,
    db: DB,
    settings: SettingsDep,
    vault: VaultDep,
    keyring: KeyRingDep,
    principal: Operator,
    idem: Idem,
) -> JSONResponse:
    def werk() -> tuple[int, dict[str, Any]]:
        return service.voer_uit(
            db,
            settings,
            vault,
            keyring,
            principal,
            service.haal(db, request_id, vergrendel=True),
            trace_id=trace_id_of(request),
        )

    return _afhandelen(request, idem, werk)


@router.post(
    "/actions/{request_id}/reconcile",
    summary="Onbekende uitkomst ophelderen met het journaal van de executor (alleen lezen; er wordt niets herhaald)",
)
def reconcile(
    request_id: uuid.UUID,
    request: Request,
    db: DB,
    settings: SettingsDep,
    keyring: KeyRingDep,
    principal: Operator,
    idem: Idem,
) -> JSONResponse:
    def werk() -> tuple[int, dict[str, Any]]:
        return service.haal_uitkomst_op(db, settings, keyring, principal, service.haal(db, request_id, vergrendel=True))

    return _afhandelen(request, idem, werk)
