"""Gezondheid per catalogus-app: verzamel de componenten (TrueNAS-staat, Uptime Kuma, heartbeat, connector-health,
worker van de Hub) en beoordeel ze met ``hub.monitoring.health.evaluate``. Altijd op leestijd, zodat veroudering nooit
achterloopt."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from hub.catalog.profiles import BINNENKANT_HUB, profile_for
from hub.config import Settings
from hub.models import CatalogApp, HealthObservation, WorkerHeartbeat
from hub.monitoring.health import TRUENAS_STATE, Component, evaluate, freshen
from hub.timeutil import utcnow


def _parse(ts: str | None) -> datetime | None:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def truenas_component(row: CatalogApp, inv_state: dict[str, Any]) -> Component:
    if inv_state.get("status") == "ok" and row.aanwezig:
        status, reason = TRUENAS_STATE.get(str(row.runtime_staat or ""), ("unknown", "status_onbekend"))
        return Component(
            "truenas",
            "truenas.app.query",
            status,
            reason,
            _parse(inv_state.get("observed_at")),
            extra={"staat": row.runtime_staat},
        )
    return Component(
        "truenas",
        "truenas.app.query",
        "unknown",
        "inventaris_verouderd",
        row.laatst_gezien,
        extra={"staat": row.runtime_staat, "verouderd": True},
    )


def hub_worker_component(db: Session, settings: Settings, now: datetime) -> Component:
    """Binnenkant van de Hub zelf: de hartslag van de eigen worker (draait taken als inventaris en back-ups)."""
    hb = db.get(WorkerHeartbeat, "worker")
    grace = max(60.0, settings.worker_poll_seconds * 6)
    if hb is None:
        return Component("binnenkant", "hub_worker", "unknown", "binnenkant_ontbreekt", None)
    if (now - hb.beat_at).total_seconds() > grace:
        return Component(
            "binnenkant", "hub_worker", "degraded", "worker_staat_stil", hb.beat_at, extra={"grace_seconden": grace}
        )
    return Component("binnenkant", "hub_worker", "healthy", None, hb.beat_at)


def observation_components(db: Session, row: CatalogApp, now: datetime) -> list[Component]:
    """Waarnemingen van bronnen die aan deze app hangen: Uptime Kuma-monitors (``subject_app_id``) en
    heartbeat/connector-health van de gekoppelde eigen dienst (``bron_id`` = dienst-id)."""
    conds = [HealthObservation.subject_app_id == row.id]
    if row.service_id is not None:
        conds.append(
            (HealthObservation.bron_type.in_(("heartbeat", "connector")))
            & (HealthObservation.bron_id == str(row.service_id))
        )
    out: list[Component] = []
    for obs in db.scalars(select(HealthObservation).where(or_(*conds))):
        soort = "buitenkant" if obs.bron_type == "uptime_kuma" else "binnenkant"
        c = Component(
            soort,
            f"{obs.bron_type}:{obs.naam}" if obs.naam else obs.bron_type,
            obs.status,
            obs.reason_code,
            obs.observed_at,
            extra={k: v for k, v in (obs.details or {}).items() if k in _PUBLIC_DETAILS},
        )
        out.append(freshen(c, obs.ttl_seconds, now))
    return out


_PUBLIC_DETAILS = {"latency_ms", "monitor_type", "monitor_url", "uptime_24u", "checks", "worker", "bron_naam"}


def app_health(
    db: Session, settings: Settings, row: CatalogApp, inv_state: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    now = now or utcnow()
    prof = profile_for(row.app_id)
    comps = [truenas_component(row, inv_state)]
    if prof.binnenkant == BINNENKANT_HUB:
        comps.append(hub_worker_component(db, settings, now))
    comps.extend(observation_components(db, row, now))
    return evaluate(
        comps, aanwezig=row.aanwezig, binnenkant_vereist=prof.binnenkant_vereist, binnenkant_bron=prof.binnenkant
    )
