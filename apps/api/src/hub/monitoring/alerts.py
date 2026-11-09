"""Alertregels (B09-003): drempel + duur + hysterese, zonder pushstorm.

Toestand per (regel, onderwerp): ``ok`` → ``pending`` (drempel overschreden, duur loopt) → ``firing`` (duur verstreken;
één melding) → herstel pas als de waarde aan de veilige kant van de **herstel**drempel blijft gedurende de
herstelduur (één hersteldmelding). Waarden tussen drempel en herstelgrens houden een actief alert actief (hysterese).

- Verouderde gegevens (geen verse meting): **geen** overgang; een actief alert wordt nooit "hersteld" door ontbrekende
  data en een nieuw alert ontstaat er ook niet door (``gegevens_verouderd``).
- Per onderwerp één reeks: TrueNAS gaat voor de Hub zelf, die voor Beszel en Uptime Kuma (zelfde metriek uit twee
  bronnen geeft geen dubbel alert).
- Meldingen: per overgang precies één rij per kanaal (``dedupe_sleutel`` uniek); dempen (regel of alert) legt de
  melding vast als ``onderdrukt``; herhaling alleen met ``herhaal_na_s``.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.models import AlertInstance, AlertRule, MetricSample, MetricSeries, Notification, NotificationChannel
from hub.timeutil import iso, utcnow

OPERATORS = ("gt", "ge", "lt", "le")
ERNST = ("info", "waarschuwing", "kritiek")
ERNST_RANK = {"info": 0, "waarschuwing": 1, "kritiek": 2}
BRON_VOORKEUR = ("truenas", "hub", "beszel", "uptime_kuma")
MAX_SAMPLES_PER_EVAL = 500
OPERATOR_TEKST = {"gt": ">", "ge": "≥", "lt": "<", "le": "≤"}


def compare(op: str, value: float, threshold: float) -> bool:
    if op == "gt":
        return value > threshold
    if op == "ge":
        return value >= threshold
    if op == "lt":
        return value < threshold
    if op == "le":
        return value <= threshold
    raise ValueError(f"onbekende operator {op}")


def hysteresis_ok(op: str, drempel: float, herstel: float) -> bool:
    """De herstelgrens ligt aan de veilige kant van de drempel (of is gelijk: geen band)."""
    return herstel <= drempel if op in ("gt", "ge") else herstel >= drempel


@dataclass(frozen=True)
class DefaultRule:
    sleutel: str
    naam: str
    metriek: str
    onderwerp_type: str
    operator: str
    drempel: float
    herstel_drempel: float
    duur_s: int
    herstel_duur_s: int
    ernst: str


# Standaardregels (beleid, geen NAS-gegevens); een beheerder kan ze aanpassen of uitschakelen.
DEFAULT_RULES: tuple[DefaultRule, ...] = (
    DefaultRule("pool-vol", "Pool raakt vol", "pool.gebruik", "pool", "ge", 85, 80, 600, 600, "waarschuwing"),
    DefaultRule("pool-bijna-vol", "Pool bijna vol", "pool.gebruik", "pool", "ge", 95, 90, 300, 600, "kritiek"),
    DefaultRule("pool-ongezond", "Pool niet gezond", "pool.gezond", "pool", "lt", 0.5, 0.5, 0, 300, "kritiek"),
    DefaultRule("app-down", "App onbereikbaar", "app.status", "app", "lt", 0.25, 0.75, 300, 120, "kritiek"),
    DefaultRule("cpu-hoog", "CPU langdurig hoog", "cpu.gebruik", "nas", "ge", 95, 85, 900, 300, "waarschuwing"),
    DefaultRule("cpu-temp", "CPU-temperatuur hoog", "cpu.temperatuur", "nas", "ge", 90, 80, 300, 300, "waarschuwing"),
    DefaultRule(
        "geheugen-krap",
        "Weinig geheugen vrij",
        "geheugen.beschikbaar_pct",
        "nas",
        "le",
        5,
        10,
        600,
        300,
        "waarschuwing",
    ),
)


def seed_default_rules(db: Session) -> int:
    """Voeg ontbrekende standaardregels toe (op ``standaard_sleutel``); bestaande worden nooit overschreven."""
    have = set(db.scalars(select(AlertRule.standaard_sleutel).where(AlertRule.standaard_sleutel.is_not(None))))
    added = 0
    for r in DEFAULT_RULES:
        if r.sleutel in have:
            continue
        db.add(
            AlertRule(
                standaard_sleutel=r.sleutel,
                naam=r.naam,
                metriek=r.metriek,
                onderwerp_type=r.onderwerp_type,
                operator=r.operator,
                drempel=r.drempel,
                herstel_drempel=r.herstel_drempel,
                duur_s=r.duur_s,
                herstel_duur_s=r.herstel_duur_s,
                ernst=r.ernst,
                kanalen=[],
                ingeschakeld=True,
                aangemaakt_door="system:standaard",
                bijgewerkt_door="system:standaard",
            )
        )
        added += 1
    db.flush()
    return added


def _priority(bron: str) -> int:
    for i, prefix in enumerate(BRON_VOORKEUR):
        if bron.startswith(prefix):
            return i
    return len(BRON_VOORKEUR)


def _matching_series(db: Session, rule: AlertRule) -> list[MetricSeries]:
    q = select(MetricSeries).where(MetricSeries.metriek == rule.metriek)
    if rule.onderwerp_type:
        q = q.where(MetricSeries.onderwerp_type == rule.onderwerp_type)
    if rule.onderwerp_id:
        q = q.where(MetricSeries.onderwerp_id == rule.onderwerp_id)
    if rule.bron:
        q = q.where(MetricSeries.bron == rule.bron)
    return list(db.scalars(q))


def choose_series(candidates: list[MetricSeries], now: datetime, stale_s: int) -> MetricSeries:
    fresh = [s for s in candidates if s.laatste_op is not None and (now - s.laatste_op).total_seconds() <= stale_s]
    pool = fresh or candidates
    return sorted(pool, key=lambda s: (_priority(s.bron), -(s.laatste_op.timestamp() if s.laatste_op else 0)))[0]


def _muted(rule: AlertRule, inst: AlertInstance, now: datetime) -> bool:
    return bool((rule.gedempt_tot and rule.gedempt_tot > now) or (inst.gedempt_tot and inst.gedempt_tot > now))


def _target_channels(db: Session, rule: AlertRule) -> list[NotificationChannel]:
    chans = list(db.scalars(select(NotificationChannel).where(NotificationChannel.ingeschakeld.is_(True))))
    wanted = {str(k) for k in rule.kanalen or []}
    if wanted:
        chans = [c for c in chans if str(c.id) in wanted]
    return [c for c in chans if ERNST_RANK[rule.ernst] >= ERNST_RANK.get(c.min_ernst, 0)]


def _fmt(v: float | None) -> str:
    if v is None:
        return "onbekend"
    return f"{v:.0f}" if abs(v - round(v)) < 1e-9 else f"{v:.1f}"


def _message(rule: AlertRule, inst: AlertInstance, series: MetricSeries | None, soort: str) -> tuple[str, str]:
    eenheid = f" {series.eenheid}" if series and series.eenheid not in ("status", "aantal") else ""
    onderwerp = f"{inst.onderwerp_type} {inst.onderwerp_id}"
    if soort == "hersteld":
        titel = f"Hersteld: {rule.naam}"
        tekst = (
            f"{onderwerp}: {rule.metriek} is weer {_fmt(inst.laatste_waarde)}{eenheid} "
            f"(herstelgrens {OPERATOR_TEKST[rule.operator]} {_fmt(rule.herstel_drempel)} niet meer gehaald). "
            f"Actief van {iso(inst.firing_sinds)} tot {iso(inst.laatst_opgelost_op)}."
        )
    else:
        titel = ("Nog steeds actief: " if soort == "herhaling" else "") + rule.naam
        tekst = (
            f"{onderwerp}: {rule.metriek} = {_fmt(inst.laatste_waarde)}{eenheid} "
            f"({OPERATOR_TEKST[rule.operator]} {_fmt(rule.drempel)}{eenheid}, langer dan {rule.duur_s} s). "
            f"Sinds {iso(inst.firing_sinds)}. Bron: {series.bron if series else 'onbekend'}."
        )
    return titel[:160], tekst[:2000]


def queue_alert_notifications(
    db: Session, rule: AlertRule, inst: AlertInstance, series: MetricSeries | None, soort: str, now: datetime
) -> int:
    titel, tekst = _message(rule, inst, series, soort)
    suffix = f":{inst.melding_teller}" if soort == "herhaling" else ""
    key = f"alert:{inst.id}:{iso(inst.firing_sinds)}:{soort}{suffix}"[:255]
    muted = _muted(rule, inst, now)
    made = 0
    for ch in _target_channels(db, rule):
        exists = db.scalar(
            select(Notification.id).where(Notification.kanaal_id == ch.id, Notification.dedupe_sleutel == key)
        )
        if exists is not None:
            continue
        db.add(
            Notification(
                kanaal_id=ch.id,
                dedupe_sleutel=key,
                bron="alert",
                alert_instance_id=inst.id,
                soort=soort,
                ernst=rule.ernst,
                titel=titel,
                bericht=tekst,
                status="onderdrukt" if muted else "wachtrij",
                reden="gedempt" if muted else None,
                volgende_poging_op=now,
                aangemaakt_op=now,
            )
        )
        made += 1
    inst.melding_teller += 1
    inst.laatst_gemeld_op = now
    db.flush()
    return made


def step(rule: AlertRule, inst: AlertInstance, ts: datetime, value: float) -> str | None:
    """Verwerk één meting; geeft ``"actief"`` of ``"hersteld"`` bij een overgang, anders None."""
    inst.laatste_waarde, inst.laatste_sample_op = value, ts
    breach = compare(rule.operator, value, rule.drempel)
    recovered = not compare(rule.operator, value, rule.herstel_drempel)
    if inst.toestand == "ok":
        if breach:
            inst.toestand, inst.sinds, inst.pending_sinds = "pending", ts, ts
            if rule.duur_s <= 0:
                inst.toestand, inst.firing_sinds, inst.herstel_sinds = "firing", ts, None
                return "actief"
        return None
    if inst.toestand == "pending":
        if not breach:
            inst.toestand, inst.sinds, inst.pending_sinds = "ok", ts, None
            return None
        if inst.pending_sinds is not None and (ts - inst.pending_sinds).total_seconds() >= rule.duur_s:
            inst.toestand, inst.sinds, inst.firing_sinds, inst.herstel_sinds = "firing", ts, ts, None
            return "actief"
        return None
    # firing
    if recovered:
        if inst.herstel_sinds is None:
            inst.herstel_sinds = ts
        if (ts - inst.herstel_sinds).total_seconds() >= rule.herstel_duur_s:
            inst.toestand, inst.sinds, inst.pending_sinds, inst.herstel_sinds = "ok", ts, None, None
            inst.laatst_opgelost_op = ts
            return "hersteld"
    else:
        inst.herstel_sinds = None
    return None


def evaluate(db: Session, settings: Settings, *, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    stats: dict[str, Any] = {"regels": 0, "onderwerpen": 0, "overgangen": 0, "meldingen": 0, "verouderd": 0}
    for rule in db.scalars(select(AlertRule).where(AlertRule.ingeschakeld.is_(True))):
        stats["regels"] += 1
        groups: dict[tuple[str, str], list[MetricSeries]] = defaultdict(list)
        for s in _matching_series(db, rule):
            groups[(s.onderwerp_type, s.onderwerp_id)].append(s)
        for (otype, oid), candidates in groups.items():
            stats["onderwerpen"] += 1
            series = choose_series(candidates, now, settings.alert_stale_seconds)
            inst = db.scalars(
                select(AlertInstance).where(
                    AlertInstance.rule_id == rule.id,
                    AlertInstance.onderwerp_type == otype,
                    AlertInstance.onderwerp_id == oid,
                )
            ).first()
            if inst is None:
                inst = AlertInstance(
                    id=uuid.uuid4(),
                    rule_id=rule.id,
                    onderwerp_type=otype,
                    onderwerp_id=oid,
                    series_id=series.id,
                    toestand="ok",
                    sinds=now,
                    gegevens_verouderd=False,
                    melding_teller=0,
                )
                db.add(inst)
                db.flush()
            inst.series_id = series.id
            inst.laatste_eval_op = now
            fresh = series.laatste_op is not None and (
                (now - series.laatste_op).total_seconds() <= settings.alert_stale_seconds
            )
            inst.gegevens_verouderd = not fresh
            if not fresh:
                stats["verouderd"] += 1
                continue
            q = select(MetricSample.ts, MetricSample.waarde).where(MetricSample.series_id == series.id)
            if inst.laatste_sample_op is not None:
                q = q.where(MetricSample.ts > inst.laatste_sample_op)
            else:
                q = q.where(MetricSample.ts >= now - timedelta(seconds=max(rule.duur_s, 60) + 60))
            for ts, value in db.execute(q.order_by(MetricSample.ts).limit(MAX_SAMPLES_PER_EVAL)).all():
                change = step(rule, inst, ts, float(value))
                if change is not None:
                    stats["overgangen"] += 1
                    stats["meldingen"] += queue_alert_notifications(db, rule, inst, series, change, now)
            if (
                inst.toestand == "firing"
                and rule.herhaal_na_s
                and inst.laatst_gemeld_op is not None
                and (now - inst.laatst_gemeld_op).total_seconds() >= rule.herhaal_na_s
            ):
                stats["meldingen"] += queue_alert_notifications(db, rule, inst, series, "herhaling", now)
    db.flush()
    return stats


def rule_dict(r: AlertRule) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "standaard": r.standaard_sleutel is not None,
        "standaard_sleutel": r.standaard_sleutel,
        "naam": r.naam,
        "metriek": r.metriek,
        "onderwerp_type": r.onderwerp_type,
        "onderwerp_id": r.onderwerp_id,
        "bron": r.bron,
        "operator": r.operator,
        "drempel": r.drempel,
        "herstel_drempel": r.herstel_drempel,
        "duur_s": r.duur_s,
        "herstel_duur_s": r.herstel_duur_s,
        "ernst": r.ernst,
        "herhaal_na_s": r.herhaal_na_s,
        "kanalen": [str(k) for k in r.kanalen or []],
        "ingeschakeld": r.ingeschakeld,
        "gedempt_tot": iso(r.gedempt_tot),
        "aangemaakt_door": r.aangemaakt_door,
        "aangemaakt_op": iso(r.aangemaakt_op),
        "bijgewerkt_door": r.bijgewerkt_door,
        "bijgewerkt_op": iso(r.bijgewerkt_op),
        "versie": r.version,
    }


def instance_dict(i: AlertInstance, rule: AlertRule | None, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    return {
        "id": str(i.id),
        "regel": None if rule is None else {"id": str(rule.id), "naam": rule.naam, "ernst": rule.ernst},
        "onderwerp_type": i.onderwerp_type,
        "onderwerp_id": i.onderwerp_id,
        "series_id": i.series_id,
        "toestand": i.toestand,
        "sinds": iso(i.sinds),
        "actief_sinds": iso(i.firing_sinds) if i.toestand == "firing" else None,
        "laatste_waarde": i.laatste_waarde,
        "laatste_meting": iso(i.laatste_sample_op),
        "laatste_evaluatie": iso(i.laatste_eval_op),
        "gegevens_verouderd": i.gegevens_verouderd,
        "gedempt_tot": iso(i.gedempt_tot) if i.gedempt_tot and i.gedempt_tot > now else None,
        "gedempt_door": i.gedempt_door if i.gedempt_tot and i.gedempt_tot > now else None,
        "meldingen": i.melding_teller,
        "laatst_gemeld_op": iso(i.laatst_gemeld_op),
        "laatst_opgelost_op": iso(i.laatst_opgelost_op),
    }
