"""Monitoringbronnen en healthchecks (B09-002): Uptime Kuma, Beszel, heartbeat van eigen diensten, status van de
periodieke taken.

- Bronnen beheert alleen een beheerder; API-key of wachtwoord gaat de vault in en komt nooit terug.
- ``POST /api/v1/monitoring/heartbeat`` is een **dienst**route (Bearer service-token, contract §4.4); een Hub-
  uitbreiding naast de connector-health van §6 (ADR-0016).
- Een test of poll vraagt echt bij de bron na en geeft het echte resultaat; nooit gesimuleerd succes.
"""

from __future__ import annotations

import re
import uuid
from datetime import timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from hub import audit
from hub.deps import (
    DB,
    Admin,
    Idem,
    Operator,
    ServiceP,
    SettingsDep,
    Viewer,
    get_keyring,
    get_vault,
)
from hub.errors import HubError
from hub.keys import KeyRing
from hub.models import CatalogApp, HealthObservation, MonitorSource, PeriodicTask, Service, VaultSecret
from hub.monitoring import heartbeat as hb
from hub.monitoring.health import MELDINGEN, Component, freshen
from hub.monitoring.periodic import TASKS, task_dict
from hub.monitoring.sources import poll_all, upsert_observation
from hub.outbound import OutboundError, validate_base_url
from hub.timeutil import iso, utcnow
from hub.vault import Vault, make_ref

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])
VaultDep = Annotated[Vault, Depends(get_vault)]
KeyringDep = Annotated[KeyRing, Depends(get_keyring)]

SLUG = r"^[a-z0-9-]{1,64}$"
SYSTEM_ID = r"^[a-z0-9]{1,32}$"
MELDING_BRON = {
    "api_key_geweigerd": "Uptime Kuma weigerde de API-key (verlopen of ingetrokken?). De monitors gelden als onbekend "
    "tot er een geldige key is ingevuld.",
    "api_key_ontbreekt": "Voor /metrics is een API-key nodig (Uptime Kuma → Instellingen → API-keys).",
    "niets_ingesteld": "Stel een API-key (voor /metrics) of minstens één statuspagina in.",
    "statuspagina_niet_gevonden": "De statuspagina bestaat niet of is niet gepubliceerd.",
    "inloggen_mislukt": "Beszel weigerde de gebruikersnaam of het wachtwoord.",
    "inloggegevens_ontbreken": "Vul de Beszel-gebruiker en het wachtwoord in.",
    "geen_leesrecht": "De Beszel-gebruiker mag de systemen niet lezen.",
    "nas_systeem_niet_gekoppeld": "Kies welk Beszel-systeem de NAS is (of vul D03 in voor automatische koppeling op "
    "host). Andere systemen, zoals de mini-pc, worden nooit gebruikt.",
    "geen_metingen": "Beszel heeft nog geen metingen van het NAS-systeem.",
    "niet_bereikbaar": "De bron is niet bereikbaar.",
    "tijdslimiet": "De bron reageerde niet op tijd.",
    "tls_fout": "Het HTTPS-certificaat van de bron wordt niet vertrouwd.",
    "redirect_niet_gevolgd": "De bron antwoordde met een doorverwijzing; die volgt de Hub nooit.",
    "antwoord_ongeldig": "De bron gaf een onverwacht antwoord.",
}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceIn(Strict):
    soort: Literal["uptime_kuma", "beszel"]
    naam: str = Field(min_length=1, max_length=64)
    basis_url: str = Field(min_length=8, max_length=512)
    api_key: str | None = Field(default=None, min_length=8, max_length=256, description="Uptime Kuma-API-key.")
    identiteit: str | None = Field(default=None, min_length=1, max_length=128, description="Beszel-gebruiker.")
    wachtwoord: str | None = Field(default=None, min_length=8, max_length=256, description="Beszel-wachtwoord.")
    status_paginas: list[Annotated[str, Field(pattern=SLUG)]] = Field(default_factory=list, max_length=10)
    metrics: bool = True
    nas_systeem: str | None = Field(default=None, pattern=SYSTEM_ID)
    ingeschakeld: bool = True

    @model_validator(mode="after")
    def _per_soort(self) -> SourceIn:
        if self.soort == "uptime_kuma":
            if self.identiteit or self.wachtwoord or self.nas_systeem:
                raise ValueError("identiteit, wachtwoord en nas_systeem horen bij Beszel")
            if not (self.metrics and self.api_key) and not self.status_paginas:
                raise ValueError("geef een API-key (voor /metrics) of minstens één statuspagina")
        else:
            if self.api_key or self.status_paginas:
                raise ValueError("api_key en status_paginas horen bij Uptime Kuma")
            if not (self.identiteit and self.wachtwoord):
                raise ValueError("Beszel vraagt een gebruiker (identiteit) en wachtwoord van een readonly-gebruiker")
        return self


class SourcePatch(Strict):
    naam: str | None = Field(default=None, min_length=1, max_length=64)
    basis_url: str | None = Field(default=None, min_length=8, max_length=512)
    api_key: str | None = Field(default=None, min_length=8, max_length=256)
    identiteit: str | None = Field(default=None, min_length=1, max_length=128)
    wachtwoord: str | None = Field(default=None, min_length=8, max_length=256)
    status_paginas: list[Annotated[str, Field(pattern=SLUG)]] | None = Field(default=None, max_length=10)
    metrics: bool | None = None
    nas_systeem: str | None = Field(default=None, pattern=SYSTEM_ID)
    nas_systeem_wissen: bool = False
    ingeschakeld: bool | None = None
    koppelingen: dict[str, str | None] | None = Field(
        default=None, description="Monitor-sleutel → app-id (uuid) of 'geen'; null verwijdert de handmatige keuze."
    )

    @field_validator("koppelingen")
    @classmethod
    def _links(cls, v: dict[str, str | None] | None) -> dict[str, str | None] | None:
        if v is None:
            return v
        if len(v) > 200:
            raise ValueError("hooguit 200 koppelingen per keer")
        for k, target in v.items():
            if not re.match(r"^(id|naam):.{1,195}$", k):
                raise ValueError("monitor-sleutel moet 'id:<n>' of 'naam:<naam>' zijn")
            if target not in (None, "geen"):
                uuid.UUID(str(target))
        return v


def _url(settings: Any, url: str) -> str:
    try:
        return validate_base_url(url, allow_loopback=settings.outbound_allow_loopback)
    except OutboundError as exc:
        raise HubError(
            422, "validation_error", "Ongeldig adres voor de bron.", {"reden": exc.reason, "detail": exc.detail}
        ) from None


def source_dict(db: Any, settings: Any, src: MonitorSource) -> dict[str, Any]:
    secret = db.scalar(select(VaultSecret).where(VaultSecret.ref == src.geheim_ref)) if src.geheim_ref else None
    now = utcnow()
    stale = src.laatste_ok is None or (now - src.laatste_ok).total_seconds() > settings.monitor_ttl_seconds
    return {
        "id": str(src.id),
        "soort": src.soort,
        "naam": src.naam,
        "basis_url": src.basis_url,
        "geheim": {
            "soort": "api_key" if src.soort == "uptime_kuma" else "wachtwoord",
            "ingesteld": secret is not None,
            "laatste4": secret.last4 if secret else None,
            "gewijzigd_op": iso(secret.updated_at) if secret else None,
        },
        "identiteit": src.identiteit,
        "opties": src.opties,
        "koppelingen": src.koppelingen,
        "ingeschakeld": src.ingeschakeld,
        "status": {
            "status": "unknown"
            if src.laatste_status is None or (stale and src.laatste_status == "ok")
            else ("ok" if src.laatste_status == "ok" else "fout"),
            "reden": src.laatste_reden,
            "melding": MELDING_BRON.get(src.laatste_reden or "", "") if src.laatste_reden else "",
            "laatste_poging": iso(src.laatste_poging),
            "laatste_ok": iso(src.laatste_ok),
            "verouderd": stale,
            "versie": src.laatste_versie,
        },
        "detail": src.laatste_detail,
        "versie": src.version,
    }


def observation_dict(row: HealthObservation, apps: dict[uuid.UUID, CatalogApp]) -> dict[str, Any]:
    c = freshen(Component("", row.bron_type, row.status, row.reason_code, row.observed_at), row.ttl_seconds, utcnow())
    app = apps.get(row.subject_app_id) if row.subject_app_id else None
    return {
        "bron_type": row.bron_type,
        "bron_id": row.bron_id,
        "sleutel": row.sleutel,
        "naam": row.naam,
        "status": c.status,
        "reason_code": c.reason_code,
        "melding": MELDINGEN.get(c.reason_code or "", "") if c.reason_code else "",
        "laatste_status": row.status,
        "observed_at": iso(row.observed_at),
        "verouderd": bool(c.extra.get("verouderd")),
        "ttl_seconden": row.ttl_seconds,
        "app": None if app is None else {"id": str(app.id), "naam": app.naam},
        "koppeling": row.koppeling,
        "details": row.details,
    }


@router.get("/sources", summary="Monitoringbronnen (Uptime Kuma, Beszel) met status, versie en reden")
def list_sources(db: DB, settings: SettingsDep, _: Operator) -> dict[str, Any]:
    rows = db.scalars(select(MonitorSource).order_by(MonitorSource.naam))
    return {"items": [source_dict(db, settings, s) for s in rows]}


@router.post("/sources", status_code=201, summary="Bron toevoegen (admin); geheim in de vault, nooit terug")
def create_source(
    body: SourceIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem, vault: VaultDep
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    sid = uuid.uuid4()
    ref = make_ref("monitoring", str(sid))
    secret = body.api_key if body.soort == "uptime_kuma" else body.wachtwoord
    opties: dict[str, Any] = (
        {"status_paginas": body.status_paginas, "metrics": body.metrics}
        if body.soort == "uptime_kuma"
        else {"nas_systeem": body.nas_systeem}
    )
    src = MonitorSource(
        id=sid,
        soort=body.soort,
        naam=body.naam,
        basis_url=_url(settings, body.basis_url),
        geheim_ref=ref if secret else None,
        identiteit=body.identiteit,
        opties=opties,
        koppelingen={},
        ingeschakeld=body.ingeschakeld,
        laatste_detail={},
        aangemaakt_door=principal.actor,
        bijgewerkt_door=principal.actor,
    )
    db.add(src)
    if secret:
        vault.put(db, ref, secret, actor=principal.actor)
    db.flush()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="monitoring.source.created",
        target_type="monitor_source",
        target_id=str(sid),
        details={"soort": body.soort, "naam": body.naam, "basis_url": src.basis_url},
    )
    return idem.save(201, source_dict(db, settings, src))


@router.get("/sources/{source_id}", summary="Bron met monitors/systemen en hun koppeling aan apps")
def get_source(source_id: uuid.UUID, db: DB, settings: SettingsDep, _: Operator) -> dict[str, Any]:
    src = db.get(MonitorSource, source_id)
    if src is None:
        raise HubError(404, "not_found", "Bron niet gevonden.")
    apps = {a.id: a for a in db.scalars(select(CatalogApp))}
    rows = db.scalars(
        select(HealthObservation).where(HealthObservation.bron_id == str(src.id)).order_by(HealthObservation.naam)
    )
    return {**source_dict(db, settings, src), "monitors": [observation_dict(r, apps) for r in rows]}


@router.patch("/sources/{source_id}", summary="Bron wijzigen (admin), inclusief handmatige koppeling monitor → app")
def update_source(
    source_id: uuid.UUID,
    body: SourcePatch,
    db: DB,
    settings: SettingsDep,
    principal: Admin,
    idem: Idem,
    vault: VaultDep,
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    src = db.get(MonitorSource, source_id)
    if src is None:
        raise HubError(404, "not_found", "Bron niet gevonden.")
    changed: list[str] = []
    if body.naam is not None:
        src.naam = body.naam
        changed.append("naam")
    if body.basis_url is not None:
        src.basis_url = _url(settings, body.basis_url)
        changed.append("basis_url")
    secret = body.api_key if src.soort == "uptime_kuma" else body.wachtwoord
    wrong = body.api_key if src.soort == "beszel" else body.wachtwoord
    if wrong is not None or (src.soort == "uptime_kuma" and (body.identiteit or body.nas_systeem)):
        raise HubError(422, "validation_error", "Dit veld hoort niet bij deze soort bron.")
    if secret is not None:
        src.geheim_ref = src.geheim_ref or make_ref("monitoring", str(src.id))
        vault.put(db, src.geheim_ref, secret, actor=principal.actor)
        changed.append("geheim")
    if body.identiteit is not None:
        src.identiteit = body.identiteit
        changed.append("identiteit")
    opts = dict(src.opties or {})
    if body.status_paginas is not None:
        opts["status_paginas"] = body.status_paginas
        changed.append("status_paginas")
    if body.metrics is not None:
        opts["metrics"] = body.metrics
        changed.append("metrics")
    if body.nas_systeem is not None:
        opts["nas_systeem"] = body.nas_systeem
        changed.append("nas_systeem")
    elif body.nas_systeem_wissen:
        opts["nas_systeem"] = None
        changed.append("nas_systeem")
    src.opties = opts
    if body.koppelingen is not None:
        links = dict(src.koppelingen or {})
        known = {str(a) for a in db.scalars(select(CatalogApp.id))}
        for k, target in body.koppelingen.items():
            if target is None:
                links.pop(k, None)
            elif target == "geen" or target in known:
                links[k] = target
            else:
                raise HubError(422, "validation_error", "Onbekende app in de koppeling.", {"app": target})
        src.koppelingen = links
        changed.append("koppelingen")
    if body.ingeschakeld is not None:
        src.ingeschakeld = body.ingeschakeld
        changed.append("ingeschakeld")
    if changed:
        src.version += 1
        src.bijgewerkt_door, src.bijgewerkt_op = principal.actor, utcnow()
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="monitoring.source.updated",
        target_type="monitor_source",
        target_id=str(src.id),
        details={"velden": changed},
    )
    db.flush()
    return idem.save(200, source_dict(db, settings, src))


@router.post("/sources/{source_id}/test", summary="Bron nu echt uitlezen (admin) en het echte resultaat tonen")
def test_source(
    source_id: uuid.UUID,
    db: DB,
    settings: SettingsDep,
    principal: Admin,
    idem: Idem,
    vault: VaultDep,
    keyring: KeyringDep,
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    src = db.get(MonitorSource, source_id)
    if src is None:
        raise HubError(404, "not_found", "Bron niet gevonden.")
    result = poll_all(db, settings, vault, keyring, only=src)["bronnen"].get(str(src.id), {})
    src = db.get(MonitorSource, source_id) or src
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="monitoring.source.tested",
        target_type="monitor_source",
        target_id=str(src.id),
        details={"resultaat": result},
    )
    db.flush()
    return idem.save(200, {"resultaat": result, "bron": source_dict(db, settings, src)})


@router.post("/poll", summary="Alle bronnen en eigen diensten nu uitlezen (operator); alleen-lezen")
def poll_now(
    db: DB, settings: SettingsDep, principal: Operator, idem: Idem, vault: VaultDep, keyring: KeyringDep
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    result = poll_all(db, settings, vault, keyring)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="monitoring.poll",
        target_type="monitoring",
        details={"bronnen": len(result["bronnen"]), "diensten": result.get("diensten")},
    )
    db.flush()
    return idem.save(200, result)


@router.get("/health", summary="Alle gezondheidswaarnemingen (Uptime Kuma, heartbeat, connector) met veroudering")
def list_observations(
    db: DB,
    _: Viewer,
    bron_type: Literal["uptime_kuma", "heartbeat", "connector"] | None = None,
    alleen_ongekoppeld: bool = Query(default=False, description="Alleen monitors zonder app."),
) -> dict[str, Any]:
    q = select(HealthObservation)
    if bron_type:
        q = q.where(HealthObservation.bron_type == bron_type)
    if alleen_ongekoppeld:
        q = q.where(HealthObservation.subject_app_id.is_(None), HealthObservation.bron_type == "uptime_kuma")
    apps = {a.id: a for a in db.scalars(select(CatalogApp))}
    rows = list(db.scalars(q.order_by(HealthObservation.bron_type, HealthObservation.naam).limit(1000)))
    return {"items": [observation_dict(r, apps) for r in rows], "observed_at": iso(utcnow())}


@router.post(
    "/heartbeat",
    status_code=202,
    summary="Heartbeat van een eigen dienst (Bearer service-token; dedupe op observed_at)",
    responses={429: {"description": "te vaak (minimaal 5 s tussen heartbeats)"}},
)
def heartbeat(body: hb.HeartbeatIn, db: DB, principal: ServiceP) -> JSONResponse:
    now = utcnow()
    if abs((body.observed_at - now).total_seconds()) > 300:
        raise HubError(422, "validation_error", "observed_at wijkt meer dan 5 minuten af van de klok van de Hub.")
    svc = db.get(Service, uuid.UUID(principal.id))
    if svc is None:
        raise HubError(401, "unauthorized", "Dienst onbekend.")
    row = db.scalars(
        select(HealthObservation).where(
            HealthObservation.bron_type == "heartbeat", HealthObservation.bron_id == str(svc.id)
        )
    ).first()
    if row is not None and row.observed_at == body.observed_at:
        return JSONResponse({"status": "duplicate", "beoordeling": {"status": row.status, "reden": row.reason_code}})
    if row is not None and row.updated_at is not None and (now - row.updated_at) < timedelta(seconds=5):
        raise HubError(429, "rate_limited", "Te veel heartbeats; minimaal 5 s ertussen.", headers={"Retry-After": "5"})
    status, reason = hb.judge(body, now)
    upsert_observation(
        db,
        bron_type="heartbeat",
        bron_id=str(svc.id),
        naam=svc.app_id,
        status=status,
        reason_code=reason,
        observed_at=body.observed_at,
        ttl_seconds=3 * body.verwacht_interval_s,
        details=hb.details(body),
        now=now,
    )
    db.commit()
    return JSONResponse({"status": "accepted", "beoordeling": {"status": status, "reden": reason}}, status_code=202)


@router.get("/status", summary="Periodieke taken (meten, alerts, meldingen, tijdreeksonderhoud) en bronnen")
def status(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    rows = {r.naam: r for r in db.scalars(select(PeriodicTask))}
    tasks = []
    for t in TASKS:
        row = rows.get(t.naam)
        tasks.append(
            task_dict(row, t.interval(settings))
            if row is not None
            else {"naam": t.naam, "interval_s": t.interval(settings), "status": "unknown", "laatst_klaar": None}
        )
    sources = [
        {"id": str(s.id), "soort": s.soort, "naam": s.naam, **source_dict(db, settings, s)["status"]}
        for s in db.scalars(select(MonitorSource).order_by(MonitorSource.naam))
    ]
    return {"taken": tasks, "bronnen": sources, "observed_at": iso(utcnow())}
