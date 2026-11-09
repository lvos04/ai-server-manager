"""Meldingen versturen (worker): rate-limit per kanaal, stille uren, herhaalpogingen en dead-letter — geen pushstorm.

- **Rate-limit:** per kanaal hooguit ``max_per_venster`` verzonden meldingen per ``venster_s``. Wat daarboven komt,
  wordt ``onderdrukt`` (``rate_limit``) en geteld; zodra er weer ruimte is gaat er één samenvatting ("N meldingen
  onderdrukt") in plaats van de hele stapel. Kritieke meldingen gaan in de wachtrij altijd vóór.
- **Stille uren:** niet-kritieke meldingen wachten tot het einde (``uitgesteld``); kritiek gaat altijd door (I13).
  Een uitgestelde "actief"-melding van een alert dat intussen hersteld is, wordt ``achterhaald`` (de hersteldmelding
  noemt de actieve periode).
- **Fouten:** netwerk/5xx → opnieuw met exponentiële backoff (30 s … 1 uur) tot ``notify_max_attempts``, daarna
  ``mislukt`` + outbox-event ``notification.delivery.failed``. Token geweigerd (401/403) → kanaal op ``fout``
  (fail-closed, geen herhaling) tot een beheerder het token vervangt; meldingen blijven tot dan in de wachtrij.
- Meldingen die langer dan ``notify_expire_seconds`` wachten, vervallen (``verlopen``): geen vloed oude berichten.
"""

from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.events.envelope import emit
from hub.models import AlertInstance, Incident, Notification, NotificationChannel
from hub.notify import gotify
from hub.timeutil import utcnow
from hub.vault import Vault

TOKEN_GEWEIGERD = "token_geweigerd"  # noqa: S105 - reden-code, geen geheim
DUE = ("wachtrij", "uitgesteld")


def parse_hhmm(v: str) -> time:
    hh, mm = v.split(":", 1)
    return time(int(hh), int(mm))


def quiet_until(stille_uren: dict[str, Any] | None, now: datetime) -> datetime | None:
    """Einde van de lopende stille periode (UTC) of None als het nu geen stille uren zijn."""
    if not stille_uren:
        return None
    try:
        tz = ZoneInfo(str(stille_uren["tijdzone"]))
        van, tot = parse_hhmm(str(stille_uren["van"])), parse_hhmm(str(stille_uren["tot"]))
    except (KeyError, ValueError, ZoneInfoNotFoundError):
        return None
    local = now.astimezone(tz)
    t = local.time()
    if van == tot:
        return None
    inside = (van <= t < tot) if van < tot else (t >= van or t < tot)
    if not inside:
        return None
    end_date = local.date() if (van < tot or t < tot) else local.date() + timedelta(days=1)
    end = datetime.combine(end_date, tot, tzinfo=tz)
    return end.astimezone(now.tzinfo)


def _backoff(pogingen: int) -> timedelta:
    base = min(3600.0, 30.0 * (2 ** max(0, pogingen - 1)))
    return timedelta(seconds=base * (0.8 + 0.4 * random.random()))  # noqa: S311 - jitter, geen cryptografie


def _sent_in_window(db: Session, ch: NotificationChannel, now: datetime) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.kanaal_id == ch.id,
                Notification.status == "verzonden",
                Notification.verzonden_op >= now - timedelta(seconds=ch.venster_s),
            )
        )
        or 0
    )


def _send(db: Session, settings: Settings, vault: Vault, ch: NotificationChannel, n: Notification) -> gotify.SendResult:
    token = vault.get(db, ch.token_ref)
    if not token:
        return gotify.SendResult(False, "token_ontbreekt", definitief=True)
    return gotify.send(
        ch.basis_url, token, titel=n.titel, bericht=n.bericht, ernst=n.ernst, policy=settings.outbound_policy()
    )


def mark_channel(db: Session, ch: NotificationChannel, ok: bool, reason: str | None, now: datetime) -> None:
    """Kanaalstatus bijwerken; bij een overgang (ok ↔ fout of een andere reden) een outbox-event (→ incident)."""
    before = (ch.laatste_status, ch.laatste_reden)
    ch.laatste_status, ch.laatste_reden, ch.laatste_op = ("ok" if ok else "fout"), reason, now
    if before != (ch.laatste_status, ch.laatste_reden) and (before[0] is not None or not ok):
        emit(
            db,
            "notification.channel.recovered" if ok else "notification.channel.failed",
            "notification_channel",
            str(ch.id),
            {"kanaal_id": str(ch.id), "naam": ch.naam, "soort": ch.soort, "reden": reason, "vorige": before[1]},
            timestamp=now,
        )


def _digest(db: Session, settings: Settings, vault: Vault, ch: NotificationChannel, now: datetime) -> bool:
    count = ch.onderdrukt_teller
    n = Notification(
        kanaal_id=ch.id,
        dedupe_sleutel=f"samenvatting:{ch.id}:{now.isoformat()}"[:255],
        bron="samenvatting",
        soort="bericht",
        ernst="waarschuwing",
        titel=f"{count} meldingen onderdrukt",
        bericht=(
            f"Om een meldingenstorm te voorkomen zijn {count} meldingen niet verstuurd (meer dan "
            f"{ch.max_per_venster} per {ch.venster_s // 60} min). Bekijk de Hub voor de actuele toestand."
        ),
        status="wachtrij",
        volgende_poging_op=now,
        aangemaakt_op=now,
    )
    db.add(n)
    db.flush()
    res = _send(db, settings, vault, ch, n)
    n.pogingen = 1
    if res.ok:
        n.status, n.verzonden_op, n.extern_id = "verzonden", now, res.extern_id
        ch.onderdrukt_teller, ch.onderdrukt_sinds = 0, None
        mark_channel(db, ch, True, None, now)
    else:
        n.status, n.reden = "mislukt", res.reden
        mark_channel(db, ch, False, res.reden, now)
    db.flush()
    return res.ok


def dispatch(db: Session, settings: Settings, vault: Vault, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    stats = {"verzonden": 0, "onderdrukt": 0, "uitgesteld": 0, "mislukt": 0, "opnieuw": 0, "verlopen": 0}
    expired = db.scalars(
        select(Notification).where(
            Notification.status.in_(DUE),
            Notification.aangemaakt_op < now - timedelta(seconds=settings.notify_expire_seconds),
        )
    )
    for n in expired:
        n.status, n.reden = "onderdrukt", "verlopen"
        stats["verlopen"] += 1
    db.flush()  # de sessie heeft geen autoflush: verlopen meldingen mogen hieronder niet meer als 'due' meetellen
    for ch in db.scalars(select(NotificationChannel).where(NotificationChannel.ingeschakeld.is_(True))):
        if ch.laatste_reden == TOKEN_GEWEIGERD:
            continue  # fail-closed tot een beheerder het token vervangt
        quiet_end = quiet_until(ch.stille_uren, now)
        sent = _sent_in_window(db, ch, now)
        if ch.onderdrukt_teller > 0 and sent < ch.max_per_venster and _digest(db, settings, vault, ch, now):
            sent += 1
            stats["verzonden"] += 1
        rank = case((Notification.ernst == "kritiek", 0), (Notification.ernst == "waarschuwing", 1), else_=2)
        due = list(
            db.scalars(
                select(Notification)
                .where(
                    Notification.kanaal_id == ch.id,
                    Notification.status.in_(DUE),
                    Notification.volgende_poging_op <= now,
                )
                .order_by(rank, Notification.aangemaakt_op)
                .limit(200)
            )
        )
        for n in due:
            if n.bron == "alert" and n.soort == "actief" and n.alert_instance_id and n.status == "uitgesteld":
                inst = db.get(AlertInstance, n.alert_instance_id)
                if inst is not None and inst.toestand != "firing":
                    n.status, n.reden = "onderdrukt", "achterhaald"
                    stats["onderdrukt"] += 1
                    continue
            if n.bron == "incident" and n.soort == "actief" and n.incident_id and n.status == "uitgesteld":
                inc = db.get(Incident, n.incident_id)
                if inc is not None and inc.status == "opgelost":
                    n.status, n.reden = "onderdrukt", "achterhaald"
                    stats["onderdrukt"] += 1
                    continue
            if quiet_end is not None and n.ernst != "kritiek":
                n.status, n.reden, n.volgende_poging_op = "uitgesteld", "stille_uren", quiet_end
                stats["uitgesteld"] += 1
                continue
            if sent >= ch.max_per_venster:
                n.status, n.reden = "onderdrukt", "rate_limit"
                ch.onderdrukt_teller += 1
                ch.onderdrukt_sinds = ch.onderdrukt_sinds or now
                stats["onderdrukt"] += 1
                continue
            res = _send(db, settings, vault, ch, n)
            n.pogingen += 1
            if res.ok:
                n.status, n.reden, n.verzonden_op, n.extern_id = "verzonden", None, now, res.extern_id
                mark_channel(db, ch, True, None, now)
                sent += 1
                stats["verzonden"] += 1
                continue
            mark_channel(db, ch, False, res.reden, now)
            if res.reden == TOKEN_GEWEIGERD:
                n.reden = TOKEN_GEWEIGERD  # blijft in de wachtrij; kanaal staat stil tot het token vervangen is
                break
            if res.definitief or n.pogingen >= settings.notify_max_attempts:
                n.status, n.reden = "mislukt", res.reden
                stats["mislukt"] += 1
                emit(
                    db,
                    "notification.delivery.failed",
                    "notification",
                    str(n.id),
                    {"kanaal_id": str(ch.id), "reden": res.reden, "pogingen": n.pogingen},
                )
                continue
            n.reden, n.volgende_poging_op = res.reden, now + _backoff(n.pogingen)
            stats["opnieuw"] += 1
    db.flush()
    return stats
