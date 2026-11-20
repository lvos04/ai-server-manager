"""Gezondheid per catalogus-app: verzamel de componenten (TrueNAS-staat, Uptime Kuma, heartbeat, connector-health,
worker van de Hub) en beoordeel ze met ``hub.monitoring.health.evaluate``. Altijd op leestijd, zodat veroudering nooit
achterloopt."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from hub.adapters.binding import binding_is_current, published_ports
from hub.adapters.health import stored_health
from hub.catalog.identity import same_destination
from hub.catalog.profiles import BINNENKANT_HUB, BINNENKANT_P3, profile_for
from hub.config import Settings
from hub.models import AdapterLink, CatalogApp, HealthObservation, WorkerHeartbeat
from hub.monitoring.health import TRUENAS_STATE, Component, evaluate, freshen
from hub.timeutil import utcnow
from hub.truenas.connection import current_target


def _source_time(raw: Any) -> datetime | None:
    try:
        deadline = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    return deadline if deadline.tzinfo is not None else None


def truenas_component(row: CatalogApp, inv: dict[str, Any], now: datetime) -> Component:
    unknown = Component("truenas", "truenas.app.query", "unknown", "inventaris_verouderd", None)
    if not isinstance(inv.get("data"), list):
        return unknown
    source = (inv.get("bron") or {}).get("nas")
    matches = inv["per_runtime_id"].get(row.runtime_id, [])
    if not matches:
        unknown.reason_code = "niet_meer_in_inventaris"
        return unknown
    if (
        not source
        or source != (row.bron or {}).get("nas")
        or len(matches) != 1
        or matches[0].get("herkend_als") != row.app_id
    ):
        unknown.reason_code = "doelbinding"
        return unknown
    try:
        observed = datetime.fromisoformat(inv["observed_at"])
    except (TypeError, ValueError, KeyError):
        unknown.reason_code = "meettijd_onbekend"
        return unknown
    app = matches[0]
    state = app.get("staat")
    status, reason = TRUENAS_STATE.get(str(state), ("unknown", "status_onbekend"))
    if observed.tzinfo is None or observed > now:
        unknown.reason_code = "meettijd_onbekend"
        return unknown
    c = Component("truenas", unknown.bron, status, reason, observed, extra={"staat": state})
    if inv["status"] != "ok":
        return c.last_known("inventaris_verouderd")
    deadline = _source_time(inv.get("geldig_tot"))
    if deadline is None or deadline < now:
        return c.last_known("meting_verouderd")
    c.geldig_tot = deadline
    if not row.aanwezig or not same_destination(row.poorten, row.portals, app):
        return c.last_known("doelbinding")
    return c


def hub_worker_component(db: Session, settings: Settings, now: datetime) -> Component:
    """Binnenkant van de Hub zelf: de hartslag van de eigen worker (draait taken als inventaris en back-ups)."""
    hb = db.get(WorkerHeartbeat, "worker")
    grace = max(60.0, settings.worker_poll_seconds * 6)
    if hb is None:
        return Component("binnenkant", "hub_worker", "unknown", "binnenkant_ontbreekt", None)
    if (now - hb.beat_at).total_seconds() > grace:
        return Component(
            "binnenkant",
            "hub_worker",
            "degraded",
            "worker_staat_stil",
            hb.beat_at,
            extra={"grace_seconden": grace},
            bevestigd_op=hb.beat_at,
        )
    return freshen(
        Component("binnenkant", "hub_worker", "healthy", None, hb.beat_at, bevestigd_op=hb.beat_at), grace, now
    )


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
        details = obs.details or {}
        confirmation = (
            obs.observed_at
            if obs.status == "healthy" and not details.get("bron_fout")
            else _source_time(details.get("bevestigd_op"))
        )
        c = Component(
            soort,
            f"{obs.bron_type}:{obs.naam}" if obs.naam else obs.bron_type,
            obs.status,
            obs.reason_code,
            obs.observed_at,
            extra={k: v for k, v in details.items() if k in _PUBLIC_DETAILS},
            bevestigd_op=confirmation,
        )
        c = freshen(c, obs.ttl_seconds, now)
        if obs.bron_type == "connector" and c.status != "unknown" and (c.status == "healthy" or "checks" in details):
            source_deadline = _source_time(details.get("geldig_tot"))
            # Bij oude metingen is onbekend hoeveel controles vóór de beoordeling zijn afgekapt.
            if (
                type(details.get("aantal_controles")) is not int
                or (source_deadline is None and c.status == "healthy")
                or (source_deadline is not None and source_deadline < now)
            ):
                c = c.last_known("meting_verouderd")
            elif source_deadline is not None and c.geldig_tot is not None:
                c.geldig_tot = min(c.geldig_tot, source_deadline)
        if details.get("bron_fout") and c.status != "unknown":
            c = c.last_known("bron_onbereikbaar")
        out.append(c)
    return out


_PUBLIC_DETAILS = {"latency_ms", "monitor_type", "monitor_url", "uptime_24u", "checks", "worker", "bron_naam"}


def adapter_component(db: Session, row: CatalogApp, inv_state: dict[str, Any], now: datetime) -> Component:
    link = db.scalar(select(AdapterLink).where(AdapterLink.catalog_app_id == row.id, AdapterLink.app_id == row.app_id))
    if link is None:
        return Component("binnenkant", BINNENKANT_P3, "unknown", "adapter_niet_gekoppeld", None)
    bound = binding_is_current(link, row, current_target(db), published_ports(inv_state))
    measurement = stored_health(link, now, bound=bound)
    extra: dict[str, Any] = {}
    if measurement.laatste_status is not None:
        extra["laatste_status"] = measurement.laatste_status
    if measurement.reason_code == "meting_verouderd":
        extra["verouderd"] = True
    return Component(
        "binnenkant",
        BINNENKANT_P3,
        measurement.status,
        measurement.reason_code,
        measurement.observed_at,
        extra=extra,
        geldig_tot=measurement.geldig_tot,
        bevestigd_op=link.observed_at
        if link.laatste_status == "healthy"
        and link.laatste_fout
        not in ("bron_identiteit_onbekend", "bron_identiteit_gewijzigd", "bron_identiteit_onbewezen")
        else None,
    )


def app_health(
    db: Session, settings: Settings, row: CatalogApp, inv_state: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    now = now or utcnow()
    prof = profile_for(row.app_id)
    runtime = truenas_component(row, inv_state, now)
    comps = []
    if prof.binnenkant == BINNENKANT_HUB:
        comps.append(hub_worker_component(db, settings, now))
    elif prof.binnenkant == BINNENKANT_P3:
        comps.append(adapter_component(db, row, inv_state, now))
    comps.extend(observation_components(db, row, now))
    boundaries = inv_state["identiteit_sinds"]
    # Discovery volgt ook wijzigingen van de ingeschreven dienst (service_id).
    limits = [_source_time(boundaries.get(row.runtime_id)), _source_time(row.bron.get("identiteit_sinds"))]
    since = max((stamp for stamp in limits if stamp is not None), default=None)
    return evaluate(
        [runtime, *comps],
        now=now,
        identiteit_gevolgd=row.runtime_id in boundaries,
        identiteit_sinds=since,
        aanwezig=row.aanwezig,
        binnenkant_vereist=prof.binnenkant_vereist,
        binnenkant_bron=prof.binnenkant,
    )
