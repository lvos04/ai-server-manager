"""Out-of-band melden (B09-005, EX22/EX23): eerlijk beeld van wat er nog meldt als de Hub of de NAS uitvalt.

Uitgangspunt (ADR-0022): **de Hub zit niet in het meldpad van Uptime Kuma.** Uptime Kuma controleert zelf en meldt zelf
via zijn eigen Gotify-instelling (Kuma → Gotify → telefoon). De Hub leest Kuma alleen (``GET /metrics``, status-page)
en verstuurt daarnaast zijn eigen meldingen; hij ontvangt en stuurt geen Kuma-meldingen door. Valt de Hub uit, dan
blijft Kuma dus melden — mits Kuma de Hub en de andere diensten zelf bewaakt en zijn Gotify-melding werkt.

Wat de Hub **niet** kan zien: of in Uptime Kuma een Gotify-melding is ingesteld en werkt (dat staat niet in
``/metrics``). Dat blijft "onbekend" tot een beheerder het in Kuma test en hier vastlegt (audit, handmatig bevestigd —
nooit "gevalideerd door de Hub").

EX23: draaien Uptime Kuma en/of Gotify op dezelfde NAS, dan meldt **niemand** iets bij volledige NAS-uitval. Ook met een
ander adres kan de Hub niet vaststellen dat die host echt onafhankelijk is (stroom, netwerk). De uitkomst is daarom
nooit "gedekt": hooguit ``extern_onbevestigd`` of ``extern_handmatig_bevestigd``.
"""

from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import APP_ID
from hub.config import Settings
from hub.models import AuditEvent, CatalogApp, HealthObservation, MonitorSource, NotificationChannel
from hub.registry import nas_address
from hub.timeutil import iso

BEVESTIGING_ACTIE = "monitoring.out_of_band.confirmed"
EIGEN_APPS = (APP_ID, "ai-server-manager-executor")
EX23_TEKST = (
    "Bij volledige uitval van de NAS meldt niemand iets: Uptime Kuma en Gotify moeten dan op een andere, "
    "onafhankelijke host draaien (eigen stroom en netwerk). Zonder zo'n externe host is er geen out-of-band melding."
)


def _host(url: str) -> str | None:
    try:
        return (urlsplit(url).hostname or "").lower() or None
    except ValueError:
        return None


def _same_host(url: str, nas: str | None) -> str:
    """``op_de_nas`` | ``andere_host`` | ``onbekend`` (alleen letterlijke vergelijking; geen DNS-aanname)."""
    host = _host(url)
    if host is None or nas is None:
        return "onbekend"
    nas_l = nas.lower().strip("[]")
    if host == nas_l:
        return "op_de_nas"
    try:
        ipaddress.ip_address(host)
        ipaddress.ip_address(nas_l)
    except ValueError:
        return "onbekend"  # een hostnaam tegenover een IP-adres: niet te beslissen zonder DNS
    return "andere_host"


def _fresh(obs: HealthObservation, now: datetime) -> bool:
    return obs.observed_at is not None and now - obs.observed_at <= timedelta(seconds=obs.ttl_seconds)


def last_confirmation(db: Session) -> dict[str, Any] | None:
    row = db.scalars(
        select(AuditEvent).where(AuditEvent.action == BEVESTIGING_ACTIE).order_by(AuditEvent.id.desc()).limit(1)
    ).first()
    if row is None:
        return None
    return {"op": iso(row.at), "door": row.actor_id, **(row.details or {}), "audit_id": row.id}


def status(db: Session, settings: Settings, now: datetime) -> dict[str, Any]:
    nas = nas_address(db)
    kuma_sources = list(
        db.scalars(
            select(MonitorSource).where(MonitorSource.soort == "uptime_kuma", MonitorSource.ingeschakeld.is_(True))
        )
    )
    channels = list(db.scalars(select(NotificationChannel).where(NotificationChannel.ingeschakeld.is_(True))))
    apps = list(db.scalars(select(CatalogApp).where(CatalogApp.aanwezig.is_(True))))
    obs = list(db.scalars(select(HealthObservation).where(HealthObservation.bron_type == "uptime_kuma")))
    watched = {o.subject_app_id for o in obs if o.subject_app_id is not None and _fresh(o, now)}
    hub_apps = [a for a in apps if a.app_id in EIGEN_APPS]
    hub_watch = {a.app_id or a.naam: (a.id in watched) for a in hub_apps}
    gaps = sorted(a.naam for a in apps if a.id not in watched)

    kuma = [
        {
            "id": str(s.id),
            "naam": s.naam,
            "status": s.laatste_status or "unknown",
            "laatst_ok": iso(s.laatste_ok),
            "locatie": _same_host(s.basis_url, nas),
        }
        for s in kuma_sources
    ]
    gotify = [{"id": str(c.id), "naam": c.naam, "locatie": _same_host(c.basis_url, nas)} for c in channels]
    confirmation = last_confirmation(db)

    if not kuma_sources:
        hub_uitval = {
            "status": "niet_ingericht",
            "tekst": "Geen Uptime Kuma als bron ingesteld: de Hub kan niet laten zien of er buiten de Hub om "
            "gemeld wordt. Richt Uptime Kuma in (I08) met een eigen Gotify-melding (I13).",
        }
    elif not hub_apps or not all(hub_watch.values()):
        hub_uitval = {
            "status": "hiaat",
            "tekst": "Uptime Kuma bewaakt de Hub (en/of de executor) niet met een verse monitor: valt de Hub uit, "
            "dan meldt Kuma dat niet. Voeg in Kuma een monitor toe op het adres en de poort van de Hub.",
        }
    else:
        hub_uitval = {
            "status": "kuma_bewaakt_hub",
            "tekst": "Uptime Kuma bewaakt de Hub zelf; Kuma meldt rechtstreeks via zijn eigen Gotify-instelling, "
            "zonder de Hub. Of die Kuma-melding werkt, ziet de Hub niet: test hem in Uptime Kuma.",
        }
    locs = {k["locatie"] for k in kuma} | {g["locatie"] for g in gotify}
    if not kuma_sources or "op_de_nas" in locs:
        nas_uitval = "niet_gedekt"
    elif locs == {"andere_host"} and confirmation and confirmation.get("externe_host"):
        nas_uitval = "extern_handmatig_bevestigd"
    elif locs == {"andere_host"}:
        nas_uitval = "extern_onbevestigd"
    else:
        nas_uitval = "onbekend"
    return {
        "hub_in_meldpad": False,
        "uitleg": "De Hub leest Uptime Kuma alleen en ontvangt of verstuurt geen Kuma-meldingen. Kuma meldt zelf via "
        "Gotify; de Hub-meldingen zijn een tweede, aparte route.",
        "uptime_kuma": kuma,
        "gotify_kanalen_hub": gotify,
        "hub_uitval": {**hub_uitval, "bewaakt": hub_watch},
        "apps_zonder_kuma_monitor": gaps,
        "kuma_meldt_via_gotify": "handmatig_bevestigd"
        if confirmation and confirmation.get("kuma_gotify_test_ontvangen")
        else "onbekend",
        "volledige_nas_uitval": {
            "status": nas_uitval,
            "gedekt": False,
            "tekst": EX23_TEKST,
        },
        "laatste_bevestiging": confirmation,
        "nas_adres_bekend": nas is not None,
        "bijgewerkt_op": iso(now),
    }
