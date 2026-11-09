"""Incidentenmotor (B01-005, B09-004…006): events → incidenten met dedupe, correlatie, snooze, erkenning en readback.

Verwerking (worker, periodiek ``incidenten_bijwerken``):
1. Nog niet verwerkte events uit de eigen outbox en de events-inbox (kolom ``incident_verwerkt_op``, geclaimd met
   ``FOR UPDATE SKIP LOCKED``; geen watermerk, dus geen gaten bij gelijktijdige commits) gaan door de regels
   (``rules.classify``) en de haken (bv. sessie-intrekking bij ``sso.access.revoked``).
2. **Dedupe/correlatie:** hooguit één niet-opgelost incident per vingerafdruk. 100 identieke crashes → één incident
   met ``aantal = 100``. Een probleem binnen het heropenvenster na een herstel heropent hetzelfde incident
   (``heropend``) in plaats van een nieuw te maken; dat telt mee voor de veilige modus (B09-006).
3. **Herstel** sluit alleen het incident met precies dezelfde vingerafdruk, en alleen als het herstel niet ouder is
   dan het laatste probleem (een laat afgeleverd oud herstel sluit niets).
4. **Tijd:** snooze en erkenning verlopen (terug naar ``open`` + melding als het nog actief is); kritieke, niet
   erkende incidenten escaleren (hooguit ``incident_max_escalations`` herinneringen).
5. **Readback:** waar de Hub de bron zelf kan teruglezen (noodaccount geroteerd, monitoringbron weer ok, kanaal weer
   ok) sluit een bevestigde readback het incident; ``unknown`` sluit nooit iets.

Meldingen gaan via de bestaande wachtrij (rate-limit, stille uren, dead-letter): één melding per opening, één
hersteldmelding als er eerder gemeld is ("systeemalerts missen geen herstelmelding"). Alert-incidenten melden niet
dubbel (de alertregels melden zelf).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from hub import APP_ID
from hub.config import Settings
from hub.incidents import hypothesis, readback
from hub.incidents.rules import ERNST_RANK, EventIn, Signaal, classify
from hub.models import InboxEvent, Incident, IncidentEvent, Notification, NotificationChannel, OutboxEvent
from hub.redact import redact_log_text
from hub.timeutil import iso, utcnow

log = logging.getLogger("hub.incidenten")

ACTIEF = ("open", "erkend", "gesnoozed")
MAX_IDS = 20
Hook = Callable[[Session, Settings, EventIn, datetime], None]
HOOKS: list[Hook] = []


def register_hook(fn: Hook) -> Hook:
    if fn not in HOOKS:
        HOOKS.append(fn)
    return fn


@dataclass
class Stats:
    events: int = 0
    nieuw: int = 0
    bijgewerkt: int = 0
    heropend: int = 0
    opgelost: int = 0
    genegeerd: int = 0
    meldingen: int = 0
    tijd: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "events": self.events,
            "nieuw": self.nieuw,
            "bijgewerkt": self.bijgewerkt,
            "heropend": self.heropend,
            "opgelost": self.opgelost,
            "genegeerd": self.genegeerd,
            "meldingen": self.meldingen,
            **self.tijd,
        }


# ------------------------------------------------------------------ events lezen
def _from_outbox(r: OutboxEvent) -> EventIn:
    return EventIn(
        stroom="outbox",
        ref=f"outbox:{r.event_id}",
        source_app=APP_ID,
        event_type=r.event_type,
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        payload=r.payload or {},
        classification=r.classification,
        op=r.timestamp_utc,
        trace_id=str(r.trace_id) if r.trace_id else None,
        actor=f"system:{APP_ID}",
    )


def _from_inbox(r: InboxEvent) -> EventIn:
    actor = r.actor or {}
    return EventIn(
        stroom="inbox",
        ref=f"inbox:{r.event_id}",
        source_app=r.source_app,
        event_type=r.event_type,
        entity_type=r.entity_type,
        entity_id=r.entity_id,
        payload=r.payload or {},
        classification=r.classification,
        op=r.timestamp_utc,
        trace_id=str(r.trace_id) if r.trace_id else None,
        correlation_id=str(r.correlation_id) if r.correlation_id else None,
        actor=f"{actor.get('type', '?')}:{actor.get('id', '?')}"[:160],
    )


# ------------------------------------------------------------------ hulpfuncties
def _push(values: list[Any] | None, value: str | None) -> list[Any]:
    out = list(values or [])
    if value and value not in out:
        out.append(value)
    return out[-MAX_IDS:]


def _event_count(db: Session, inc: Incident) -> int:
    return int(
        db.scalar(select(func.count()).select_from(IncidentEvent).where(IncidentEvent.incident_id == inc.id)) or 0
    )


def add_event(
    db: Session,
    inc: Incident,
    *,
    ref: str,
    soort: str,
    op: datetime,
    samenvatting: str,
    settings: Settings | None = None,
    event_type: str | None = None,
    bron: str = "",
    details: dict[str, Any] | None = None,
    classificatie: str = "internal",
    trace_id: str | None = None,
    actor: str | None = None,
    force: bool = False,
) -> IncidentEvent | None:
    """Gebeurtenis vastleggen (begrensd per incident; status- en notitie-events altijd)."""
    cap = settings.incident_max_events if settings is not None else 500
    if not force and soort in ("probleem", "info", "gecorreleerd") and _event_count(db, inc) >= cap:
        return None
    if db.scalar(select(IncidentEvent.id).where(IncidentEvent.bron_ref == ref)) is not None:
        return None
    row = IncidentEvent(
        incident_id=inc.id,
        bron_ref=ref[:200],
        soort=soort,
        op=op,
        ontvangen_op=utcnow(),
        event_type=event_type,
        bron=bron[:64],
        samenvatting=redact_log_text(samenvatting, max_len=500),
        details=details or {},
        classificatie=classificatie,
        trace_id=trace_id,
        actor=actor,
    )
    db.add(row)
    db.flush()
    return row


def _channels(db: Session, ernst: str) -> list[NotificationChannel]:
    chans = db.scalars(select(NotificationChannel).where(NotificationChannel.ingeschakeld.is_(True)))
    return [c for c in chans if ERNST_RANK.get(ernst, 0) >= ERNST_RANK.get(c.min_ernst, 0)]


def _message(inc: Incident, soort: str) -> tuple[str, str]:
    onderwerp = f" ({inc.onderwerp_naam})" if inc.onderwerp_naam and inc.onderwerp_naam not in inc.titel else ""
    if soort == "hersteld":
        titel = f"Hersteld: {inc.titel}"
        tekst = (
            f"{inc.titel}{onderwerp} is hersteld ({inc.oplos_reden or 'herstelsignaal van de bron'}). "
            f"Open sinds {iso(inc.geopend_op)}, {inc.aantal} gebeurtenis(sen)."
        )
    elif soort == "herhaling":
        titel = f"Nog actief: {inc.titel}"
        tekst = (
            f"{inc.titel}{onderwerp} is nog niet opgelost en niet (meer) erkend. Sinds {iso(inc.geopend_op)}; "
            f"{inc.aantal} gebeurtenis(sen). Bekijk de incidenten-inbox in de Hub."
        )
    else:
        titel = f"[{inc.ernst}] {inc.titel}"
        tekst = (
            f"{inc.titel}{onderwerp}. Bron: {inc.bron}. Eerste gebeurtenis {iso(inc.eerste_op)}, laatste "
            f"{iso(inc.laatste_op)} ({inc.aantal}×). Bekijk de incidenten-inbox in de Hub."
        )
    return redact_log_text(titel, max_len=160), redact_log_text(tekst, max_len=2000)


def notify(db: Session, inc: Incident, soort: str, now: datetime, *, suffix: str = "") -> int:
    """Eén melding per kanaal per overgang (dedupe-sleutel); gesnoozed → vastgelegd als ``onderdrukt``."""
    if not inc.meldt and soort != "veilige_modus":
        return 0
    titel, tekst = _message(inc, "actief" if soort == "veilige_modus" else soort)
    if soort == "veilige_modus":
        titel = f"Veilige modus: {inc.titel}"[:160]
        tekst = (
            f"{inc.titel} faalt herhaaldelijk ({inc.heropend}× heropend). De Hub stelt geen herstart meer voor; "
            "onderzoek de oorzaak via het runbook in de Hub."
        )
    key = f"incident:{inc.id}:{iso(inc.geopend_op)}:{soort}{suffix}"[:255]
    muted = inc.status == "gesnoozed" and inc.gesnoozed_tot is not None and inc.gesnoozed_tot > now
    made = 0
    for ch in _channels(db, inc.ernst):
        exists = db.scalar(
            select(Notification.id).where(Notification.kanaal_id == ch.id, Notification.dedupe_sleutel == key)
        )
        if exists is not None:
            continue
        db.add(
            Notification(
                kanaal_id=ch.id,
                dedupe_sleutel=key,
                bron="incident",
                incident_id=inc.id,
                soort="hersteld" if soort == "hersteld" else ("herhaling" if soort == "herhaling" else "actief"),
                ernst=inc.ernst,
                titel=titel,
                bericht=tekst,
                status="onderdrukt" if muted and soort != "hersteld" else "wachtrij",
                reden="gesnoozed" if muted and soort != "hersteld" else None,
                volgende_poging_op=now,
                aangemaakt_op=now,
                aangemaakt_door="system:incidenten",
            )
        )
        made += 1
    if made and soort != "hersteld":
        inc.melding_teller += 1
        inc.laatst_gemeld_op = now
    db.flush()
    return made


def _new_incident(sig: Signaal, ev: EventIn) -> Incident:
    now = utcnow()
    return Incident(
        id=uuid.uuid4(),
        vingerafdruk=sig.vingerafdruk[:255],
        soort=sig.soort[:64],
        titel=redact_log_text(sig.titel, max_len=200),
        ernst=sig.ernst,
        status="open",
        bron=sig.bron[:64],
        onderwerp_type=sig.onderwerp_type[:64],
        onderwerp_id=sig.onderwerp_id[:200],
        onderwerp_naam=redact_log_text(sig.onderwerp_naam, max_len=200),
        eerste_op=ev.op,
        laatste_op=ev.op,
        geopend_op=ev.op,
        aantal=1,
        heropend=0,
        heropeningen=[],
        hypothese={},
        veilige_modus=False,
        trace_ids=_push([], ev.trace_id),
        correlatie_ids=_push([], ev.correlation_id),
        meldt=sig.meldt,
        melding_teller=0,
        escalaties=0,
        classificatie=ev.classification,
        details=sig.details,
        aangemaakt_op=now,
        bijgewerkt_op=now,
        version=1,
    )


def active_for(db: Session, fingerprint: str) -> Incident | None:
    return db.scalars(
        select(Incident).where(Incident.vingerafdruk == fingerprint, Incident.status.in_(ACTIEF)).with_for_update()
    ).first()


def resolve(db: Session, inc: Incident, *, door: str, reden: str, op: datetime) -> None:
    inc.status, inc.opgelost_op, inc.opgelost_door = "opgelost", op, door[:80]
    inc.oplos_reden = reden[:300]
    inc.erkend_tot = inc.gesnoozed_tot = None
    inc.bijgewerkt_op, inc.version = utcnow(), inc.version + 1


def apply_signal(db: Session, settings: Settings, sig: Signaal, ev: EventIn, now: datetime, stats: Stats) -> None:
    inc = active_for(db, sig.vingerafdruk)
    common: dict[str, Any] = {
        "event_type": ev.event_type,
        "bron": ev.source_app,
        "classificatie": ev.classification,
        "trace_id": ev.trace_id,
        "actor": ev.actor,
        "settings": settings,
    }
    if sig.rol == "probleem":
        opened = reopened = False
        if inc is None:
            last = db.scalars(
                select(Incident)
                .where(Incident.vingerafdruk == sig.vingerafdruk, Incident.status == "opgelost")
                .order_by(Incident.opgelost_op.desc())
                .limit(1)
                .with_for_update()
            ).first()
            window = timedelta(seconds=settings.incident_reopen_window_seconds)
            if last is not None and last.opgelost_op is not None and ev.op - last.opgelost_op <= window:
                inc, reopened = last, True
                inc.status, inc.heropend = "open", inc.heropend + 1
                inc.heropeningen = [*list(inc.heropeningen or []), iso(ev.op)][-MAX_IDS:]
                inc.geopend_op = ev.op
                inc.opgelost_op = inc.opgelost_door = inc.oplos_reden = None
                inc.erkend_door = inc.erkend_op = inc.erkend_tot = None
                inc.gesnoozed_door = inc.gesnoozed_tot = None
                inc.escalaties = 0
                stats.heropend += 1
            else:
                inc, opened = _new_incident(sig, ev), True
                db.add(inc)
                db.flush()
                stats.nieuw += 1
        if not opened:
            inc.aantal += 1
            if ev.op > inc.laatste_op:
                inc.laatste_op = ev.op
            if ev.op < inc.eerste_op:
                inc.eerste_op = ev.op
            if ERNST_RANK.get(sig.ernst, 0) > ERNST_RANK.get(inc.ernst, 0):
                inc.ernst = sig.ernst  # automatisch alleen verhogen, nooit verlagen
            if sig.details:
                inc.details = sig.details
            inc.trace_ids = _push(inc.trace_ids, ev.trace_id)
            inc.correlatie_ids = _push(inc.correlatie_ids, ev.correlation_id)
            inc.bijgewerkt_op, inc.version = utcnow(), inc.version + 1
            if not reopened:
                stats.bijgewerkt += 1
        add_event(
            db,
            inc,
            ref=ev.ref,
            soort="probleem",
            op=ev.op,
            samenvatting=sig.samenvatting or sig.titel,
            details=sig.details,
            **common,
        )
        hypothesis.refresh(db, settings, inc, now)
        from hub.runbooks.engine import check_safe_mode, runbook_for  # laat import: runbooks gebruikt deze module

        rb = runbook_for(inc)
        inc.runbook_id = rb.id if rb is not None else None
        if reopened and check_safe_mode(db, settings, inc, now):
            stats.meldingen += notify(db, inc, "veilige_modus", now)
        if opened or reopened or sig.meldt_elke_keer:
            stats.meldingen += notify(
                db, inc, "actief", now, suffix="" if not sig.meldt_elke_keer else f":{inc.aantal}"
            )
        return
    if inc is None:
        stats.genegeerd += 1
        return
    if sig.rol == "herstel":
        if ev.op < inc.laatste_op:
            # Een herstel dat ouder is dan het laatste probleem (late levering) sluit niets.
            add_event(
                db,
                inc,
                ref=ev.ref,
                soort="info",
                op=ev.op,
                samenvatting="Herstelsignaal ouder dan het laatste probleem: genegeerd.",
                **common,
            )
            stats.genegeerd += 1
            return
        add_event(
            db,
            inc,
            ref=ev.ref,
            soort="herstel",
            op=ev.op,
            samenvatting=sig.samenvatting or sig.titel,
            force=True,
            **common,
        )
        was_notified = inc.melding_teller > 0
        resolve(db, inc, door="system:herstel", reden=f"herstelsignaal: {ev.event_type}", op=ev.op)
        stats.opgelost += 1
        if was_notified:
            stats.meldingen += notify(db, inc, "hersteld", now)
        return
    add_event(db, inc, ref=ev.ref, soort="info", op=ev.op, samenvatting=sig.samenvatting or sig.titel, **common)


def _attach_correlated(db: Session, settings: Settings, ev: EventIn) -> bool:
    if not ev.correlation_id:
        return False
    inc = db.scalars(
        select(Incident)
        .where(Incident.status.in_(ACTIEF), Incident.correlatie_ids.contains([ev.correlation_id]))
        .order_by(Incident.laatste_op.desc())
        .limit(1)
    ).first()
    if inc is None:
        return False
    add_event(
        db,
        inc,
        ref=ev.ref,
        soort="gecorreleerd",
        op=ev.op,
        settings=settings,
        event_type=ev.event_type,
        bron=ev.source_app,
        samenvatting=f"Gecorreleerd event {ev.event_type} (correlation_id).",
        classificatie=ev.classification,
        trace_id=ev.trace_id,
        actor=ev.actor,
    )
    return True


def handle(db: Session, settings: Settings, ev: EventIn, now: datetime, stats: Stats) -> None:
    for hook in HOOKS:
        try:
            with db.begin_nested():
                hook(db, settings, ev, now)
        except Exception:
            log.exception("incidenthaak %s faalde voor %s", getattr(hook, "__name__", "?"), ev.ref)
    sig = classify(ev)
    if sig is None:
        if not _attach_correlated(db, settings, ev):
            stats.genegeerd += 1
        return
    apply_signal(db, settings, sig, ev, now, stats)


def _pending(db: Session, model: type[OutboxEvent] | type[InboxEvent], limit: int) -> list[Any]:
    return list(
        db.scalars(
            select(model)
            .where(model.incident_verwerkt_op.is_(None))
            .order_by(model.seq)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
    )


def ingest(db: Session, settings: Settings, now: datetime, stats: Stats) -> None:
    """Verwerk nog niet verwerkte events (eerst de eigen outbox, dan de inbox) in volgorde van ``seq``."""
    for stroom in ("outbox", "inbox"):
        rows = _pending(db, OutboxEvent if stroom == "outbox" else InboxEvent, settings.incident_batch)
        for r in rows:
            ev = _from_outbox(r) if stroom == "outbox" else _from_inbox(r)
            try:
                with db.begin_nested():
                    handle(db, settings, ev, now, stats)
            except Exception:
                log.exception("event %s niet verwerkt tot incident", ev.ref)
            r.incident_verwerkt_op = now
            stats.events += 1
        db.flush()


# ------------------------------------------------------------------ tijd en readback
def tick(db: Session, settings: Settings, now: datetime, stats: Stats) -> None:
    t = {"snooze_verlopen": 0, "erkenning_verlopen": 0, "escalaties": 0, "readback_opgelost": 0, "opgeruimd": 0}
    for inc in db.scalars(select(Incident).where(Incident.status.in_(ACTIEF)).with_for_update(skip_locked=True)):
        if inc.status == "gesnoozed" and inc.gesnoozed_tot is not None and inc.gesnoozed_tot <= now:
            inc.status, inc.gesnoozed_tot = "open", None
            inc.bijgewerkt_op, inc.version = now, inc.version + 1
            add_event(
                db,
                inc,
                ref=f"status:{uuid.uuid4()}",
                soort="status",
                op=now,
                settings=settings,
                samenvatting="Snooze verlopen; incident weer open.",
                force=True,
            )
            t["snooze_verlopen"] += 1
            stats.meldingen += notify(db, inc, "herhaling", now, suffix=f":snooze:{iso(now)}")
        if inc.status == "erkend" and inc.erkend_tot is not None and inc.erkend_tot <= now:
            inc.status = "open"
            inc.bijgewerkt_op, inc.version = now, inc.version + 1
            add_event(
                db,
                inc,
                ref=f"status:{uuid.uuid4()}",
                soort="status",
                op=now,
                settings=settings,
                samenvatting="Erkenning verlopen; incident weer open.",
                force=True,
            )
            t["erkenning_verlopen"] += 1
            stats.meldingen += notify(db, inc, "herhaling", now, suffix=f":erkenning:{iso(now)}")
        rb = readback.state(db, settings, inc, now)
        if rb["toestand"] == "hersteld" and rb.get("autoritatief"):
            add_event(
                db,
                inc,
                ref=f"status:{uuid.uuid4()}",
                soort="herstel",
                op=now,
                settings=settings,
                samenvatting=f"Readback: {rb.get('detail') or 'bron meldt herstel'}.",
                force=True,
            )
            was_notified = inc.melding_teller > 0
            resolve(db, inc, door="system:readback", reden=f"readback: {rb.get('detail') or 'hersteld'}", op=now)
            t["readback_opgelost"] += 1
            stats.opgelost += 1
            if was_notified:
                stats.meldingen += notify(db, inc, "hersteld", now)
            continue
        if (
            inc.status == "open"
            and inc.ernst == "kritiek"
            and inc.meldt
            and inc.laatst_gemeld_op is not None
            and inc.escalaties < settings.incident_max_escalations
            and now - inc.laatst_gemeld_op >= timedelta(seconds=settings.incident_escalation_seconds)
        ):
            inc.escalaties += 1
            t["escalaties"] += 1
            stats.meldingen += notify(db, inc, "herhaling", now, suffix=f":escalatie:{inc.escalaties}")
        hypothesis.refresh(db, settings, inc, now)
    cutoff = now - timedelta(days=settings.incident_retention_days)
    res = db.execute(delete(Incident).where(Incident.status == "opgelost", Incident.opgelost_op < cutoff))
    t["opgeruimd"] = int(getattr(res, "rowcount", 0) or 0)
    stats.tijd = t
    db.flush()


def run(db: Session, settings: Settings, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    stats = Stats()
    ingest(db, settings, now, stats)
    tick(db, settings, now, stats)
    return stats.as_dict()
