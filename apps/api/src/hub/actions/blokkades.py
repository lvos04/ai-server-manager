"""Dynamische blokkades op de gemeten toestand (contract 1.3 §8, EX11/EX12, B12-006, ADR-0030 punt 11–16).

Statische blokkades (shell, destructief, boiler, …) komen uit het beleid zelf (:mod:`asm_policy.engine`). Dit bestand
voegt toe wat alleen de Hub kan weten:

- **gates**: pool niet gezond of onbekend → ``pool_niet_gezond``; back-upgate niet groen → ``backup_gate_rood``;
  executor niet gekoppeld → ``executor_niet_gekoppeld``; een ander besluit nog niet getest → ``gate_dicht``;
- **noodstop**: een beheerder kan alle uitvoering stilleggen (Hub-instelling ``acties.noodstop``);
- **anti-flap**: afkoeltijd en maximum per uur per (actie, doel) — voor iedereen, niet alleen voor de AI;
- **herstelpunt**: een actie met ``requires_backup`` heeft een geverifieerd herstelpunt (B12) nodig.

Een blokkade geldt óók met goedkeuring; er is geen route om er een weg te klikken. Onbekend telt als geblokkeerd.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from asm_policy import Policy
from asm_policy.engine import Classification, class_at_least
from asm_policy.loader import ActieDef
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.models import ActionRequest, HubSetting
from hub.onboarding import gates as gates_mod
from hub.timeutil import iso, utcnow

NOODSTOP_KEY = "acties.noodstop"
GATE_DICHT = ("BLK-GATE", "gate_dicht", "Een gate die deze actie nodig heeft, is niet open.")
EXECUTOR_LOS = (
    "BLK-EXECUTOR",
    "executor_niet_gekoppeld",
    "De executor is niet gekoppeld; zonder executor wordt er niets op de NAS gewijzigd.",
)


def gate_inputs(db: Session, settings: Settings) -> gates_mod.GateInputs:
    """Dezelfde invoer als het gate-scherm (één waarheid). Aparte naam, zodat tests de gemeten toestand kunnen
    zetten zonder de beoordeling zelf te vervangen."""
    from hub.routers.onboarding import gate_inputs as _gate_inputs

    return _gate_inputs(db, settings)


def verified_checkpoint(db: Session, req: ActionRequest) -> str | None:
    """Het id van een geverifieerd herstelpunt (B12) van de app binnen het RPO, of ``None``.

    App-herstelpunten (B12) bestaan in deze versie nog niet; daarom altijd ``None`` en dus de blokkade
    ``backup_checkpoint_ontbreekt`` voor acties met ``requires_backup``. Een id dat een gebruiker of de AI opgeeft,
    is nooit bewijs: alleen een eigen, geverifieerd record telt.
    """
    return None


def nodige_gates(actie: ActieDef, cls: Classification) -> list[str]:
    out: list[str] = []
    if class_at_least(cls.risk_class, "R2"):
        out.append("r2_r3_acties")
    if cls.opslagmutatie:
        out.append("data_mutatie")
    if actie.action_id == "app.install":
        out.append("deployment")
    if actie.action_id in ("app.update", "app.rollback"):
        out.append("bestaande_app_updates")
    return out


def uit_gates(policy: Policy, uitkomst: list[dict[str, Any]], gate_ids: list[str]) -> list[dict[str, Any]]:
    """Vertaal dichte gates naar blokkades; loopt door afhankelijke gates heen tot de eigenlijke oorzaak."""
    per_id = {g["id"]: g for g in uitkomst}
    gevonden: dict[str, dict[str, Any]] = {}

    def voeg_toe(regel: tuple[str, str, str], tekst: str) -> None:
        rid, code, reden = regel
        item = gevonden.setdefault(code, {"id": rid, "code": code, "reden": reden, "details": []})
        if tekst and tekst not in item["details"]:
            item["details"].append(tekst)

    def dyn(naam: str) -> tuple[str, str, str]:
        r = policy.dynamisch[naam]
        return (r.id, r.code, r.reden_nl)

    def loop(gid: str, in_backup: bool, diepte: int) -> None:
        g = per_id.get(gid)
        if g is None or diepte > 8:
            voeg_toe(GATE_DICHT, f"Gate '{gid}' is onbekend.")
            return
        if g["status"] == "toegestaan":
            return
        binnen = in_backup or gid == "backup_gate"
        for r in g["redenen"]:
            tekst = str(r.get("tekst") or "")
            if r.get("soort") == "gate":
                loop(str(r.get("id")), binnen, diepte + 1)
            elif binnen:
                voeg_toe(dyn("backup"), tekst)
            elif r.get("soort") == "meting" and r.get("id") == "pools":
                voeg_toe(dyn("pool"), tekst)
            elif r.get("soort") == "executor":
                voeg_toe(EXECUTOR_LOS, tekst)
            else:
                voeg_toe(GATE_DICHT, tekst)

    for gid in gate_ids:
        loop(gid, False, 0)
    return list(gevonden.values())


# ------------------------------------------------------------------ noodstop
def noodstop(db: Session) -> dict[str, Any]:
    row = db.get(HubSetting, NOODSTOP_KEY)
    waarde = row.waarde if row is not None else {}
    return {
        "actief": bool(waarde.get("actief")),
        "reden": waarde.get("reden") or None,
        "sinds": waarde.get("sinds") or None,
        "door": waarde.get("door") or None,
    }


def zet_noodstop(db: Session, *, actief: bool, reden: str | None, door: str) -> dict[str, Any]:
    now = utcnow()
    waarde = {"actief": actief, "reden": reden or None, "sinds": iso(now), "door": door}
    row = db.get(HubSetting, NOODSTOP_KEY)
    if row is None:
        db.add(HubSetting(sleutel=NOODSTOP_KEY, waarde=waarde, gewijzigd_op=now, gewijzigd_door=door))
    else:
        row.waarde, row.gewijzigd_op, row.gewijzigd_door = waarde, now, door
    db.flush()
    return noodstop(db)


# ------------------------------------------------------------------ anti-flap
def _tempo(db: Session, policy: Policy, actie: ActieDef, doel_sleutel: str, now: datetime) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    basis = (
        ActionRequest.action_id == actie.action_id,
        ActionRequest.doel_sleutel == doel_sleutel,
        ActionRequest.gestart_op.is_not(None),
    )
    if actie.cooldown_seconden > 0:
        laatste = db.scalar(select(func.max(ActionRequest.gestart_op)).where(*basis))
        if laatste is not None:
            tot = laatste + timedelta(seconds=actie.cooldown_seconden)
            if tot > now:
                r = policy.dynamisch["cooldown"]
                out.append(
                    {
                        "id": r.id,
                        "code": r.code,
                        "reden": r.reden_nl,
                        "details": [f"Afkoeltijd {actie.cooldown_seconden} s; weer mogelijk vanaf {iso(tot)}."],
                        "tot": iso(tot),
                    }
                )
    if actie.max_per_uur > 0:
        aantal = db.scalar(
            select(func.count())
            .select_from(ActionRequest)
            .where(*basis, ActionRequest.gestart_op > now - timedelta(hours=1))
        )
        if int(aantal or 0) >= actie.max_per_uur:
            r = policy.dynamisch["frequentie"]
            out.append(
                {
                    "id": r.id,
                    "code": r.code,
                    "reden": r.reden_nl,
                    "details": [f"Maximaal {actie.max_per_uur} per uur voor dit doel; nu {int(aantal or 0)}."],
                }
            )
    return out


# ------------------------------------------------------------------ alles samen
def dynamisch(
    db: Session,
    settings: Settings,
    policy: Policy,
    actie: ActieDef,
    cls: Classification,
    req: ActionRequest,
    *,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """``(blokkades, backup_checkpoint_id)`` voor dit moment. Een lege lijst betekent: nu niets in de weg."""
    now = now or utcnow()
    out: list[dict[str, Any]] = []
    stop = noodstop(db)
    if stop["actief"]:
        r = policy.dynamisch["noodstop"]
        out.append(
            {"id": r.id, "code": r.code, "reden": r.reden_nl, "details": [str(stop["reden"])] if stop["reden"] else []}
        )
    nodig = nodige_gates(actie, cls)
    if nodig:
        out += uit_gates(policy, gates_mod.evaluate(gate_inputs(db, settings)), nodig)
    out += _tempo(db, policy, actie, req.doel_sleutel, now)
    checkpoint: str | None = None
    if cls.requires_backup:
        checkpoint = verified_checkpoint(db, req)
        if not checkpoint:
            r = policy.dynamisch["checkpoint"]
            out.append({"id": r.id, "code": r.code, "reden": r.reden_nl, "details": []})
    return out, checkpoint
