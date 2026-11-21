"""Catalogusinstallatie via een eigen plannerplan (contract 1.3 §8.1/§8.2; ADR-0032 deel D; S-P2-050d).

Alleen gebruikerssessies: een dienst-token (ook dat van de planner) maakt geen plan, voorstel of stapresultaat. Het
voorstel loopt daarna langs de gewone actieweg (goedkeuring en uitvoering onder ``/api/v1/actions``).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from hub import audit
from hub.catalog import plannen
from hub.deps import DB, Idem, Operator, SettingsDep, Viewer, get_keyring, get_vault
from hub.errors import trace_id_of
from hub.keys import KeyRing
from hub.routers.actions import _afhandelen
from hub.vault import Vault

router = APIRouter(prefix="/api/v1/catalog/plans", tags=["catalogusinstallatie"])
VaultDep = Annotated[Vault, Depends(get_vault)]
KeyRingDep = Annotated[KeyRing, Depends(get_keyring)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DoelIn(Strict):
    truenas_version: str = Field(min_length=1, max_length=32)
    ix_app_version: str = Field(min_length=1, max_length=32)


class InstallPlanIn(Strict):
    app_id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$", description="Vaste catalogus-app_id.")
    version_id: uuid.UUID = Field(description="ID van de gekozen versie bij de appstore.")
    app_name: str = Field(pattern=r"^[a-z]([a-z0-9-]{0,38}[a-z0-9])?$", description="Runtime-appnaam op de NAS.")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Invulling van de manifestparameters.")
    doel: DoelIn


def _audit(db: Any, principal: Any, action: str, plan: dict[str, Any]) -> None:
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action=action,
        target_type="catalog_plan",
        target_id=plan["plan_id"],
        details={k: plan[k] for k in ("app_id", "app_name", "step_id", "status", "request_id")},
    )


@router.post("/install", status_code=201, summary="Installatieplan maken bij de planner na eigen bronverificatie")
def maak(
    body: InstallPlanIn,
    request: Request,
    db: DB,
    settings: SettingsDep,
    keyring: KeyRingDep,
    principal: Operator,
    idem: Idem,
) -> JSONResponse:
    def werk() -> tuple[int, dict[str, Any]]:
        plan = plannen.maak_plan(
            db,
            settings,
            keyring,
            principal,
            app_id=body.app_id,
            version_id=str(body.version_id),
            app_name=body.app_name,
            parameters=body.parameters,
            doel=body.doel.model_dump(),
        )
        _audit(db, principal, "catalog.plan.created", plan)
        return 201, plan

    return _afhandelen(request, idem, werk)


@router.get("/{plan_id}", summary="Eén eigen plan met status, registratie en open controles")
def toon(plan_id: uuid.UUID, db: DB, _: Viewer) -> dict[str, Any]:
    return plannen.plan_dict(plannen.haal_plan(db, plan_id))


@router.post(
    "/{plan_id}/steps/{step_id}/propose",
    status_code=201,
    summary="Actievoorstel maken voor de vrijgegeven installatiestap (eigen plan, na hercontrole)",
)
def stel_voor(
    plan_id: uuid.UUID,
    step_id: Annotated[str, Path(pattern=r"^[a-z][a-z0-9-]{0,63}$")],
    request: Request,
    db: DB,
    settings: SettingsDep,
    vault: VaultDep,
    keyring: KeyRingDep,
    principal: Operator,
    idem: Idem,
) -> JSONResponse:
    def werk() -> tuple[int, dict[str, Any]]:
        plan = plannen.haal_plan(db, plan_id, vergrendel=True)
        uit = plannen.stel_stap_voor(
            db,
            settings,
            vault,
            keyring,
            principal,
            plan,
            step_id=step_id,
            request_id=idem.key,
            trace_id=trace_id_of(request),
        )
        _audit(db, principal, "catalog.plan.proposed", plannen.plan_dict(plan))
        return 201, uit

    return _afhandelen(request, idem, werk)
