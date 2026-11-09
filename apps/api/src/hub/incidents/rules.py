"""Van event naar incidentsignaal (B01-005): vaste, deterministische regels — geen AI, geen vrije tekst als opdracht.

Een signaal heeft een **rol** (``probleem`` | ``herstel`` | ``info``) en een **vingerafdruk** (soort × bron ×
onderwerp). Correlatie gebeurt alleen op die vingerafdruk: een herstel sluit uitsluitend het incident met precies
dezelfde vingerafdruk (nooit een "gerelateerd" incident van een andere app of een andere soort storing).

Bronnen:
- **eigen outbox** van de Hub (monitoringbronnen, meldingskanalen, eigen back-up, inventaris, noodlogin,
  alert-overgangen, auditketting);
- **events-inbox** van diensten (contract §7): ``app.health.changed``, de SSO-events van ``home-control-hub``
  (ADR-0009 daar: ``sso.authentik_sync.failed``, ``sso.authentik_upgrade_gate.evaluated``,
  ``sso.authentik_restore_check.completed``, ``sso.anomaly.detected``) en een algemene regel op het laatste segment
  (``…failed``/``…crashed`` → probleem, ``…succeeded``/``…recovered`` → herstel). Onbekende events maken geen incident.

Teksten uit payloads zijn **gegevens**, nooit instructies: ze komen alleen geschoond en ingekort in titel/details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from hub import APP_ID
from hub.redact import redact_log_text, redact_log_value

ERNST = ("info", "waarschuwing", "kritiek")
ERNST_RANK = {"info": 0, "waarschuwing": 1, "kritiek": 2}
HCH = "home-control-hub"

PROBLEEM_WOORDEN = {
    "failed",
    "crashed",
    "error",
    "errored",
    "down",
    "unhealthy",
    "timeout",
    "stalled",
    "offline",
    "lost",
    "expired",
    "rejected",
    "unreachable",
    "broken",
    "mismatch",
}
HERSTEL_WOORDEN = {"succeeded", "recovered", "restored", "healthy", "online", "resolved", "reachable"}
KRITIEK_WOORDEN = {"crashed", "down", "broken", "lost"}
ERNST_HINT = {
    "kritiek": "kritiek",
    "critical": "kritiek",
    "hoog": "kritiek",
    "high": "kritiek",
    "waarschuwing": "waarschuwing",
    "warning": "waarschuwing",
    "middel": "waarschuwing",
    "medium": "waarschuwing",
    "info": "info",
    "laag": "info",
    "low": "info",
}


@dataclass(frozen=True)
class EventIn:
    stroom: str  # inbox | outbox
    ref: str  # inbox:<event_id> | outbox:<event_id>
    source_app: str
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    classification: str
    op: datetime
    trace_id: str | None = None
    correlation_id: str | None = None
    actor: str | None = None


@dataclass(frozen=True)
class Signaal:
    rol: str  # probleem | herstel | info
    soort: str
    vingerafdruk: str
    titel: str
    ernst: str
    bron: str
    onderwerp_type: str = ""
    onderwerp_id: str = ""
    onderwerp_naam: str = ""
    meldt: bool = True  # meldingen via de incidentenmotor (alerts melden zelf al)
    meldt_elke_keer: bool = False  # elke probleemgebeurtenis opnieuw melden (bv. noodlogin)
    samenvatting: str = ""
    details: dict[str, Any] = field(default_factory=dict)


def _s(v: Any, n: int = 120) -> str:
    return redact_log_text(str(v), max_len=n) if v not in (None, "") else ""


def _ernst(payload: dict[str, Any], default: str) -> str:
    for key in ("ernst", "severity"):
        hint = ERNST_HINT.get(str(payload.get(key) or "").lower())
        if hint:
            return hint
    return default


def _safe_details(ev: EventIn, keys: tuple[str, ...] | None = None) -> dict[str, Any]:
    p = ev.payload or {}
    if keys is not None:
        p = {k: p[k] for k in keys if k in p}
    return redact_log_value(p)  # type: ignore[no-any-return]


# ------------------------------------------------------------------ eigen outbox van de Hub
def _hub(ev: EventIn) -> Signaal | None:
    p = ev.payload or {}
    et, eid = ev.event_type, ev.entity_id
    if et in ("monitoring.source.failed", "monitoring.source.recovered"):
        naam = _s(p.get("naam"), 64) or eid
        fp = f"{APP_ID}:monitor_source:{eid}"
        if et.endswith("recovered"):
            return Signaal(
                "herstel",
                "monitoring.bron_storing",
                fp,
                f"Monitoringbron '{naam}' weer bereikbaar",
                "info",
                "hub:monitoring",
                "monitor_source",
                eid,
                naam,
                samenvatting=f"Bron '{naam}' werkt weer.",
            )
        reden = _s(p.get("reden"), 64) or "onbekend"
        return Signaal(
            "probleem",
            "monitoring.bron_storing",
            fp,
            f"Monitoringbron '{naam}' faalt ({reden})",
            "waarschuwing",
            "hub:monitoring",
            "monitor_source",
            eid,
            naam,
            samenvatting=f"Bron '{naam}' ({_s(p.get('soort'), 32)}) gaf: {reden}.",
            details=_safe_details(ev, ("soort", "naam", "reden", "vorige")),
        )
    if et in ("notification.channel.failed", "notification.channel.recovered", "notification.delivery.failed"):
        kanaal = str(p.get("kanaal_id") or eid)
        naam = _s(p.get("naam"), 64) or kanaal
        fp = f"{APP_ID}:kanaal:{kanaal}"
        if et == "notification.channel.recovered":
            return Signaal(
                "herstel",
                "melding.kanaal_storing",
                fp,
                f"Meldingskanaal '{naam}' werkt weer",
                "info",
                "hub:meldingen",
                "notification_channel",
                kanaal,
                naam,
                samenvatting="Een melding is weer afgeleverd.",
            )
        reden = _s(p.get("reden"), 64) or "onbekend"
        samen = (
            f"Melding definitief niet afgeleverd na {p.get('pogingen')} pogingen (dead-letter): {reden}."
            if et == "notification.delivery.failed"
            else f"Kanaal '{naam}' faalt: {reden}."
        )
        return Signaal(
            "probleem",
            "melding.kanaal_storing",
            fp,
            f"Meldingskanaal '{naam}' faalt ({reden})",
            "waarschuwing",
            "hub:meldingen",
            "notification_channel",
            kanaal,
            naam,
            samenvatting=samen,
            details=_safe_details(ev, ("reden", "pogingen", "soort")),
        )
    if et in ("backup.run.failed", "backup.run.succeeded"):
        fp = f"{APP_ID}:eigen_backup"
        if et.endswith("succeeded"):
            return Signaal(
                "herstel",
                "backup.eigen_mislukt",
                fp,
                "Eigen database-export weer geslaagd",
                "info",
                "hub:backup",
                "self_backup",
                "hub",
                "Eigen database-export",
                samenvatting="Nieuwe export geslaagd en geverifieerd.",
            )
        reden = _s(p.get("reason_code"), 64) or "onbekend"
        return Signaal(
            "probleem",
            "backup.eigen_mislukt",
            fp,
            f"Eigen database-export mislukt ({reden})",
            "kritiek",
            "hub:backup",
            "self_backup",
            "hub",
            "Eigen database-export",
            samenvatting=f"Export {eid} mislukt: {reden}.",
            details=_safe_details(ev, ("status", "reason_code")),
        )
    if et == "inventory.run.completed":
        fp = f"{APP_ID}:truenas:inventaris"
        status = str(p.get("status") or "")
        reden = _s(p.get("reason_code"), 64) or "onbekend"
        if status == "ok":
            return Signaal(
                "herstel",
                "nas.inventaris",
                fp,
                "TrueNAS-inventaris weer volledig",
                "info",
                "hub:inventaris",
                "nas",
                "primary",
                "TrueNAS",
                samenvatting="Inventaris volledig gelezen.",
            )
        titel = "TrueNAS-inventaris onvolledig" if status == "partial" else "TrueNAS-inventaris mislukt"
        return Signaal(
            "probleem",
            "nas.inventaris",
            fp,
            f"{titel} ({reden})",
            "waarschuwing",
            "hub:inventaris",
            "nas",
            "primary",
            "TrueNAS",
            samenvatting=f"Inventaris {status or 'onbekend'}: {reden}.",
            details=_safe_details(ev, ("status", "reason_code")),
        )
    if et == "auth.break_glass.used":
        return Signaal(
            "probleem",
            "auth.noodlogin",
            f"{APP_ID}:noodaccount:{eid}",
            "Noodlogin gebruikt",
            "kritiek",
            "hub:auth",
            "user",
            eid,
            "noodaccount",
            meldt_elke_keer=True,
            samenvatting="Het noodaccount heeft ingelogd (wachtwoord + TOTP); roteren is verplicht.",
            details=_safe_details(ev, ("op", "sessieduur_minuten")),
        )
    if et in ("alert.instance.fired", "alert.instance.resolved"):
        rule_id = str(p.get("regel_id") or "")
        otype, oid = str(p.get("onderwerp_type") or ""), str(p.get("onderwerp_id") or "")
        naam = _s(p.get("onderwerp_naam"), 80) or oid
        regel = _s(p.get("regel_naam"), 80) or "Alert"
        soort = f"alert.{p.get('regel_sleutel') or 'eigen'}"
        fp = f"{APP_ID}:alert:{rule_id}:{otype}:{oid}"
        if et.endswith("resolved"):
            return Signaal(
                "herstel",
                soort,
                fp,
                f"{regel}: {naam} hersteld",
                "info",
                "hub:alerts",
                otype,
                oid,
                naam,
                meldt=False,
                samenvatting=f"Waarde {p.get('waarde')} weer binnen de herstelgrens.",
            )
        return Signaal(
            "probleem",
            soort,
            fp,
            f"{regel}: {naam}",
            _ernst(p, "waarschuwing"),
            "hub:alerts",
            otype,
            oid,
            naam,
            meldt=False,
            samenvatting=f"{_s(p.get('metriek'), 64)} = {p.get('waarde')} (drempel {p.get('drempel')}).",
            details=_safe_details(ev, ("metriek", "waarde", "drempel", "bron", "regel_sleutel")),
        )
    if et == "audit.chain.broken":
        return Signaal(
            "probleem",
            "audit.ketting_verbroken",
            f"{APP_ID}:audit:ketting",
            "Auditspoor: hash-ketting verbroken",
            "kritiek",
            "hub:audit",
            "audit_chain",
            "hub",
            "Auditspoor",
            samenvatting="De controle van het auditspoor vond een wijziging, gat of afgeknipte staart.",
            details=_safe_details(ev, ("fouten", "anker")),
        )
    return None


# ------------------------------------------------------------------ home-control-hub (SSO, ADR-0009 daar)
def _hch(ev: EventIn) -> Signaal | None:
    p = ev.payload or {}
    et = ev.event_type
    base = f"{HCH}:sso"
    if et == "sso.authentik_sync.failed":
        reden = _s(p.get("reason"), 64) or "onbekend"
        return Signaal(
            "probleem",
            "sso.authentik_sync",
            f"{base}:authentik_sync",
            f"Authentik-synchronisatie mislukt ({reden})",
            "waarschuwing",
            HCH,
            "integration_source",
            "authentik",
            "Authentik",
            samenvatting="home-control-hub kon Authentik niet lezen; rechten en events zijn mogelijk verouderd.",
            details=_safe_details(ev, ("reason",)),
        )
    if et == "sso.authentik_upgrade_gate.evaluated":
        outcome = str(p.get("outcome") or "")
        fp = f"{base}:upgrade_gate"
        if outcome == "ok_lokaal":
            return Signaal(
                "herstel",
                "sso.upgrade_gate",
                fp,
                "Authentik-upgradegate: lokaal in orde",
                "info",
                HCH,
                "integration_source",
                "authentik",
                "Authentik",
                samenvatting="Gate: ok_lokaal.",
            )
        rol = "probleem" if outcome == "rood" else "info"
        return Signaal(
            rol,
            "sso.upgrade_gate",
            fp,
            f"Authentik-upgradegate: {outcome or 'onbekend'}",
            "waarschuwing",
            HCH,
            "integration_source",
            "authentik",
            "Authentik",
            samenvatting=f"Gate naar {_s(p.get('target_version'), 32)}: {outcome or 'onbekend'}.",
            details=_safe_details(ev, ("target_version", "outcome", "failed")),
        )
    if et == "sso.authentik_restore_check.completed":
        outcome = str(p.get("outcome") or "")
        fp = f"{base}:herstelcontrole"
        if outcome == "ok":
            return Signaal(
                "herstel",
                "sso.herstelcontrole",
                fp,
                "Authentik-herstelcontrole in orde",
                "info",
                HCH,
                "integration_source",
                "authentik",
                "Authentik",
                samenvatting="Herstelcontrole: ok.",
            )
        rol = "probleem" if outcome == "afwijking" else "info"
        return Signaal(
            rol,
            "sso.herstelcontrole",
            fp,
            f"Authentik-herstelcontrole: {outcome or 'onbekend'}",
            "kritiek",
            HCH,
            "integration_source",
            "authentik",
            "Authentik",
            samenvatting="Na herstel/upgrade wijkt Authentik af van de export (rechten, 2FA of clients)."
            if outcome == "afwijking"
            else "Herstelcontrole onbekend.",
            details=_safe_details(ev, ("export_id", "outcome", "failed")),
        )
    if et == "sso.anomaly.detected":
        regel = _s(p.get("rule_id"), 64) or "onbekend"
        return Signaal(
            "probleem",
            "sso.afwijking",
            f"{HCH}:sso_anomaly:{ev.entity_id}",
            f"SSO-afwijking: {regel}",
            _ernst(p, "waarschuwing"),
            HCH,
            "sso_anomaly",
            ev.entity_id,
            regel,
            samenvatting=f"Afwijking '{regel}' in Authentik ({p.get('count') or 1}×).",
            details=_safe_details(ev, ("rule_id", "severity", "count", "first_seen")),
        )
    return None


# ------------------------------------------------------------------ algemene regels (alle bronnen)
def _generic(ev: EventIn) -> Signaal | None:
    p = ev.payload or {}
    domain, obj, verb = [*ev.event_type.split("."), "", "", ""][:3]
    onderwerp = f"{ev.entity_type}:{ev.entity_id}"
    naam = _s(p.get("naam") or p.get("name") or p.get("app_id"), 80) or ev.entity_id
    bron = ev.source_app
    if ev.event_type == "app.health.changed":
        status = str(p.get("status") or "unknown").lower()
        fp = f"{bron}:{onderwerp}:gezondheid"
        if status == "healthy":
            return Signaal(
                "herstel",
                "app.gezondheid",
                fp,
                f"{naam} weer gezond",
                "info",
                bron,
                ev.entity_type,
                ev.entity_id,
                naam,
                samenvatting="Status healthy.",
            )
        if status in ("down", "degraded"):
            ernst = "kritiek" if status == "down" else "waarschuwing"
            reden = _s(p.get("reason_code") or p.get("reden"), 64)
            return Signaal(
                "probleem",
                "app.gezondheid",
                fp,
                f"{naam}: {status}" + (f" ({reden})" if reden else ""),
                _ernst(p, ernst),
                bron,
                ev.entity_type,
                ev.entity_id,
                naam,
                samenvatting=f"Status {status}" + (f": {reden}." if reden else "."),
                details=_safe_details(ev, ("status", "reason_code", "reden", "vorige")),
            )
        # unknown is nooit een herstel en geen nieuw probleem
        return Signaal(
            "info",
            "app.gezondheid",
            fp,
            f"{naam}: status onbekend",
            "info",
            bron,
            ev.entity_type,
            ev.entity_id,
            naam,
            samenvatting="Status unknown (geen herstel).",
        )
    soort = f"{domain}.{obj}"
    fp = f"{bron}:{soort}:{onderwerp}"
    if verb in PROBLEEM_WOORDEN:
        default = "kritiek" if verb in KRITIEK_WOORDEN else "waarschuwing"
        return Signaal(
            "probleem",
            soort,
            fp,
            f"{bron}: {domain}.{obj} {verb} ({naam})",
            _ernst(p, default),
            bron,
            ev.entity_type,
            ev.entity_id,
            naam,
            samenvatting=f"Event {ev.event_type}.",
            details=_safe_details(ev),
        )
    if verb in HERSTEL_WOORDEN:
        return Signaal(
            "herstel",
            soort,
            fp,
            f"{bron}: {domain}.{obj} {verb} ({naam})",
            "info",
            bron,
            ev.entity_type,
            ev.entity_id,
            naam,
            samenvatting=f"Event {ev.event_type}.",
        )
    return None


def classify(ev: EventIn) -> Signaal | None:
    """Het signaal voor dit event, of ``None`` (geen incident; het event blijft wel in de inbox/outbox)."""
    if ev.source_app == APP_ID and ev.stroom == "outbox":
        return _hub(ev)
    if ev.source_app == HCH and ev.event_type.startswith("sso."):
        sig = _hch(ev)
        if sig is not None or ev.event_type in ("sso.access.revoked", "sso.access.changed"):
            return sig
    return _generic(ev)
