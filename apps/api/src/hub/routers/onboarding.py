"""Onboarding-wizard-API (B01-001, D01–D18), gates en de alleen-lezen TrueNAS-koppeling."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import audit
from hub.backup.selfbackup import latest_verified
from hub.config import Settings
from hub.deps import DB, Admin, Idem, Operator, SettingsDep, Viewer, get_vault
from hub.errors import HubError
from hub.events.envelope import emit
from hub.inventory.store import kind_state
from hub.models import Decision, Service
from hub.onboarding import gates as gates_mod
from hub.onboarding import service
from hub.onboarding.catalog import BY_ID, DECISIONS
from hub.registry import EXECUTOR_APP_ID
from hub.timeutil import iso, utcnow
from hub.truenas.client import display_fingerprint, fetch_server_fingerprint, normalize_fingerprint
from hub.truenas.connection import API_KEY_REF, connection_row, current_target, record_test, run_collect
from hub.truenas.messages import advice, message
from hub.vault import Vault, last4

router = APIRouter(prefix="/api/v1", tags=["onboarding en gates"])
DecisionId = Annotated[str, Path(pattern=r"^D(0[1-9]|1[0-8])$")]
VaultDep = Annotated[Vault, Depends(get_vault)]


class ValueIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    waarde: dict[str, Any]


class StatusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["Open", "Geblokkeerd", "N.v.t."]
    reden: str = Field(default="", max_length=1000)


class EvidenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    soort: Literal["handmatige_test", "meting_extern", "document", "hersteltest", "screenshot"]
    omschrijving: str = Field(min_length=10, max_length=2000)
    referentie: str = Field(default="", max_length=512)
    resultaat: Literal["geslaagd", "mislukt"]
    uitgevoerd_op: date


class ApiKeyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: str = Field(min_length=16, max_length=512)


class TrustIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fingerprint_sha256: str = Field(min_length=64, max_length=128)


def _get(db: Session, did: str) -> Decision:
    service.seed(db)
    row = db.get(Decision, did)
    if row is None:
        raise HubError(404, "not_found", "Besluit niet gevonden.")
    return row


def _etag(row: Decision) -> str:
    return f'W/"{row.id}-{row.version}"'


def _check_if_match(row: Decision, if_match: str | None) -> None:
    if if_match and if_match.strip() not in (_etag(row), "*"):
        raise HubError(
            412,
            "precondition_failed",
            "Het besluit is intussen gewijzigd; laad het opnieuw.",
            {"huidige_etag": _etag(row)},
        )


def _raise(exc: service.DecisionError) -> HubError:
    return HubError(exc.status, exc.code, exc.message, exc.details)


def _changed(db: Session, row: Decision, actor: str, action: str, details: dict[str, Any] | None = None) -> None:
    audit.record(
        db,
        actor_type="user",
        actor_id=actor,
        action=action,
        target_type="decision",
        target_id=row.id,
        details={"status": row.status, "version": row.version, **(details or {})},
    )
    emit(db, "onboarding.decision.changed", "decision", row.id, {"status": row.status, "version": row.version})


@router.get("/decisions", summary="Alle besluiten D01–D18 met status")
def list_decisions(db: DB, _: Viewer) -> dict[str, Any]:
    service.seed(db)
    db.commit()
    rows = {r.id: r for r in db.scalars(select(Decision))}
    items = [service.to_dict(rows[d.id]) for d in DECISIONS]
    counts: dict[str, int] = {}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    return {"items": items, "telling": counts}


@router.get("/decisions/{decision_id}", summary="Eén besluit, met JSON-schema van de waarde")
def get_decision(decision_id: DecisionId, db: DB, _: Viewer) -> JSONResponse:
    row = _get(db, decision_id)
    db.commit()
    return JSONResponse(service.to_dict(row, with_schema=True), headers={"ETag": _etag(row)})


@router.put("/decisions/{decision_id}/waarde", summary="Waarde invullen (gevalideerd) → Ingevuld")
def put_value(
    decision_id: DecisionId,
    body: ValueIn,
    db: DB,
    principal: Admin,
    idem: Idem,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = _get(db, decision_id)
    _check_if_match(row, if_match)
    try:
        service.set_value(row, body.waarde, principal.name)
    except ValidationError as exc:
        fouten = [{"veld": ".".join(str(p) for p in e["loc"]), "fout": e["msg"]} for e in exc.errors()]
        raise HubError(
            422, "validation_error", "De waarde voldoet niet aan het schema van dit besluit.", {"fouten": fouten}
        ) from exc
    except service.DecisionError as exc:
        raise _raise(exc) from exc
    _changed(db, row, principal.name, "decision.value_set")
    return idem.save(200, service.to_dict(row))


@router.post("/decisions/{decision_id}/status", summary="Open / Geblokkeerd / N.v.t. (met reden)")
def post_status(
    decision_id: DecisionId,
    body: StatusIn,
    db: DB,
    principal: Admin,
    idem: Idem,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = _get(db, decision_id)
    _check_if_match(row, if_match)
    try:
        service.set_status(row, body.status, body.reden, principal.name)
    except service.DecisionError as exc:
        raise _raise(exc) from exc
    _changed(db, row, principal.name, "decision.status_set", {"reden": body.reden})
    return idem.save(200, service.to_dict(row))


@router.post("/decisions/{decision_id}/bewijs", summary="Expliciet bewijsrecord vastleggen (geslaagd → Getest)")
def post_evidence(decision_id: DecisionId, body: EvidenceIn, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = _get(db, decision_id)
    try:
        record = service.add_evidence(db, row, body.model_dump(), principal.name)
    except service.DecisionError as exc:
        raise _raise(exc) from exc
    _changed(
        db, row, principal.name, "decision.evidence_added", {"bewijs_id": record["id"], "resultaat": body.resultaat}
    )
    return idem.save(200, service.to_dict(row))


@router.post("/decisions/{decision_id}/meting", summary="Meten via TrueNAS-readback (D01, D02, D03, D06, D07)")
async def post_measure(
    decision_id: DecisionId, db: DB, settings: SettingsDep, vault: VaultDep, principal: Operator, idem: Idem
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = _get(db, decision_id)
    if not BY_ID[decision_id].meetbaar:
        raise HubError(422, "not_measurable", f"{decision_id} is niet via TrueNAS meetbaar; leg een bewijsrecord vast.")
    try:
        m = await service.measure(db, vault, settings, row, principal.name)
    except service.DecisionError as exc:
        raise _raise(exc) from exc
    _changed(db, row, principal.name, "decision.measured", {"meting": m.status, "reason_code": m.reason_code})
    body = {
        "besluit": service.to_dict(row),
        "meting": {
            "status": m.status,
            "reason_code": m.reason_code,
            "melding": m.melding,
            "advies": advice(m.reason_code),
            "details": m.details,
            "run_id": m.run_id,
        },
    }
    return idem.save(200, body)


# ------------------------------------------------------------------ gates
def gate_inputs(db: Session, settings: Settings) -> gates_mod.GateInputs:
    service.seed(db)
    decisions = {r.id: (r.status, r.waarde) for r in db.scalars(select(Decision))}
    target = current_target(db)
    b = latest_verified(db)
    return gates_mod.GateInputs(
        decisions=decisions,
        pools_state=kind_state(
            db, "pools", target=target.url if target else None, ttl_seconds=settings.inventory_max_age_seconds
        ),
        eigen_backup={"finished_at": b.finished_at, "sha256": b.sha256, "id": str(b.id)}
        if b and b.finished_at
        else None,
        eigen_backup_max_age_seconds=settings.self_backup_interval_seconds + 2 * 3600,
        # Gekoppeld = een actieve registratie van de executor (koppeling afgerond op zijn eigen statuspagina, §3.9).
        executor_gekoppeld=db.scalars(
            select(Service.id).where(Service.app_id == EXECUTOR_APP_ID, Service.status == "active")
        ).first()
        is not None,
    )


@router.get("/gates", summary="Wat mag nu? Afgeleid uit besluiten + gemeten toestand")
def get_gates(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    items = gates_mod.evaluate(gate_inputs(db, settings))
    db.commit()
    return {"items": items, "toelichting": "Onbekend telt nooit als groen; gates kunnen niet worden weggeklikt."}


@router.get("/gates/{gate_id}", summary="Eén gate met redenen")
def get_gate(gate_id: str, db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    for g in gates_mod.evaluate(gate_inputs(db, settings)):
        if g["id"] == gate_id:
            return g
    raise HubError(404, "not_found", "Onbekende gate.")


# ------------------------------------------------------------------ TrueNAS-koppeling (alleen-lezen)
def _conn_dict(db: Session, vault: Vault) -> dict[str, Any]:
    row = connection_row(db)
    target = current_target(db)
    key_row_last4 = None
    from hub.models import VaultSecret

    vs = db.scalars(select(VaultSecret).where(VaultSecret.ref == API_KEY_REF)).first()
    if vs is not None:
        key_row_last4 = vs.last4
    pinned_valid = bool(target and row.pinned_fingerprint and row.pinned_for_url == target.url)
    return {
        "nas_url": target.url if target else None,
        "nas_adres_bron": "D03" if target else None,
        "api_key": {
            "ingesteld": vs is not None,
            "laatste4": key_row_last4,
            "ingesteld_op": iso(row.api_key_set_at),
            "ingesteld_door": row.api_key_set_by,
            "vault_ref": API_KEY_REF if vs else None,
        },
        "tls": {
            "modus": "vingerafdruk_bevestigd" if pinned_valid else "systeem_ca",
            "vingerafdruk": display_fingerprint(row.pinned_fingerprint)
            if pinned_valid and row.pinned_fingerprint
            else None,
            "bevestigd_door": row.pinned_by if pinned_valid else None,
            "bevestigd_op": iso(row.pinned_at) if pinned_valid else None,
        },
        "laatste_test": {
            "op": iso(row.last_test_at),
            "url": row.last_test_url,
            "status": row.last_test_status,
            "reason_code": row.last_test_reason,
            "melding": message(row.last_test_reason),
            "advies": advice(row.last_test_reason),
            "details": row.last_test_detail,
        }
        if row.last_test_at
        else None,
        "alleen_lezen": True,
    }


@router.get("/truenas", summary="Status van de TrueNAS-koppeling (nooit de key zelf)")
def get_truenas(db: DB, vault: VaultDep, _: Viewer) -> dict[str, Any]:
    out = _conn_dict(db, vault)
    db.commit()
    return out


@router.put("/truenas/api-key", summary="Alleen-lezen-API-key instellen (versleuteld in de vault)")
def put_api_key(body: ApiKeyIn, db: DB, vault: VaultDep, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    vault.put(db, API_KEY_REF, body.api_key.strip(), actor=principal.name)
    row = connection_row(db)
    row.api_key_set_at, row.api_key_set_by = utcnow(), principal.name
    row.last_test_at = None
    row.last_test_status = row.last_test_reason = None
    row.last_test_detail = {}
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="truenas.api_key_set",
        target_type="vault",
        target_id=API_KEY_REF,
        details={"laatste4": last4(body.api_key.strip())},
    )
    db.flush()
    return idem.save(200, _conn_dict(db, vault))


@router.post("/truenas/test", summary="Verbinding testen: TLS, aanmelden, rechten, versie, capability-map")
async def test_truenas(db: DB, settings: SettingsDep, vault: VaultDep, principal: Operator, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    res = await run_collect(db, vault, settings, ("system",))
    row = connection_row(db)
    record_test(row, res)
    sysk = res.kind("system")
    body = {
        "verbonden": res.status == "ok",
        "status": "ok" if res.status == "ok" else "unknown",
        "reason_code": res.reason_code,
        "melding": message(res.reason_code) if res.reason_code else "Verbonden en aangemeld met een alleen-lezen-key.",
        "advies": advice(res.reason_code),
        "nas_url": res.target_url or None,
        "nas_versie": res.nas_version,
        "key_scope": res.key_scope,
        "tls_modus": res.tls_mode,
        "capabilities": res.capabilities.as_dict() if res.capabilities else None,
        "capability_fout": res.capability_error,
        "details": {k: v for k, v in res.error_details.items() if k != "detail"}
        | ({"detail": res.error_details["detail"]} if "detail" in res.error_details else {}),
        "system": sysk.data if sysk and sysk.status == "ok" else None,
        "getest_op": iso(utcnow()),
    }
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="truenas.tested",
        target_type="truenas",
        target_id=res.target_url,
        details={"status": body["status"], "reason_code": res.reason_code},
    )
    emit(
        db,
        "truenas.connection.tested",
        "truenas",
        "primary",
        {"status": body["status"], "reason_code": res.reason_code},
    )
    return idem.save(200, body)


@router.post("/truenas/tls/trust", summary="Zelfondertekend certificaat vertrouwen na vingerafdruk-bevestiging")
async def trust_tls(body: TrustIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    target = current_target(db)
    if target is None:
        raise HubError(409, "not_configured", "Vul eerst het NAS-adres (D03) in.")
    try:
        confirmed = normalize_fingerprint(body.fingerprint_sha256)
    except ValueError as exc:
        raise HubError(422, "invalid_fingerprint", str(exc)) from exc
    presented = await fetch_server_fingerprint(target.url, settings.truenas_connect_timeout)
    if presented is None:
        raise HubError(
            502, "unreachable", "Kon het certificaat van de NAS niet ophalen.", {"reason_code": "unreachable"}
        )
    if presented != confirmed:
        raise HubError(
            409,
            "fingerprint_mismatch",
            "De bevestigde vingerafdruk komt niet overeen met wat de NAS nu aanbiedt; niets vertrouwd.",
            {"aangeboden": display_fingerprint(presented)},
        )
    row = connection_row(db)
    row.pinned_fingerprint, row.pinned_for_url = confirmed, target.url
    row.pinned_by, row.pinned_at, row.updated_at = principal.name, utcnow(), utcnow()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="truenas.tls_trusted",
        target_type="truenas",
        target_id=target.url,
        details={"vingerafdruk": display_fingerprint(confirmed)},
    )
    return idem.save(200, {"vertrouwd": True, "url": target.url, "vingerafdruk": display_fingerprint(confirmed)})


@router.post("/truenas/tls/untrust", summary="Bevestigde vingerafdruk intrekken")
def untrust_tls(db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    row = connection_row(db)
    row.pinned_fingerprint = row.pinned_for_url = row.pinned_by = None
    row.pinned_at, row.updated_at = None, utcnow()
    audit.record(db, actor_type="user", actor_id=principal.name, action="truenas.tls_untrusted", target_type="truenas")
    return idem.save(200, {"vertrouwd": False})
