"""Runbooks koppelen aan incidenten, veilige modus en de knoppen 'Onderzoek' en 'Herstel voorstellen' (B09-006).

- **Koppeling** incidentsoort/bron → runbook met vaste regels (geen AI). Geen passend runbook → ``None``: de Hub zegt
  dat eerlijk in plaats van een willekeurig runbook te tonen.
- **Veilige modus:** heropent een incident ``max_herhalingen`` keer binnen ``venster_s`` (de app faalt telkens
  opnieuw, ook na herstarts door TrueNAS of een mens), dan gaat het incident in de veilige modus: één melding met de
  oorzaak-vraag, en 'Herstel voorstellen' geeft **geen** herstart meer (geen eindeloze herstartlus).
- **Herstel voorstellen** maakt alleen een ``ActionProposal`` (contract §8) zonder uitvoering: de policy-engine en de
  executor-acties komen in P2, dus ``uitvoerbaar: false`` met een vaste reden. Nooit gesimuleerd succes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from hub.config import Settings
from hub.incidents import engine as incidents
from hub.models import CatalogApp, Incident
from hub.runbooks.catalogus import BY_ID, Runbook, VeiligeModus
from hub.timeutil import iso


def runbook_for(inc: Incident) -> Runbook | None:
    s, bron = inc.soort.lower(), inc.bron.lower()
    if any(k in s for k in ("migration", "migratie")):
        return BY_ID["db_migratie_mislukt"]
    if any(k in s for k in ("pool-vol", "pool-bijna-vol", "pool-ongezond", "quota", "disk", "schijf", "storage")):
        return BY_ID["schijf_vol"]
    if any(k in s for k in ("deploy", "update", "upgrade", "install", "digest", "release")):
        return BY_ID["slechte_deployment"]
    if any(k in s for k in ("tailscale", "cloudflare", "tunnel", "vpn", "toegang")) or s == "auth.noodlogin":
        return BY_ID["toegang_kwijt"]
    if bron.startswith("jelly-leon") and "client" in s:
        return BY_ID["jellyfin_client"]
    if "gree" in s or (bron == "my_house" and any(k in s for k in ("climate", "device", "airco"))):
        return BY_ID["gree_onbekend"]
    if bron == "media-source-optimizer" and any(k in s for k in ("provider", "indexer", "usenet")):
        return BY_ID["mso_provider_uitval"]
    if s.startswith(("alert.app-down", "app.", "monitoring.bron_storing")):
        return BY_ID["service_offline"]
    return None


def _safe_cfg(settings: Settings, rb: Runbook | None) -> VeiligeModus:
    if rb is not None:
        return rb.veilige_modus
    return VeiligeModus(settings.incident_safe_mode_max_restarts, settings.incident_safe_mode_window_seconds)


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def check_safe_mode(db: Session, settings: Settings, inc: Incident, now: datetime) -> bool:
    """Aangeroepen bij elke heropening. ``True`` = het incident ging zojuist de veilige modus in (→ één melding)."""
    if inc.veilige_modus:
        return False
    cfg = _safe_cfg(settings, runbook_for(inc))
    stamps = [t for t in (_parse(str(s)) for s in inc.heropeningen or []) if t is not None]
    if not stamps:
        return False
    latest = max(stamps)
    recent = [t for t in stamps if latest - t <= timedelta(seconds=cfg.venster_s)]
    if len(recent) < cfg.max_herhalingen:
        return False
    inc.veilige_modus, inc.veilige_modus_sinds = True, now
    incidents.add_event(
        db,
        inc,
        ref=f"status:{uuid.uuid4()}",
        soort="status",
        op=now,
        settings=settings,
        force=True,
        samenvatting=f"Veilige modus: {len(recent)}× opnieuw gefaald binnen {cfg.venster_s // 60} min; "
        "de Hub stelt geen herstart meer voor.",
    )
    return True


def _target(db: Session, inc: Incident) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """(doel, expected_version, reden) voor een voorstel; alleen apps uit de catalogus (TrueNAS-appnaam)."""
    if inc.onderwerp_type != "app":
        return None, None, "doel_onbekend"
    app: CatalogApp | None = None
    try:
        app = db.get(CatalogApp, uuid.UUID(inc.onderwerp_id))
    except ValueError:
        app = None
    if app is None:
        return None, None, "doel_onbekend"
    expected = app.image_digest or f"versie:{app.version}"
    return {"host_id": "nas-primary", "app_id": app.runtime_id}, expected, None


def onderzoek(db: Session, settings: Settings, inc: Incident, now: datetime) -> dict[str, Any]:
    rb = runbook_for(inc)
    from hub.incidents import readback
    from hub.runbooks.catalogus import to_dict

    app_id = inc.onderwerp_id if inc.onderwerp_type == "app" else ""
    rb_dict = to_dict(rb) if rb is not None else None
    if rb_dict is not None:
        for stappen in rb_dict["fasen"].values():
            for st in stappen:
                if st.get("bron"):
                    st["bron"] = st["bron"].replace("{incident_id}", str(inc.id)).replace("{app_id}", app_id)
    return {
        "incident_id": str(inc.id),
        "runbook": rb_dict,
        "runbook_toelichting": None
        if rb is not None
        else "Geen runbook voor deze soort incident; volg de hypothese en het bewijs, of leg de oorzaak vast als "
        "notitie.",
        "hypothese": inc.hypothese,
        "readback": readback.state(db, settings, inc, now),
        "veilige_modus": {"actief": inc.veilige_modus, "sinds": iso(inc.veilige_modus_sinds)},
        "heropend": inc.heropend,
        "gemaakt_op": iso(now),
    }


def herstel_voorstellen(db: Session, settings: Settings, inc: Incident, actor: str, now: datetime) -> dict[str, Any]:
    rb = runbook_for(inc)
    base: dict[str, Any] = {
        "incident_id": str(inc.id),
        "runbook_id": rb.id if rb is not None else None,
        "uitvoerbaar": False,
        "veilige_modus": inc.veilige_modus,
        "gemaakt_op": iso(now),
    }
    if inc.status == "opgelost":
        return {**base, "voorstel": None, "reden": "al_opgelost", "advies": "Het incident is al opgelost."}
    if inc.veilige_modus:
        return {
            **base,
            "voorstel": None,
            "reden": "veilige_modus",
            "advies": "Veilige modus: de app faalt herhaaldelijk. De Hub stelt geen herstart meer voor; onderzoek "
            "de oorzaak met het runbook (logs, laatste wijziging, opslag) en hef de veilige modus pas op na een "
            "gerichte oplossing.",
        }
    if rb is None or rb.herstart_voorstel is None:
        return {
            **base,
            "voorstel": None,
            "reden": "geen_voorstel",
            "advies": "Voor dit incident is geen automatisch voorstel; volg het runbook of de hypothese.",
        }
    target, expected, why = _target(db, inc)
    if target is None:
        return {
            **base,
            "voorstel": None,
            "reden": why,
            "advies": "Het doel (TrueNAS-app) is niet bekend in de catalogus; geen voorstel.",
        }
    from hub.runbooks.catalogus import ALLOWLIST

    proposal = {
        "idempotency_key": str(uuid.uuid4()),
        "action_id": rb.herstart_voorstel,
        "target": target,
        "parameters": {"grace_seconds": 30} if rb.herstart_voorstel == "app.restart" else {},
        "reason": f"Incident {inc.id}: {inc.titel}"[:200],
        "actor": {"type": "user", "id": actor},
        "expected_version": expected,
        "risk_claim": ALLOWLIST[rb.herstart_voorstel],
        "evidence_ids": [f"incident:{inc.id}"],
        "expires_in_seconds": 300,
    }
    return {
        **base,
        "voorstel": proposal,
        "reden": "policy_engine_niet_beschikbaar",
        "advies": "Dit is alleen een voorstel. De policy-engine, goedkeuring en uitvoering door de executor volgen in "
        "fase P2; tot dan voer je dit zelf uit in TrueNAS → Apps. risk_claim is informatief: de policy bepaalt de "
        "klasse.",
    }
