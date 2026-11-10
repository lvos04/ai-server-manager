"""Oorzaak-hypothese met zekerheid en bewijs (B01-005, 08_UI "Problemen"): vaste regels, geen AI.

Elke hypothese noemt een ``sleutel`` (voor groepering in de inbox), een Nederlandse ``tekst``, een ``zekerheid``
(0–1, een grove inschatting van de regel, geen statistiek) en de ``bewijs``-verwijzingen waarop hij rust. Past
geen regel, dan is de uitkomst eerlijk **"Ik weet het niet"** (``sleutel`` en ``zekerheid`` leeg).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.inventory.store import kind_state
from hub.models import CatalogApp, Incident
from hub.timeutil import iso
from hub.truenas.connection import current_target

ONBEKEND_TEKST = "Ik weet het niet: er is onvoldoende bewijs voor een oorzaak."
APP_SOORTEN = ("alert.app-down", "app.gezondheid")
CREDENTIAL_REDENEN = ("geweigerd", "api_key", "credential", "token_ongeldig", "auth_failed", "unauthorized")


def _h(
    sleutel: str | None, tekst: str, zekerheid: float | None, bewijs: list[dict[str, Any]], regel: str, now: datetime
) -> dict[str, Any]:
    return {
        "sleutel": sleutel,
        "tekst": tekst,
        "zekerheid": zekerheid,
        "bewijs": bewijs[:20],
        "regel": regel,
        "berekend_op": iso(now),
    }


def unknown(now: datetime) -> dict[str, Any]:
    return _h(None, ONBEKEND_TEKST, None, [], "geen_regel", now)


def _reden(inc: Incident) -> str:
    d = inc.details or {}
    return str(d.get("reden") or d.get("reason_code") or d.get("reason") or "").lower()


def _nas_wide(db: Session, settings: Settings, inc: Incident, now: datetime) -> dict[str, Any] | None:
    """Meerdere apps tegelijk weg én de TrueNAS-inventaris faalt → vermoedelijk NAS/TrueNAS-API onbereikbaar."""
    if inc.soort not in APP_SOORTEN and not inc.soort.startswith("app."):
        return None
    window = timedelta(minutes=10)
    others = list(
        db.scalars(
            select(Incident).where(
                Incident.status != "opgelost",
                Incident.soort.in_(APP_SOORTEN),
                Incident.eerste_op >= inc.eerste_op - window,
                Incident.eerste_op <= inc.eerste_op + window,
            )
        )
    )
    subjects = {(o.onderwerp_type, o.onderwerp_id) for o in others}
    if len(subjects) < 3:
        return None
    target = current_target(db)
    st = kind_state(db, "apps", target=target.url if target else None, ttl_seconds=settings.inventory_max_age_seconds)
    bewijs: list[dict[str, Any]] = [{"soort": "incident", "id": str(o.id), "titel": o.titel} for o in others[:10]]
    bewijs.append({"soort": "inventaris", "status": st.get("status"), "reden": st.get("reason_code")})
    if st.get("status") != "ok":
        return _h(
            "nas:onbereikbaar",
            f"{len(subjects)} apps vallen binnen 10 minuten uit en de TrueNAS-inventaris "
            "faalt: vermoedelijk is de NAS of de TrueNAS-API (deels) onbereikbaar.",
            0.6,
            bewijs,
            "meerdere_apps_en_inventaris",
            now,
        )
    pools = kind_state(
        db, "pools", target=target.url if target else None, ttl_seconds=settings.inventory_max_age_seconds
    )
    bad = [p.get("naam") for p in pools.get("data") or [] if isinstance(p, dict) and p.get("gezond") is False]
    if pools.get("status") == "ok" and bad:
        bewijs.append({"soort": "pools", "ongezond": bad[:5]})
        return _h(
            "pool:ongezond",
            f"{len(subjects)} apps vallen tegelijk uit en een pool is niet gezond: vermoedelijk een opslagprobleem.",
            0.6,
            bewijs,
            "meerdere_apps_en_pool",
            now,
        )
    return _h(
        "gelijktijdig:apps",
        f"{len(subjects)} apps vallen binnen 10 minuten uit; een gedeelde oorzaak is "
        "waarschijnlijk maar niet vastgesteld (inventaris en pools zijn in orde).",
        0.3,
        bewijs,
        "meerdere_apps",
        now,
    )


def _app_state(db: Session, inc: Incident, now: datetime) -> dict[str, Any] | None:
    if inc.onderwerp_type != "app":
        return None
    try:
        app = db.get(CatalogApp, uuid.UUID(inc.onderwerp_id))
    except ValueError:
        return None
    if app is None or not app.runtime_staat:
        return None
    bewijs = [
        {
            "soort": "catalog_app",
            "id": str(app.id),
            "runtime_staat": app.runtime_staat,
            "laatst_gezien": iso(app.laatst_gezien),
        }
    ]
    staat = app.runtime_staat.upper()
    if staat == "STOPPED":
        return _h(
            "app:gestopt",
            f"TrueNAS meldt '{app.naam}' als gestopt (bewust of na een fout).",
            0.8,
            bewijs,
            "truenas_staat",
            now,
        )
    if staat == "CRASHED":
        return _h(
            "app:crasht", f"TrueNAS meldt '{app.naam}' als gecrasht; zie de app-log.", 0.7, bewijs, "truenas_staat", now
        )
    if staat == "DEPLOYING":
        return _h(
            "app:start_op",
            f"'{app.naam}' start (nog) op; wacht de start af voordat je ingrijpt.",
            0.4,
            bewijs,
            "truenas_staat",
            now,
        )
    return None


def compute(db: Session, settings: Settings, inc: Incident, now: datetime) -> dict[str, Any]:
    reden = _reden(inc)
    ev_bewijs: list[dict[str, Any]] = [{"soort": "incident", "id": str(inc.id), "reden": reden or None}]
    if inc.soort == "monitoring.bron_storing":
        if any(k in reden for k in CREDENTIAL_REDENEN):
            return _h(
                "credential:geweigerd",
                "De bron weigert de sleutel of het wachtwoord van de Hub: ingetrokken, verlopen of gewijzigd.",
                0.9,
                ev_bewijs,
                "reden_bron",
                now,
            )
        if reden in ("niet_bereikbaar", "tijdslimiet", "tls_fout"):
            return _h(
                "bron:onbereikbaar",
                "De bron is niet bereikbaar (app gestopt, netwerk of certificaat).",
                0.5,
                ev_bewijs,
                "reden_bron",
                now,
            )
    if inc.soort == "melding.kanaal_storing":
        if "token" in reden:
            return _h(
                "gotify:token",
                "Gotify weigert het applicatietoken: ingetrokken of verkeerd ingevuld.",
                0.9,
                ev_bewijs,
                "reden_kanaal",
                now,
            )
        if reden in ("niet_bereikbaar", "tijdslimiet", "tls_fout"):
            return _h("gotify:onbereikbaar", "Gotify is niet bereikbaar.", 0.5, ev_bewijs, "reden_kanaal", now)
    if inc.soort == "nas.inventaris":
        if "auth" in reden or "key" in reden or "geweigerd" in reden:
            return _h(
                "truenas:sleutel",
                "TrueNAS weigert de alleen-lezen API-sleutel.",
                0.8,
                ev_bewijs,
                "reden_inventaris",
                now,
            )
        if "unreachable" in reden or "niet_bereikbaar" in reden or "timeout" in reden:
            return _h(
                "nas:onbereikbaar",
                "De NAS of de TrueNAS-API is niet bereikbaar.",
                0.6,
                ev_bewijs,
                "reden_inventaris",
                now,
            )
        if "tls" in reden or "certificaat" in reden or "fingerprint" in reden:
            return _h(
                "truenas:certificaat",
                "Het TLS-certificaat van TrueNAS is gewijzigd of niet vertrouwd.",
                0.7,
                ev_bewijs,
                "reden_inventaris",
                now,
            )
    if inc.soort == "audit.ketting_verbroken":
        return _h(
            "audit:buiten_hub_gewijzigd",
            "Het auditspoor is buiten de Hub om gewijzigd of de database is "
            "teruggezet van een oudere stand (het anker ligt verder).",
            0.5,
            ev_bewijs,
            "audit",
            now,
        )
    for rule in (_nas_wide,):
        found = rule(db, settings, inc, now)
        if found is not None:
            return found
    found = _app_state(db, inc, now)
    if found is not None:
        return found
    return unknown(now)


def refresh(db: Session, settings: Settings, inc: Incident, now: datetime) -> None:
    h = compute(db, settings, inc, now)
    if (h.get("sleutel"), h.get("tekst")) != ((inc.hypothese or {}).get("sleutel"), (inc.hypothese or {}).get("tekst")):
        inc.hypothese = h
        inc.oorzaak_sleutel = h.get("sleutel")
