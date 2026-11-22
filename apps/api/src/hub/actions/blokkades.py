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
from asm_policy import checkpoint as cpmod
from asm_policy.engine import Classification, class_at_least
from asm_policy.loader import ActieDef
from asm_policy.params import expected_image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.models import ActionRequest, HubSetting
from hub.onboarding import gates as gates_mod
from hub.timeutil import iso, utcnow

NOODSTOP_KEY = "acties.noodstop"
GATE_DICHT = ("BLK-GATE", "gate_dicht", "Een gate die deze actie nodig heeft, is niet open.")
DATABASE_HERSTEL = (
    "BLK-EX15",
    "database_herstel_vereist",
    "Na deze versie liep een databasemigratie (of de tag-terugval is onveilig): alleen de image terugzetten kan de "
    "data beschadigen. Terugzetten kan alleen samen met de database uit het checkpoint, via de eigenaar.",
)
HERKOMST_ONBEKEND = (
    "BLK-HERKOMST",
    "herkomst_onbekend",
    "Dit herstelpunt is geen eigen, uitgevoerde bijwerking van deze app; de herkomst is onbekend.",
)
APP_WIJZIGINGEN = ("app.update", "app.rollback")
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


def _app_datasets(db: Session, settings: Settings, app: str) -> list[str] | None:
    """De datasets van deze app volgens de verse inventaris (opslag → koppelpunt, plus elke dataset die daaronder is
    aangekoppeld), of ``None`` als dat onbekend is. Geen opslag telt alleen bij een draaiende app (positief bewijs uit
    de werklast); een gestopte app toont geen koppelingen, dus dan onbekend (R-HARDE-EIS-1)."""
    from hub.routers.backups import coverage_inputs

    inp = coverage_inputs(db, settings)
    if inp.apps.get("status") != "ok" or inp.datasets.get("status") != "ok":
        return None
    mounts = [(str(d["mountpoint"]), str(d["naam"])) for d in inp.datasets.get("data") or [] if d.get("mountpoint")]
    rij = next((a for a in inp.apps.get("data") or [] if a.get("naam") == app), None)
    if rij is None:
        return None
    uit: list[str] = []
    for m in rij.get("opslag") or []:
        if m.get("type") == "tmpfs":
            continue
        lijst = cpmod.onder_pad(str(m.get("bron") or ""), mounts)
        if lijst is None:
            return None
        uit.extend(d for d in lijst if d not in uit)
    if not uit and rij.get("staat") != "RUNNING":
        return None
    return uit


def _eigen_wijzigingen(db: Session, req: ActionRequest) -> list[ActionRequest]:
    """Eigen bijwerkingen en terugzettingen van dit doel die naar de executor gingen, op volgorde."""
    return list(
        db.scalars(
            select(ActionRequest)
            .where(
                ActionRequest.doel_sleutel == req.doel_sleutel,
                ActionRequest.action_id.in_(APP_WIJZIGINGEN),
                ActionRequest.gestart_op.is_not(None),
                ActionRequest.id != req.id,
            )
            .order_by(ActionRequest.gestart_op)
        )
    )


def verified_checkpoint(
    db: Session, settings: Settings, req: ActionRequest, *, now: datetime | None = None
) -> tuple[str | None, str]:
    """``(id, reden)``: het id van een eigen, geverifieerd app-checkpoint, of ``None`` met de reden (S-P2-050f).

    Een checkpoint is een eigen ``zfs.snapshot.create`` die de executor uitvoerde en teruglas (aanwezig, met
    ``createtxg``, zonder ``checkpoint_niet_vastgelegd``), hooguit een uur oud, gemaakt na de laatste eigen bijwerking
    van deze app, op een dataset die alle opslag van de app dekt. Een id dat een gebruiker of de AI opgeeft, is nooit
    bewijs. De executor controleert bij de uitvoering zelf opnieuw (bestaan, ``createtxg``, dekking uit
    ``app.config``)."""
    if req.action_id not in APP_WIJZIGINGEN:
        return None, "geen_app_wijziging"
    now = now or utcnow()
    app = req.doel_sleutel.removeprefix("app:")
    nodig = _app_datasets(db, settings, app)
    if nodig is None:
        return None, "dekking_onbekend"
    params = req.parameters if isinstance(req.parameters, dict) else {}
    if "herstel_van" in params:
        # Ook de opslag van de waarden die het terugzetten schrijft (R-HARDE-EIS-4): de executor meldde die datasets
        # bij de bijwerking waarvan het recept is.
        bron = next((r for r in _eigen_wijzigingen(db, req) if str(r.id) == str(params["herstel_van"])), None)
        bron_rb = bron.resultaat.get("readback") if bron is not None and isinstance(bron.resultaat, dict) else None
        extra = bron_rb.get("herstel_datasets") if isinstance(bron_rb, dict) else None
        if isinstance(extra, list):
            nodig = [*nodig, *(str(d) for d in extra if str(d) not in nodig)]
        # shortcut: een recept van vóór deze versie meldt zijn datasets niet; dan toetst alleen de executor (die het
        # recept zelf leest en een ongedekte bestemming weigert). Vervalt als zulke recepten er niet meer zijn.
    vanaf = now - timedelta(seconds=cpmod.CHECKPOINT_MAX_SECONDEN)
    vorige = _eigen_wijzigingen(db, req)
    if vorige:
        # Na het einde van de laatste eigen wijziging (``gestart_op`` is op hele seconden afgerond; de laatste
        # bijwerking van het verzoek ligt altijd ná de werkelijke start).
        vanaf = max(vanaf, *(t for t in (vorige[-1].gestart_op, vorige[-1].bijgewerkt_op) if t is not None))
    kandidaten = db.scalars(
        select(ActionRequest)
        .where(
            ActionRequest.action_id == "zfs.snapshot.create",
            ActionRequest.status == "uitgevoerd",
            ActionRequest.uitgevoerd_op.is_not(None),
            ActionRequest.uitgevoerd_op > vanaf,
        )
        .order_by(ActionRequest.uitgevoerd_op.desc())
    )
    for k in kandidaten:
        res = k.resultaat if isinstance(k.resultaat, dict) else {}
        rb_ruw = res.get("readback")
        rb: dict[str, Any] = rb_ruw if isinstance(rb_ruw, dict) else {}
        if not (rb.get("aanwezig") is True and rb.get("createtxg")) or "checkpoint_niet_vastgelegd" in (
            res.get("waarschuwingen") or []
        ):
            continue
        # Per dataset een eigen, teruggelezen snapshot van die actie (R-HARDE-EIS-2); het verzoek zelf telt niet.
        leden = rb.get("leden")
        if isinstance(leden, dict) and all(d in leden for d in nodig):
            return str(k.id), "geverifieerd"
    return None, "geen_passend_checkpoint"


def ex15(db: Session, req: ActionRequest) -> list[dict[str, Any]]:
    """EX15 bij de Hub, uit de eigen administratie (ADR-0032 besluit 8): geen terugzetten op alleen de image na een
    gemelde migratie, en geen herstelpunt dat geen eigen uitgevoerde wijziging van dit doel is. Bij elke bijwerking en
    terugzetting: een doel (image, digest of catalogusversie) dat vóór een gemelde migratie draaide, vereist
    databaseherstel, ongeacht de actienaam (R-HARDE-EIS-5)."""
    if req.action_id not in APP_WIJZIGINGEN:
        return []
    eigen = [r for r in _eigen_wijzigingen(db, req) if r.status == "uitgevoerd"]
    params = req.parameters if isinstance(req.parameters, dict) else {}
    historie = [(_migratie(r.parameters), cpmod.identiteiten(_huidig(r))) for r in eigen]
    doel = cpmod.doel_identiteiten(expected_image(params), params.get("catalog_version"))
    if cpmod.terug_voor_migratie(historie, doel):
        return [_blok(DATABASE_HERSTEL)]
    if req.action_id != "app.rollback":
        return []
    if "herstel_van" in params:
        idx = next((i for i, r in enumerate(eigen) if str(r.id) == str(params["herstel_van"])), None)
        if idx is None:
            return [_blok(HERKOMST_ONBEKEND)]
        eigen = eigen[idx:]
    # shortcut: bij een catalogusrollback telt elke gemelde migratie van dit doel (de Hub kent de vertrekversie niet
    # per verzoek); de executor kijkt preciezer vanaf de laatste update die van de doelversie vertrok. Versie 2.
    if any(_migratie(r.parameters) for r in eigen):
        return [_blok(DATABASE_HERSTEL)]
    return []


def _huidig(r: ActionRequest) -> dict[str, Any]:
    """Wat er vóór die wijziging draaide, zoals de preview het toonde (``app_state`` uit de eigen inventaris)."""
    huidig = r.preview.get("huidig") if isinstance(r.preview, dict) else None
    return huidig if isinstance(huidig, dict) else {}


def _migratie(params: Any) -> bool:
    up = params.get("upgrade") if isinstance(params, dict) else None
    return isinstance(up, dict) and (up.get("migrations") is True or up.get("tag_only_rollback_safe") is False)


def _blok(t: tuple[str, str, str]) -> dict[str, Any]:
    return {"id": t[0], "code": t[1], "reden": t[2], "details": []}


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
        checkpoint, reden = verified_checkpoint(db, settings, req, now=now)
        if not checkpoint:
            r = policy.dynamisch["checkpoint"]
            out.append({"id": r.id, "code": r.code, "reden": r.reden_nl, "details": [reden]})
    out += ex15(db, req)
    return out, checkpoint
