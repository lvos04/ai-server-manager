"""Bronnen pollen (B09-002): Uptime Kuma-monitors, Beszel (NAS-systeem) en connector-health van eigen diensten.

Alles alleen-lezen. Elke waarneming krijgt ``observed_at`` en een TTL; een bron die faalt laat haar waarnemingen
verouderen (→ ``unknown``) in plaats van de laatste status te herhalen. Credentials komen uit de vault en gaan nooit
naar logs of antwoorden.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.catalog.profiles import BINNENKANT_DIENST, profile_for
from hub.config import Settings
from hub.events.envelope import emit
from hub.inventory.store import kind_state
from hub.keys import KeyRing
from hub.models import CatalogApp, HealthObservation, MonitorSource, Service
from hub.monitoring import beszel, kuma, timeseries
from hub.monitoring.health import status_value
from hub.monitoring.timeseries import Sample
from hub.registry import nas_address, service_base_url
from hub.servicecalls import ServiceCallError, call
from hub.timeutil import iso, utcnow
from hub.truenas.connection import current_target
from hub.vault import Vault

log = logging.getLogger("hub.monitoring")
JOB_CHECKS = ("worker", "jobs", "job", "queue", "wachtrij", "taken")


def _obs(db: Session, bron_type: str, bron_id: str, sleutel: str = "") -> HealthObservation | None:
    return db.scalars(
        select(HealthObservation).where(
            HealthObservation.bron_type == bron_type,
            HealthObservation.bron_id == bron_id,
            HealthObservation.sleutel == sleutel,
        )
    ).first()


def upsert_observation(
    db: Session,
    *,
    bron_type: str,
    bron_id: str,
    sleutel: str = "",
    naam: str,
    status: str,
    reason_code: str | None,
    observed_at: datetime | None,
    ttl_seconds: int,
    details: dict[str, Any],
    subject_app_id: Any = None,
    koppeling: str | None = None,
    now: datetime,
) -> HealthObservation:
    row = _obs(db, bron_type, bron_id, sleutel)
    if row is None:
        row = HealthObservation(bron_type=bron_type, bron_id=bron_id, sleutel=sleutel, fouten_op_rij=0)
        db.add(row)
    row.naam = naam[:200]
    row.status, row.reason_code, row.observed_at = status, reason_code, observed_at
    row.ttl_seconds, row.details, row.updated_at = ttl_seconds, details, now
    row.subject_app_id, row.koppeling = subject_app_id, koppeling
    db.flush()
    return row


def _source_state(db: Session, src: MonitorSource, ok: bool, reason: str | None, now: datetime) -> None:
    """Status van de bron bijwerken; alleen bij een overgang (ok ↔ fout of een andere reden) een outbox-event."""
    before = (src.laatste_status, src.laatste_reden)
    src.laatste_status, src.laatste_reden = ("ok" if ok else "fout"), reason
    if ok:
        src.laatste_ok = now
    if before != (src.laatste_status, src.laatste_reden) and (before[0] is not None or not ok):
        emit(
            db,
            "monitoring.source.recovered" if ok else "monitoring.source.failed",
            "monitor_source",
            str(src.id),
            {"soort": src.soort, "naam": src.naam, "reden": reason, "vorige": before[1]},
        )


# ------------------------------------------------------------------ Uptime Kuma
def _app_endpoints(db: Session) -> dict[tuple[str, int], CatalogApp]:
    """(host, hostpoort) → app, met het NAS-adres uit D03 (zonder D03 geen automatische koppeling)."""
    host = nas_address(db)
    if not host:
        return {}
    out: dict[tuple[str, int], CatalogApp] = {}
    for app in db.scalars(select(CatalogApp).where(CatalogApp.aanwezig.is_(True))):
        for p in app.poorten or []:
            if p.get("host_poort") and p.get("protocol") == "tcp":
                out[(host.lower(), int(p["host_poort"]))] = app
    return out


def _monitor_endpoint(m: kuma.KumaMonitor) -> tuple[str, int] | None:
    if m.url:
        p = urlsplit(m.url)
        if p.hostname:
            port = p.port or (443 if p.scheme == "https" else 80)
            return p.hostname.lower(), port
    if m.hostname and m.port:
        return m.hostname.lower(), m.port
    return None


def link_monitor(
    m: kuma.KumaMonitor, src: MonitorSource, endpoints: dict[tuple[str, int], CatalogApp], apps: dict[str, CatalogApp]
) -> tuple[Any, str | None]:
    explicit = (src.koppelingen or {}).get(m.sleutel)
    if explicit == "geen":
        return None, "handmatig"
    if explicit and explicit in apps:
        return apps[explicit].id, "handmatig"
    ep = _monitor_endpoint(m)
    if ep is not None and ep in endpoints:
        return endpoints[ep].id, "automatisch"
    return None, None


def poll_kuma(db: Session, settings: Settings, vault: Vault, src: MonitorSource, now: datetime) -> dict[str, Any]:
    api_key = vault.get(db, src.geheim_ref) if src.geheim_ref else None
    opts = src.opties or {}
    res = kuma.fetch(
        src.basis_url,
        api_key,
        [str(s) for s in opts.get("status_paginas") or []],
        use_metrics=bool(opts.get("metrics", True)),
        policy=settings.outbound_policy(),
        now=now,
    )
    src.laatste_poging = now
    if not res.ok:
        _source_state(db, src, False, res.reden, now)
        src.laatste_detail = {**(src.laatste_detail or {}), "fouten": res.fouten}
        revoked = res.reden == "api_key_geweigerd"
        for row in db.scalars(
            select(HealthObservation).where(
                HealthObservation.bron_type == "uptime_kuma", HealthObservation.bron_id == str(src.id)
            )
        ):
            row.details = {**(row.details or {}), "bron_fout": res.reden}
            if revoked:  # fail-closed: een geweigerde key maakt de monitors direct onbekend (EX16)
                row.status, row.reason_code = "unknown", "bron_credential_geweigerd"
        db.flush()
        return {"status": "fout", "reden": res.reden}
    _source_state(db, src, True, None, now)
    src.laatste_versie = res.versie
    endpoints = _app_endpoints(db)
    apps = {str(a.id): a for a in db.scalars(select(CatalogApp))}
    seen: set[str] = set()
    samples: list[Sample] = []
    bron = f"uptime_kuma:{src.id}"
    linked = 0
    for m in res.monitors.values():
        seen.add(m.sleutel)
        app_id, how = link_monitor(m, src, endpoints, apps)
        linked += 1 if app_id else 0
        upsert_observation(
            db,
            bron_type="uptime_kuma",
            bron_id=str(src.id),
            sleutel=m.sleutel,
            naam=m.naam,
            status=m.status,
            reason_code=m.reason_code,
            observed_at=m.observed_at,
            ttl_seconds=settings.monitor_ttl_seconds,
            details={
                "latency_ms": m.latency_ms,
                "monitor_type": m.type,
                "monitor_url": m.url,
                "uptime_24u": m.uptime_24u,
                "cert_dagen": m.cert_dagen,
                "bron_naam": src.naam,
                "via": m.bronnen,
            },
            subject_app_id=app_id,
            koppeling=how,
            now=now,
        )
        oid = f"{src.id}:{m.sleutel}"[:128]
        labels = {"naam": m.naam, "app": str(app_id) if app_id else None}
        if m.observed_at is not None:
            v = status_value(m.status)
            if v is not None:
                samples.append(Sample("monitor", oid, "monitor.status", "status", bron, m.observed_at, v, labels))
            if m.latency_ms is not None:
                samples.append(
                    Sample("monitor", oid, "monitor.latentie", "ms", bron, m.observed_at, m.latency_ms, labels)
                )
    for row in db.scalars(
        select(HealthObservation).where(
            HealthObservation.bron_type == "uptime_kuma", HealthObservation.bron_id == str(src.id)
        )
    ):
        if row.sleutel not in seen:
            db.delete(row)  # monitor bestaat niet meer in Uptime Kuma
    rec = timeseries.record(db, settings, samples, now=now)
    src.laatste_detail = {**res.summary(), "gekoppeld": linked, "metingen": rec.as_dict()}
    db.flush()
    return {"status": "ok", "monitors": len(res.monitors), "gekoppeld": linked}


# ------------------------------------------------------------------ Beszel
def _gpus(db: Session, settings: Settings) -> list[dict[str, Any]]:
    """GPU-identiteiten (PCI-slot) uit de inventaris; de laatst bekende volstaat (identiteit verandert niet)."""
    target = current_target(db)
    st = kind_state(db, "gpus", target=target.url if target else None, ttl_seconds=settings.inventory_ttl_seconds)
    return [g for g in st.get("data") or [] if isinstance(g, dict)]


def poll_beszel(db: Session, settings: Settings, vault: Vault, src: MonitorSource, now: datetime) -> dict[str, Any]:
    password = vault.get(db, src.geheim_ref) if src.geheim_ref else None
    src.laatste_poging = now
    if not password or not src.identiteit:
        _source_state(db, src, False, "inloggegevens_ontbreken", now)
        db.flush()
        return {"status": "fout", "reden": "inloggegevens_ontbreken"}
    nas_system = (src.opties or {}).get("nas_systeem")
    res = beszel.fetch(
        src.basis_url,
        src.identiteit,
        password,
        nas_system=str(nas_system) if nas_system else None,
        nas_address=nas_address(db),
        gpus=_gpus(db, settings),
        bron=f"beszel:{src.id}",
        policy=settings.outbound_policy(),
    )
    detail: dict[str, Any] = {
        "systemen": res.systemen,
        "nas": {**res.nas, "observed_at": iso(res.nas.get("observed_at"))} if res.nas else None,
        "gpu_niet_toegewezen": res.gpu_niet_toegewezen,
    }
    if res.versie:
        src.laatste_versie = res.versie
    if not res.ok or res.nas is None or res.reden:
        _source_state(db, src, False, res.reden or "fout", now)
        src.laatste_detail = {**(src.laatste_detail or {}), **({} if not res.ok else detail)}
        db.flush()
        return {"status": "fout", "reden": src.laatste_reden}
    rec = timeseries.record(db, settings, res.samples, now=now)
    detail["metingen"] = rec.as_dict()
    _source_state(db, src, True, None, now)
    src.laatste_detail = detail
    db.flush()
    return {"status": "ok", "metingen": rec.opgeslagen, "gpu_niet_toegewezen": len(res.gpu_niet_toegewezen)}


# ------------------------------------------------------------------ connector-health van eigen diensten (§6)
def judge_connector_health(body: Any, now: datetime) -> tuple[str, str | None, datetime, dict[str, Any]]:
    """Antwoord van ``GET /connector/v1/health`` → (status, reden, observed_at, details). Een dienst die zelf
    'healthy' zegt maar een worker/jobs-controle heeft die faalt, is ``degraded`` (``jobs_staan_stil``)."""
    if not isinstance(body, dict) or body.get("status") not in ("healthy", "degraded", "down", "unknown"):
        return "unknown", "antwoord_ongeldig", now, {}
    status = str(body["status"])
    reason = str(body.get("reason_code"))[:64] if body.get("reason_code") else None
    observed = now
    raw = body.get("observed_at")
    if isinstance(raw, str):
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if ts.tzinfo is not None and abs((ts - now).total_seconds()) <= 300:
                observed = ts
        except ValueError:
            pass
    checks = [c for c in body.get("checks") or [] if isinstance(c, dict)][:20]
    clean: list[dict[str, Any]] = [
        {
            "name": str(c.get("name") or "")[:64],
            "status": str(c.get("status") or "")[:16],
            "observed_at": c.get("observed_at") if isinstance(c.get("observed_at"), str) else None,
        }
        for c in checks
    ]
    stalled = [
        c for c in clean if any(k in c["name"].lower() for k in JOB_CHECKS) and c["status"] in ("down", "degraded")
    ]
    if status == "healthy" and stalled:
        status, reason = "degraded", "jobs_staan_stil"
    return status, reason, observed, {"checks": clean}


def _fail(row: HealthObservation | None, threshold: int) -> tuple[str, str, int]:
    fails = (row.fouten_op_rij if row is not None else 0) + 1
    if fails >= threshold:
        return "down", "dienst_onbereikbaar", fails
    return "unknown", "eerste_fout_grace", fails


def poll_connectors(db: Session, settings: Settings, keyring: KeyRing | None, now: datetime) -> dict[str, Any]:
    stats = {"diensten": 0, "healthy": 0, "niet_gezond": 0}
    ttl = settings.monitoring_interval_seconds * 3
    for svc in db.scalars(select(Service).where(Service.status == "active")):
        if profile_for(svc.app_id).binnenkant != BINNENKANT_DIENST:
            continue
        stats["diensten"] += 1
        row = _obs(db, "connector", str(svc.id))
        base, why = service_base_url(db, settings, svc)

        def save(
            status: str, reason: str | None, observed: datetime, details: dict[str, Any], svc: Service = svc
        ) -> None:
            upsert_observation(
                db,
                bron_type="connector",
                bron_id=str(svc.id),
                naam=svc.app_id,
                status=status,
                reason_code=reason,
                observed_at=observed,
                ttl_seconds=ttl,
                details=details,
                now=now,
            )

        if base is None or keyring is None:
            save("unknown", "dienst_adres_onbekend", now, {"reden": why})
            stats["niet_gezond"] += 1
            continue
        bearer, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
        fails = 0
        status: str
        reason: str | None
        try:
            res = call(
                base,
                "GET",
                "/connector/v1/health",
                bearer=bearer,
                connect_timeout=settings.service_call_connect_timeout,
                read_timeout=settings.service_call_read_timeout,
            )
        except ServiceCallError as exc:
            status, reason, fails = _fail(row, settings.connector_fail_threshold)
            save(status, reason, now, {"fout": exc.reason})
        else:
            details: dict[str, Any]
            if res.status in (401, 403):
                status, reason, observed, details = "unknown", "dienst_weigerde", now, {"http": res.status}
            elif res.status == 404:
                status, reason, observed, details = "unknown", "capability_unavailable", now, {"http": 404}
            elif res.body is not None and res.status in (200, 503):
                status, reason, observed, details = judge_connector_health(res.body, now)
            else:
                status, reason, fails = _fail(row, settings.connector_fail_threshold)
                observed, details = now, {"http": res.status}
            save(status, reason, observed, details)
        new = _obs(db, "connector", str(svc.id))
        if new is not None:
            new.fouten_op_rij = fails
        stats["healthy" if status == "healthy" else "niet_gezond"] += 1
    db.flush()
    return stats


# ------------------------------------------------------------------ alles samen
def poll_all(
    db: Session,
    settings: Settings,
    vault: Vault,
    keyring: KeyRing | None,
    *,
    now: datetime | None = None,
    only: MonitorSource | None = None,
) -> dict[str, Any]:
    now = now or utcnow()
    out: dict[str, Any] = {"bronnen": {}}
    sources = (
        [only]
        if only is not None
        else list(db.scalars(select(MonitorSource).where(MonitorSource.ingeschakeld.is_(True))))
    )
    for src in sources:
        try:
            if src.soort == "uptime_kuma":
                out["bronnen"][str(src.id)] = poll_kuma(db, settings, vault, src, now)
            elif src.soort == "beszel":
                out["bronnen"][str(src.id)] = poll_beszel(db, settings, vault, src, now)
            db.commit()
        except Exception as exc:
            db.rollback()
            log.exception("bron %s pollen mislukt", src.id)
            out["bronnen"][str(src.id)] = {"status": "fout", "reden": type(exc).__name__}
    if only is None:
        out["diensten"] = poll_connectors(db, settings, keyring, now)
    return out
