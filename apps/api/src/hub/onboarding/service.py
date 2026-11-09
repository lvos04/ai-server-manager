"""Statusovergangen en metingen voor de besluiten D01–D18.

- ``Open`` → ``Ingevuld``: waarde ingevuld en gevalideerd tegen het schema.
- ``Ingevuld`` → ``Getest``: alleen door een echte meting (TrueNAS-readback, D01/D02/D03/D06/D07) of een expliciet
  bewijsrecord met resultaat ``geslaagd``. D05 vereist daarnaast geregistreerde hersteltests (foto én database).
- Waarde wijzigen na ``Getest`` → terug naar ``Ingevuld`` (de test hoort bij de oude waarde).
- ``Geblokkeerd``/``N.v.t.`` alleen met reden; ``N.v.t.`` alleen waar toegestaan. D10 is een vast besluit.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.inventory.collector import CollectResult
from hub.inventory.store import save_run
from hub.models import Decision, RestoreTest
from hub.onboarding.catalog import BY_ID, D10_VAST, DECISIONS, validate_value
from hub.timeutil import iso, utcnow
from hub.truenas.connection import run_collect
from hub.truenas.messages import advice, message
from hub.vault import Vault

MEASURABLE = ("D01", "D02", "D03", "D06", "D07")
_MEASURE_KINDS: dict[str, tuple[str, ...]] = {
    "D01": ("system",),
    "D02": ("pools", "datasets"),
    "D03": ("system",),
    "D06": ("pools", "smart"),
    "D07": ("apps",),
}


class DecisionError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details or {}


def seed(db: Session) -> None:
    """Zorg dat alle besluiten bestaan; alleen D10 (vast besluit van de gebruiker) is vooraf ingevuld."""
    existing = set(db.scalars(select(Decision.id)))
    now = utcnow()
    for d in DECISIONS:
        if d.id in existing:
            continue
        row = Decision(
            id=d.id,
            titel=d.titel,
            wat_vastleggen=d.wat_vastleggen,
            gate=d.gate,
            status="Open",
            waarde=None,
            bewijs=[],
            reden="",
            version=1,
            updated_at=now,
        )
        if d.vast:
            row.status = "Ingevuld"
            row.waarde = dict(D10_VAST)
            row.waarde_bron = "vast"
            row.ingevuld_door = "gebruiker (vast besluit)"
            row.ingevuld_op = now
        db.add(row)
    db.flush()


def to_dict(row: Decision, *, with_schema: bool = False) -> dict[str, Any]:
    d = BY_ID[row.id]
    out: dict[str, Any] = {
        "id": row.id,
        "titel": row.titel,
        "wat_vastleggen": row.wat_vastleggen,
        "gate": row.gate,
        "status": row.status,
        "waarde": row.waarde,
        "waarde_bron": row.waarde_bron,
        "bewijs": row.bewijs or [],
        "reden": row.reden or "",
        "ingevuld_door": row.ingevuld_door,
        "ingevuld_op": iso(row.ingevuld_op),
        "getest_door": row.getest_door,
        "getest_op": iso(row.getest_op),
        "laatste_meting": row.laatste_meting,
        "meetbaar": d.meetbaar,
        "nvt_toegestaan": d.nvt_toegestaan,
        "vast": d.vast,
        "version": row.version,
        "updated_at": iso(row.updated_at),
    }
    if with_schema:
        out["schema"] = d.schema.model_json_schema()
    return out


def _bump(row: Decision) -> None:
    row.version += 1
    row.updated_at = utcnow()


def _require_mutable(row: Decision) -> None:
    if BY_ID[row.id].vast:
        raise DecisionError(
            409, "decision_fixed", f"{row.id} is een vast besluit van de gebruiker en kan niet wijzigen."
        )


def set_value(row: Decision, value: Any, actor: str) -> None:
    _require_mutable(row)
    normalized = validate_value(row.id, value)
    row.waarde = normalized
    row.waarde_bron = "gebruiker"
    row.status = "Ingevuld"
    row.reden = ""
    row.ingevuld_door, row.ingevuld_op = actor, utcnow()
    row.getest_door, row.getest_op = None, None
    _bump(row)


def set_status(row: Decision, status: str, reden: str, actor: str) -> None:
    _require_mutable(row)
    d = BY_ID[row.id]
    reden = reden.strip()
    if status == "Open":
        row.waarde, row.waarde_bron, row.reden = None, None, ""
        row.ingevuld_door = row.ingevuld_op = None
        row.getest_door = row.getest_op = None
    elif status in ("Geblokkeerd", "N.v.t."):
        if len(reden) < 5:
            raise DecisionError(422, "reason_required", "Geef een reden (minstens 5 tekens).")
        if status == "N.v.t." and not d.nvt_toegestaan:
            raise DecisionError(409, "not_applicable_forbidden", f"{row.id} kan niet op N.v.t. worden gezet.")
        row.reden = reden
        row.getest_door = row.getest_op = None
    else:
        raise DecisionError(
            422, "invalid_status", "Status Ingevuld/Getest ontstaat alleen door invullen, meten of bewijs vastleggen."
        )
    row.status = status
    row.ingevuld_door = actor if status != "Open" else None
    _bump(row)


def _restore_evidence(db: Session) -> tuple[bool, bool]:
    rows = db.scalars(select(RestoreTest).where(RestoreTest.resultaat == "geslaagd"))
    soorten = {r.soort for r in rows}
    return "foto" in soorten, "database" in soorten


def add_evidence(db: Session, row: Decision, ev: dict[str, Any], actor: str) -> dict[str, Any]:
    _require_mutable(row)
    if row.status not in ("Ingevuld", "Getest"):
        raise DecisionError(
            409, "decision_not_filled", "Vul het besluit eerst in; bewijs hoort bij een ingevulde waarde."
        )
    record = {
        "id": str(uuid.uuid4()),
        "bron": "gebruiker",
        "soort": ev["soort"],
        "omschrijving": ev["omschrijving"],
        "referentie": ev.get("referentie") or "",
        "resultaat": ev["resultaat"],
        "uitgevoerd_op": ev["uitgevoerd_op"].isoformat()
        if isinstance(ev["uitgevoerd_op"], date)
        else str(ev["uitgevoerd_op"]),
        "vastgelegd_door": actor,
        "vastgelegd_op": iso(utcnow()),
        "hoort_bij_versie": row.version,
    }
    if ev["resultaat"] == "geslaagd":
        if row.id == "D05":
            foto, database = _restore_evidence(db)
            val = row.waarde or {}
            if not (foto and database and val.get("foto_hersteld") and val.get("db_export_hersteld")):
                raise DecisionError(
                    409,
                    "restore_evidence_missing",
                    "D05 kan pas Getest zijn als er een geslaagde hersteltest van een foto én van een database-export "
                    "is vastgelegd (Back-ups → Hersteltests) en de waarde beide als hersteld markeert.",
                    {"foto": foto, "database": database},
                )
        row.status = "Getest"
        row.getest_door, row.getest_op = actor, utcnow()
    elif row.status == "Getest":
        row.status = "Ingevuld"
        row.getest_door = row.getest_op = None
    row.bewijs = [*(row.bewijs or []), record]
    _bump(row)
    return record


@dataclass
class Measurement:
    status: str  # geslaagd | afwijking | mislukt | voorstel
    reason_code: str | None
    melding: str
    details: dict[str, Any]
    run_id: str | None


def _evidence_from_measurement(row: Decision, m: Measurement, method: str | None, actor: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "bron": "meting",
        "soort": "truenas_readback",
        "omschrijving": m.melding,
        "referentie": f"inventory_run:{m.run_id}" if m.run_id else "",
        "resultaat": "geslaagd" if m.status == "geslaagd" else "mislukt",
        "methode": method,
        "uitgevoerd_op": iso(utcnow()),
        "vastgelegd_door": actor,
        "vastgelegd_op": iso(utcnow()),
        "hoort_bij_versie": row.version + 1,
    }


def _compare(row: Decision, res: CollectResult) -> tuple[Measurement, dict[str, Any] | None, str | None]:
    """Vergelijk de meting met de waarde. Geeft (meting, nieuwe waarde uit meting of None, methode)."""
    kind = {k.kind: k for k in res.kinds}
    run_id = None
    if row.id in ("D01", "D03"):
        sysk = kind["system"]
        if sysk.status != "ok":
            return Measurement("mislukt", sysk.reason_code, sysk.message, {}, run_id), None, sysk.method
        measured = str(sysk.data.get("versie") or "")
        if row.id == "D03":
            return (
                Measurement(
                    "geslaagd",
                    None,
                    f"Verbonden en aangemeld bij TrueNAS ({measured}) op het D03-adres.",
                    {"nas_versie": measured, "tls_modus": res.tls_mode},
                    run_id,
                ),
                None,
                "auth.login_with_api_key",
            )
        if not measured:
            return Measurement("mislukt", "protocol_error", "Versie niet uitgelezen.", {}, run_id), None, sysk.method
        current = (row.waarde or {}).get("versie")
        if current and current != measured:
            return (
                Measurement(
                    "afwijking",
                    None,
                    f"Ingevulde versie '{current}' wijkt af van gemeten '{measured}'.",
                    {"ingevuld": current, "gemeten": measured},
                    run_id,
                ),
                None,
                sysk.method,
            )
        return (
            Measurement(
                "geslaagd", None, f"Versie gemeten via system.version: {measured}.", {"gemeten": measured}, run_id
            ),
            None if current else {"versie": measured},
            sysk.method,
        )
    if row.id == "D02":
        pk, dk = kind["pools"], kind["datasets"]
        for k in (pk, dk):
            if k.status != "ok":
                return Measurement("mislukt", k.reason_code, k.message, {}, run_id), None, k.method
        pools = {p["naam"] for p in pk.data}
        dsets = {d["naam"] for d in dk.data}
        if row.waarde is None:
            return (
                Measurement(
                    "voorstel",
                    None,
                    "Gemeten pools en datasets; kies zelf de appdata- en mediapaden.",
                    {"pools": sorted(pools), "datasets": sorted(dsets)[:500]},
                    run_id,
                ),
                None,
                dk.method,
            )
        val = row.waarde
        missing_pools = [p for p in val.get("pools", []) if p not in pools]
        missing_ds = [d for d in [*val.get("appdata_datasets", []), *val.get("media_datasets", [])] if d not in dsets]
        if missing_pools or missing_ds:
            return (
                Measurement(
                    "afwijking",
                    None,
                    "Niet alle opgegeven pools/datasets bestaan op de NAS.",
                    {"ontbrekende_pools": missing_pools, "ontbrekende_datasets": missing_ds},
                    run_id,
                ),
                None,
                dk.method,
            )
        return (
            Measurement("geslaagd", None, "Alle opgegeven pools en datasets bestaan op de NAS.", {}, run_id),
            None,
            dk.method,
        )
    if row.id == "D06":
        pk, sk = kind["pools"], kind["smart"]
        if pk.status != "ok":
            return Measurement("mislukt", pk.reason_code, pk.message, {}, run_id), None, pk.method
        smart_ok: bool | None = None
        if sk.status == "ok":
            statuses = [(d.get("laatste_test") or {}).get("status") for d in sk.data]
            smart_ok = all(s == "SUCCESS" for s in statuses) if statuses and all(statuses) else None
        value: dict[str, Any] = {
            "pools": [
                {
                    "naam": p["naam"],
                    "status": p["status"] or "ONBEKEND",
                    "gezond": bool(p["gezond"]),
                    "gebruik_pct": p["gebruik_pct"],
                    "laatste_scrub": p["scrub"]["laatst_beeindigd"],
                    "scrub_fouten": p["scrub"]["fouten"] if isinstance(p["scrub"]["fouten"], int) else None,
                }
                for p in pk.data
            ],
            "smart_ok": smart_ok,
            "snapshot_capaciteit_ok": None,
        }
        pool_rows: list[dict[str, Any]] = value["pools"]
        if not pool_rows:
            return Measurement("mislukt", "protocol_error", "Geen pools gevonden.", {}, run_id), None, pk.method
        unhealthy = [p["naam"] for p in pool_rows if not p["gezond"]]
        melding = "Poolstatus gemeten via pool.query." + (f" Niet gezond: {', '.join(unhealthy)}." if unhealthy else "")
        return (
            Measurement(
                "geslaagd", None, melding, {"niet_gezond": unhealthy, "smart_bron": sk.reason_code or "ok"}, run_id
            ),
            value,
            pk.method,
        )
    if row.id == "D07":
        ak = kind["apps"]
        if ak.status != "ok":
            return Measurement("mislukt", ak.reason_code, ak.message, {}, run_id), None, ak.method
        apps = [
            {
                "naam": a["naam"],
                "image": (a["images"][0]["image"] if a["images"] else None),
                "versie": a["versie"],
                "staat": a["staat"],
            }
            for a in ak.data
        ]
        if not apps:
            return Measurement("mislukt", "protocol_error", "Geen apps gevonden.", {}, run_id), None, ak.method
        return (
            Measurement("geslaagd", None, f"{len(apps)} apps gemeten via app.query.", {}, run_id),
            {"apps": apps},
            ak.method,
        )
    raise DecisionError(422, "not_measurable", f"{row.id} is niet via TrueNAS meetbaar; leg bewijs vast.")


async def measure(db: Session, vault: Vault, settings: Settings, row: Decision, actor: str) -> Measurement:
    if row.id not in MEASURABLE:
        raise DecisionError(422, "not_measurable", f"{row.id} is niet via TrueNAS meetbaar; leg een bewijsrecord vast.")
    if row.id == "D03" and row.status not in ("Ingevuld", "Getest"):
        raise DecisionError(409, "decision_not_filled", "Vul eerst het NAS-adres (D03) in.")
    if row.status in ("Geblokkeerd", "N.v.t."):
        raise DecisionError(409, "decision_closed", f"{row.id} staat op {row.status}; zet het eerst terug op Open.")
    started = utcnow()
    res = await run_collect(db, vault, settings, _MEASURE_KINDS[row.id])
    run = (
        save_run(db, res, trigger=f"meting:{row.id}", started_at=started)
        if res.reason_code != "not_configured"
        else None
    )
    m, new_value, method = _compare(row, res)
    m.run_id = str(run.id) if run else None
    if m.reason_code and not m.melding:
        m.melding = message(m.reason_code)
    row.laatste_meting = {
        "status": m.status,
        "reason_code": m.reason_code,
        "melding": m.melding,
        "advies": advice(m.reason_code),
        "details": m.details,
        "run_id": m.run_id,
        "gemeten_op": iso(utcnow()),
        "door": actor,
    }
    if m.status == "geslaagd":
        if new_value is not None:
            row.waarde = validate_value(row.id, new_value)
            row.waarde_bron = "meting"
            row.ingevuld_door, row.ingevuld_op = f"meting door {actor}", utcnow()
        row.bewijs = [*(row.bewijs or []), _evidence_from_measurement(row, m, method, actor)]
        row.status = "Getest"
        row.reden = ""
        row.getest_door, row.getest_op = f"meting door {actor}", utcnow()
    elif m.status == "afwijking" and row.status == "Getest":
        row.status = "Ingevuld"
        row.getest_door = row.getest_op = None
    _bump(row)
    return m
