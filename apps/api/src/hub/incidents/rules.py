"""Van event naar incidentsignaal (B01-005): vaste, deterministische regels — geen AI, geen vrije tekst als opdracht.

Een signaal heeft een **rol** (``probleem`` | ``herstel`` | ``info``) en een **vingerafdruk** (soort × bron ×
onderwerp). Correlatie gebeurt alleen op die vingerafdruk: een herstel sluit uitsluitend het incident met precies
dezelfde vingerafdruk (nooit een "gerelateerd" incident van een andere app of een andere soort storing).

Bronnen:
- **eigen outbox** van de Hub (monitoringbronnen, meldingskanalen, eigen back-up, inventaris, noodlogin,
  alert-overgangen, auditketting);
- **events-inbox** van diensten (contract 1.3 §7): ``app.health.changed`` over de eigen app, de SSO-events van
  ``home-control-hub`` (ADR-0009 daar: ``sso.authentik_sync.failed``, ``sso.authentik_upgrade_gate.evaluated``,
  ``sso.authentik_restore_check.completed``, ``sso.anomaly.detected``) en een algemene regel op het werkwoord (derde
  segment): **probleem** ``failed``, ``crashed``, ``down``, ``degraded``, ``stalled``, ``blocked``, ``rejected``,
  ``saturated``, ``conflict``; **herstel** ``recovered``, ``succeeded``, ``resolved``, ``restored``; de rest is
  informatie. Die regels gelden alleen binnen de **domeinen van de eigenaar** (``source_app``, eerste segment); een
  event buiten het eigen domein blijft algemene informatie en maakt geen incident. Onbekende events maken geen incident.
- **Ernst** (§7): ``payload.ernst`` met één van de vijf Peil-woorden (``kritiek``, ``hoog``, ``middel``, ``laag``,
  ``info``) → vaste afbeelding op de drie Hub-niveaus (``kritiek``; ``hoog``/``middel`` → ``waarschuwing``;
  ``laag``/``info`` → ``info``); de bronwaarde blijft bewaard voor de UI. ``payload.severity`` geldt nog één
  overgangsrelease (deze, 0.1.x) en vervalt daarna. Alleen ``kritiek`` escaleert.

Teksten uit payloads zijn **gegevens**, nooit instructies: ze komen alleen geschoond en ingekort in titel/details.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from hub import APP_ID
from hub.redact import redact_log_text, redact_log_value

ERNST = ("info", "waarschuwing", "kritiek")
ERNST_RANK = {"info": 0, "waarschuwing": 1, "kritiek": 2}
HCH = "home-control-hub"

# Contract 1.3 §7: vaste werkwoorden (derde segment) voor probleem en herstel; de rest is informatie.
PROBLEEM_WOORDEN = {"failed", "crashed", "down", "degraded", "stalled", "blocked", "rejected", "saturated", "conflict"}
HERSTEL_WOORDEN = {"recovered", "succeeded", "resolved", "restored"}
KRITIEK_WOORDEN = {"crashed", "down"}

# Contract 1.3 §7: de vijf Peil-woorden en hun vaste afbeelding op de drie Hub-niveaus.
ERNST_WOORDEN = ("kritiek", "hoog", "middel", "laag", "info")
ERNST_AFBEELDING = {
    "kritiek": "kritiek",
    "hoog": "waarschuwing",
    "middel": "waarschuwing",
    "laag": "info",
    "info": "info",
}
# Overgang (één release): payload.severity met de oude waarden → Peil-woord.
SEVERITY_OVERGANG = {
    "critical": "kritiek",
    "kritiek": "kritiek",
    "high": "hoog",
    "hoog": "hoog",
    "warning": "middel",
    "waarschuwing": "middel",
    "medium": "middel",
    "middel": "middel",
    "low": "laag",
    "laag": "laag",
    "info": "info",
}
# UI-label als de bron geen ernst meegaf (§7): kritiek → Kritiek, waarschuwing → Middel, info → Info.
ERNST_LABEL = {"kritiek": "Kritiek", "waarschuwing": "Middel", "info": "Info"}

# Contract 1.3 §7: domeinen per eigenaar (eerste segment). De eigenaar van een event is (source_app, domein).
DOMEINEN: dict[str, frozenset[str]] = {
    APP_ID: frozenset(
        {"auth", "alert", "audit", "backup", "inventory", "monitoring", "notification", "onboarding", "action"}
    ),
    HCH: frozenset({"sso", "energy", "network", "automation", "flow"}),
    "appstore-en-fork": frozenset({"catalog"}),
    "jelly-leon-platform": frozenset({"lifecycle"}),
    "zoeken-en-persoonlijke-ai": frozenset({"search", "voice"}),
    "jelly-leon": frozenset({"media"}),
    "mediaguard": frozenset({"media"}),  # via de Hub-adapter (P3); eigen regels, los van media van jelly-leon
}
# Gedeeld: app (alleen app.health.changed over de eigen app) en service (alleen de vaste lijst).
SERVICE_EVENTS = frozenset(
    {
        "service.hub_link.linked",
        "service.hub_link.unlinked",
        "service.hub_link.revoked",
        "service.token.rotated",
        "service.key_rotation.applied",
        "service.key_rotation.rejected",
    }
)
# Oude namen: één release lang mag een dienst beide sturen (informatie, nooit een incident).
SERVICE_EVENTS_OUD = frozenset(
    {"service.enrollment.completed", "service.hub_link.paired", "service.hub_key.rotation_rejected"}
)


def eigen_domein(source_app: str, event_type: str, entity_type: str, entity_id: str) -> bool:
    """Valt dit event onder de regels van zijn eigenaar (§7)? Buiten het eigen domein: alleen informatie."""
    domein = event_type.split(".", 1)[0]
    if domein == "app":
        return event_type == "app.health.changed" and entity_id == source_app
    if domein == "service":
        return event_type in SERVICE_EVENTS and entity_type == "service" and entity_id == source_app
    return domein in DOMEINEN.get(source_app, frozenset())


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
    ernst_bron: str | None = None  # Peil-woord uit payload.ernst (§7), voor de UI


def _s(v: Any, n: int = 120) -> str:
    return redact_log_text(str(v), max_len=n) if v not in (None, "") else ""


def bron_ernst(payload: dict[str, Any]) -> str | None:
    """Het Peil-woord uit ``payload.ernst`` (§7), of tijdens de overgang uit ``payload.severity``; anders ``None``."""
    ernst = payload.get("ernst")
    if isinstance(ernst, str) and ernst in ERNST_WOORDEN:
        return ernst
    severity = payload.get("severity")
    if isinstance(severity, str):
        return SEVERITY_OVERGANG.get(severity.strip().lower())
    return None


def _ernst(payload: dict[str, Any], default: str) -> str:
    woord = bron_ernst(payload)
    return ERNST_AFBEELDING[woord] if woord else default


def ernst_label(ernst: str, bron: str | None) -> str:
    """Wat de UI toont: de bronwaarde als die er is, anders de vaste afbeelding (§7)."""
    if bron in ERNST_WOORDEN:
        return bron.capitalize()
    return ERNST_LABEL.get(ernst, "Info")


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
    if et in ("action.run.failed", "action.run.succeeded", "action.outcome.clarified"):
        # Uitvoering van een actie via de executor (contract §8). Alleen een afwijking of een onbekende uitkomst is een
        # incident; een nette weigering of een mislukte TrueNAS-aanroep (toestand onveranderd) staat in de audit.
        doel = _s(p.get("doel"), 120) or eid
        actie = _s(p.get("action_id"), 96) or "actie"
        verzoek = _s(p.get("request_id"), 40)
        uitkomst = str(p.get("uitkomst") or "")
        if et == "action.outcome.clarified":
            return Signaal(
                "herstel",
                "actie.uitkomst_onbekend",
                f"{APP_ID}:actie_onbekend:{verzoek}",
                f"Uitkomst van {actie} op {doel} is opgehelderd",
                "info",
                "hub:acties",
                "action_request",
                verzoek,
                doel,
                samenvatting=f"Het journaal van de executor gaf uitsluitsel: {uitkomst or 'bekend'}.",
            )
        if et.endswith("succeeded"):
            return Signaal(
                "herstel",
                "actie.afwijking",
                f"{APP_ID}:actie_afwijking:{doel}",
                f"{actie} op {doel} uitgevoerd en gecontroleerd",
                "info",
                "hub:acties",
                "action_target",
                eid,
                doel,
                samenvatting="De toestand na de uitvoering klopt met de verwachting (readback door de executor).",
            )
        if uitkomst == "afwijking":
            return Signaal(
                "probleem",
                "actie.afwijking",
                f"{APP_ID}:actie_afwijking:{doel}",
                f"Afwijking na {actie} op {doel}: executor gestopt",
                "kritiek",
                "hub:acties",
                "action_target",
                eid,
                doel,
                meldt_elke_keer=True,
                samenvatting=(
                    "De toestand na de uitvoering wijkt af van de verwachting of is onbekend. De executor voert niets "
                    "meer uit tot een beheerder hem op de statuspagina van de executor vrijgeeft."
                ),
                details=_safe_details(ev, ("request_id", "action_id", "doel", "risk_class", "reden", "gestopt")),
            )
        if uitkomst == "onbekend":
            return Signaal(
                "probleem",
                "actie.uitkomst_onbekend",
                f"{APP_ID}:actie_onbekend:{verzoek}",
                f"Uitkomst van {actie} op {doel} is onbekend",
                "waarschuwing",
                "hub:acties",
                "action_request",
                verzoek,
                doel,
                samenvatting=(
                    "De executor gaf geen bruikbaar antwoord. De Hub herhaalt niets; vraag de uitkomst op via het "
                    "journaal van de executor."
                ),
                details=_safe_details(ev, ("request_id", "action_id", "doel", "risk_class", "reden")),
            )
        return None
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
        sig = _hub(ev)
    elif not eigen_domein(ev.source_app, ev.event_type, ev.entity_type, ev.entity_id):
        return None  # buiten het eigen domein: algemene informatie, nooit de regels van de eigenaar (§7)
    elif ev.source_app == HCH and ev.event_type.startswith("sso."):
        sig = _hch(ev)
        if sig is None and ev.event_type not in ("sso.access.revoked", "sso.access.changed"):
            sig = _generic(ev)
    else:
        sig = _generic(ev)
    if sig is not None and sig.ernst_bron is None:
        woord = bron_ernst(ev.payload or {})
        if woord is not None:
            sig = replace(sig, ernst_bron=woord)
    return sig
