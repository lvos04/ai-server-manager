"""Readback (B01-005, 05_OPERATIES): de actuele toestand van de bron achter een incident, teruggelezen door de Hub.

``toestand`` ∈ ``actief`` | ``hersteld`` | ``onbekend``. ``autoritatief`` betekent dat de Hub deze bron zelf meet en een
``hersteld`` het incident mag sluiten (bv. noodaccount geroteerd, monitoringbron weer ok). Bij events van andere
diensten weet de Hub de toestand meestal niet: dan ``onbekend`` — en ``onbekend`` sluit nooit iets.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.models import (
    AlertInstance,
    Incident,
    InventoryRun,
    MonitorSource,
    NotificationChannel,
    SelfBackup,
    User,
)
from hub.timeutil import iso


def _uuid(v: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(v)
    except ValueError:
        return None


def _out(toestand: str, bron: str, gemeten: datetime | None, detail: str, autoritatief: bool = False) -> dict[str, Any]:
    return {
        "toestand": toestand,
        "autoritatief": autoritatief and toestand == "hersteld",
        "bron": bron,
        "gemeten_op": iso(gemeten),
        "detail": detail,
    }


def _alert(db: Session, inc: Incident) -> dict[str, Any]:
    parts = inc.vingerafdruk.split(":alert:", 1)
    rule_s = parts[1].split(":", 1)[0] if len(parts) == 2 else ""
    rid = _uuid(rule_s)
    if rid is None:
        return _out("onbekend", "alert", None, "alertregel onbekend")
    inst = db.scalars(
        select(AlertInstance).where(
            AlertInstance.rule_id == rid,
            AlertInstance.onderwerp_type == inc.onderwerp_type,
            AlertInstance.onderwerp_id == inc.onderwerp_id,
        )
    ).first()
    if inst is None:
        return _out("onbekend", "alert", None, "alert niet (meer) gevonden")
    if inst.gegevens_verouderd:
        return _out("onbekend", "alert", inst.laatste_sample_op, "geen verse meting (verouderd telt nooit als herstel)")
    if inst.toestand in ("firing", "pending"):
        return _out("actief", "alert", inst.laatste_sample_op, f"alert {inst.toestand}, waarde {inst.laatste_waarde}")
    return _out("hersteld", "alert", inst.laatste_sample_op, f"alert ok, waarde {inst.laatste_waarde}")


def state(db: Session, settings: Settings, inc: Incident, now: datetime) -> dict[str, Any]:
    soort = inc.soort
    if soort.startswith("alert."):
        return _alert(db, inc)
    if soort == "monitoring.bron_storing":
        src = db.get(MonitorSource, _uuid(inc.onderwerp_id)) if _uuid(inc.onderwerp_id) else None
        if src is None or src.laatste_status is None:
            return _out("onbekend", "monitoringbron", None, "bron onbekend of nog niet gepeild")
        if src.laatste_status == "ok" and src.laatste_ok is not None and src.laatste_ok > inc.laatste_op:
            return _out("hersteld", "monitoringbron", src.laatste_ok, "bron weer ok", autoritatief=True)
        if src.laatste_status == "fout":
            return _out("actief", "monitoringbron", src.laatste_poging, f"bron faalt: {src.laatste_reden}")
        return _out("onbekend", "monitoringbron", src.laatste_poging, "geen nieuwere geslaagde peiling")
    if soort == "melding.kanaal_storing":
        ch = db.get(NotificationChannel, _uuid(inc.onderwerp_id)) if _uuid(inc.onderwerp_id) else None
        if ch is None or ch.laatste_status is None:
            return _out("onbekend", "meldingskanaal", None, "kanaal onbekend of nog niet gebruikt")
        if ch.laatste_status == "ok" and ch.laatste_op is not None and ch.laatste_op > inc.laatste_op:
            return _out("hersteld", "meldingskanaal", ch.laatste_op, "melding weer afgeleverd", autoritatief=True)
        if ch.laatste_status == "fout":
            return _out("actief", "meldingskanaal", ch.laatste_op, f"kanaal faalt: {ch.laatste_reden}")
        return _out("onbekend", "meldingskanaal", ch.laatste_op, "nog geen nieuwere aflevering")
    if soort == "backup.eigen_mislukt":
        b = db.scalars(select(SelfBackup).order_by(SelfBackup.started_at.desc()).limit(1)).first()
        if b is None:
            return _out("onbekend", "eigen_backup", None, "nog geen export")
        if b.status == "geslaagd" and b.finished_at is not None and b.finished_at > inc.laatste_op:
            return _out("hersteld", "eigen_backup", b.finished_at, "nieuwe export geslaagd", autoritatief=True)
        if b.status == "mislukt":
            return _out(
                "actief", "eigen_backup", b.finished_at or b.started_at, f"laatste export mislukt: {b.reason_code}"
            )
        return _out("onbekend", "eigen_backup", b.started_at, f"laatste export: {b.status}")
    if soort == "nas.inventaris":
        r = db.scalars(select(InventoryRun).order_by(InventoryRun.started_at.desc()).limit(1)).first()
        if r is None:
            return _out("onbekend", "inventaris", None, "nog geen inventaris")
        if r.status == "ok" and r.started_at > inc.laatste_op:
            return _out("hersteld", "inventaris", r.finished_at or r.started_at, "inventaris volledig")
        if r.status in ("partial", "unknown"):
            return _out(
                "actief", "inventaris", r.finished_at or r.started_at, f"inventaris {r.status}: {r.reason_code}"
            )
        return _out("onbekend", "inventaris", r.started_at, f"inventaris {r.status}")
    if soort == "auth.noodlogin":
        user = db.get(User, _uuid(inc.onderwerp_id)) if _uuid(inc.onderwerp_id) else None
        if user is None:
            return _out("onbekend", "noodaccount", None, "noodaccount niet gevonden")
        rotated = (
            not user.break_glass_rotation_required
            and user.totp_confirmed_at is not None
            and (user.break_glass_last_used_at is None or user.updated_at >= user.break_glass_last_used_at)
        )
        if rotated:
            return _out("hersteld", "noodaccount", user.updated_at, "noodaccount geroteerd en bevestigd", True)
        return _out("actief", "noodaccount", user.break_glass_last_used_at, "rotatie van het noodaccount nog nodig")
    return _out("onbekend", inc.bron, None, "de Hub kan deze bron niet zelf teruglezen")
