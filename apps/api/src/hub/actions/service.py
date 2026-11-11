"""Acties voorstellen, goedkeuren en uitvoeren (contract 1.3 §8, B01-007, B01-003; ADR-0030).

Stroom: voorstel → deterministische classificatie (``risk_claim`` wordt genegeerd) → eigen readback van het doel →
preview met ``preview_hash`` → bij R2/R3 een goedkeuring die vastzit aan preview, ETag en beleid → vlak vóór verzending
alles opnieuw → ondertekend ``ExecutionRequest`` naar de executor → uitkomst eerlijk vastleggen.

Vaste regels in dit bestand:

- De Hub voert zelf niets uit op de NAS; hij leest alleen (alleen-lezen-sleutel) en stuurt een ondertekend verzoek.
- Verandert een gebonden veld tussen goedkeuring en uitvoering, dan vervalt de goedkeuring (EX19).
- De eenmalige nonce van een goedkeuring wordt atomair verbruikt vóór verzending (EX20); er is geen tweede poging.
- Een storing of onduidelijk antwoord is nooit een succes: de status wordt ``onbekend`` tot het journaal van de
  executor uitsluitsel geeft. De Hub herhaalt een uitvoering nooit vanzelf.
- Parameterwaarden komen niet in de audit, de events of de API-antwoorden (alleen hun SHA-256 en de preview).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, NoReturn

from asm_policy import Policy, execreq
from asm_policy.engine import Classification, class_at_least, classify
from asm_policy.loader import ActieDef
from asm_policy.params import validate_parameters, validate_target, vault_refs
from asm_policy.verify import check_decision, check_envelope
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from hub import audit, servicecalls
from hub.actions import blokkades as blok_mod
from hub.actions.beleid import get_policy
from hub.actions.doel import Doel, DoelOnbekend, lees_doel
from hub.actions.preview import SCHEMA, bouw
from hub.config import Settings
from hub.deps import Principal
from hub.errors import HubError
from hub.events.envelope import emit
from hub.keys import KeyRing
from hub.models import ActionRequest, Approval, Notification, NotificationChannel, Service
from hub.monitoring.alerts import ERNST_RANK
from hub.registry import EXECUTOR_APP_ID, service_base_url
from hub.security import Role
from hub.timeutil import iso, utcnow
from hub.vault import Vault

OPEN = ("wacht_op_goedkeuring", "klaar", "goedgekeurd")
REQUEST_TTL = 300  # geldigheid van één ExecutionRequest (s); de executor weigert daarna
ANTWOORD_MARGE = 60  # extra leestijd bovenop de tijdslimiet van de actie (s)
STATUSSEN = (
    "wacht_op_goedkeuring",
    "klaar",
    "goedgekeurd",
    "afgewezen",
    "geweigerd",
    "bezig",
    "uitgevoerd",
    "mislukt",
    "afwijking",
    "onbekend",
    "verlopen",
)


AUDIT_WOORD = {"uitgevoerd": "succeeded", "onbekend": "unknown", "afwijking": "deviated"}


class Bewaard(HubError):
    """Een foutantwoord waarbij de toestandswijziging blijft staan (bv. een vervallen goedkeuring). De route legt het
    antwoord idempotent vast en commit; een gewone ``HubError`` laat de database ongemoeid."""


def _nu() -> datetime:
    return utcnow().replace(microsecond=0)


# ------------------------------------------------------------------ weergave
def huidige_goedkeuring(db: Session, req: ActionRequest) -> Approval | None:
    """De open goedkeuring van dit verzoek (hooguit één); anders de laatst afgesloten.

    Tijdstippen zijn op hele seconden: twee goedkeuringen in dezelfde seconde (vervallen en meteen opnieuw
    goedgekeurd) mogen nooit door toeval worden verwisseld. Daarom gaat een open goedkeuring altijd voor en is de
    volgorde daarna volledig bepaald (gebruikt vóór vervallen)."""
    rows = list(db.scalars(select(Approval).where(Approval.request_id == req.id)))
    if not rows:
        return None
    return max(
        rows,
        key=lambda a: (
            a.used_at is None and a.vervallen_op is None,
            a.approved_at,
            a.used_at is not None,
            a.used_at or a.vervallen_op or a.approved_at,
            str(a.id),
        ),
    )


def _goedkeuring_dict(ap: Approval) -> dict[str, Any]:
    # De eenmalige nonce komt nooit in een antwoord: hij is alleen bedoeld voor het ondertekende verzoek.
    return {
        "approval_id": str(ap.id),
        "approved_by": ap.approved_by,
        "approved_at": iso(ap.approved_at),
        "expires_at": iso(ap.expires_at),
        "preview_hash": ap.preview_hash,
        "resource_etag": ap.resource_etag,
        "policy_hash": ap.policy_hash,
        "risk_class": ap.risk_class,
        "backup_checkpoint_id": ap.backup_checkpoint_id,
        "gebruikt_op": iso(ap.used_at),
        "vervallen_op": iso(ap.vervallen_op),
        "vervallen_reden": ap.vervallen_reden,
    }


def weergave(db: Session, req: ActionRequest) -> dict[str, Any]:
    ap = huidige_goedkeuring(db, req)
    return {
        "request_id": str(req.id),
        "status": req.status,
        "action_id": req.action_id,
        "target": req.target,
        "parameters_sha256": (req.preview or {}).get("parameters_sha256"),
        "reason": req.reden,
        "actor": {"type": req.actor_type, "id": req.actor_id},
        "evidence_ids": req.evidence_ids,
        "risk_class": req.risk_class,
        "risk_claim": req.risk_claim,
        "risk_claim_genegeerd": req.risk_claim is not None,
        "rule_ids": req.rule_ids,
        "goedkeuring_nodig": class_at_least(req.risk_class, "R2"),
        "policy_hash": req.policy_hash,
        "uitvoerder": req.uitvoerder,
        "resource_etag": req.resource_etag or None,
        "preview_hash": req.preview_hash or None,
        "preview": req.preview if req.preview_hash else None,
        "blokkades": req.blokkades,
        "goedkeuring": _goedkeuring_dict(ap) if ap is not None else None,
        "resultaat": req.resultaat,
        "aangemaakt_op": iso(req.aangemaakt_op),
        "bijgewerkt_op": iso(req.bijgewerkt_op),
        "geldig_tot": iso(req.geldig_tot),
        "gestart_op": iso(req.gestart_op),
        "uitgevoerd_op": iso(req.uitgevoerd_op),
    }


def haal(db: Session, request_id: uuid.UUID, *, vergrendel: bool = False) -> ActionRequest:
    """Het verzoek; met ``vergrendel`` ook de rij (``SELECT … FOR UPDATE``) tot het einde van de transactie.

    Goedkeuren, afwijzen, uitvoeren en ophelderen vergrendelen altijd: twee gelijktijdige aanroepen op hetzelfde
    verzoek lopen dan na elkaar en de tweede ziet de status die de eerste achterliet (V-044). De atomaire
    voorwaardelijke updates in :func:`voer_uit` blijven daarnaast staan."""
    if vergrendel:
        req = db.get(ActionRequest, request_id, with_for_update=True, populate_existing=True)
    else:
        req = db.get(ActionRequest, request_id)
    if req is None:
        raise HubError(404, "not_found", "Dit actieverzoek bestaat niet.")
    return req


# ------------------------------------------------------------------ tijdgebonden overgangen
def veeg(db: Session, now: datetime | None = None) -> None:
    """Verlopen goedkeuringen en verlopen voorstellen bijwerken. De aanroeper commit.

    Alleen verzoeken waarvan deze transactie de rij kan vergrendelen (``FOR UPDATE SKIP LOCKED``; de eigen rij van de
    aanroeper telt mee). Een verzoek dat een andere transactie nu goedkeurt, afwijst, uitvoert of opheldert, slaat de
    veeg over: die houdt de rij vast en ziet zelf wat er verlopen is. Op de vergrendelde rij gelden de voorwaarden
    opnieuw, zodat een gebruikte goedkeuring nooit ook "verlopen" wordt en een verzoek dat al ``bezig`` is nooit
    terug gaat (ADR-0030 besluit 23). De volgorde (eerst het verzoek, dan zijn goedkeuringen) is dezelfde als in
    goedkeuren en uitvoeren."""
    now = now or utcnow()
    db.flush()  # wijzigingen van de aanroeper eerst: de rijen hieronder worden opnieuw gelezen
    open_ap = (Approval.used_at.is_(None), Approval.vervallen_op.is_(None))
    kandidaten = set(db.scalars(select(Approval.request_id).where(*open_ap, Approval.expires_at <= now)))
    kandidaten |= set(
        db.scalars(select(ActionRequest.id).where(ActionRequest.status.in_(OPEN), ActionRequest.geldig_tot <= now))
    )
    if not kandidaten:
        return
    vast = db.scalars(
        select(ActionRequest)
        .where(ActionRequest.id.in_(kandidaten))
        .order_by(ActionRequest.id)
        .with_for_update(skip_locked=True)
        .execution_options(populate_existing=True)
    ).all()
    for req in vast:
        goedkeuringen = db.scalars(
            select(Approval).where(Approval.request_id == req.id, *open_ap).execution_options(populate_existing=True)
        ).all()
        for ap in goedkeuringen:
            if ap.expires_at > now:
                continue
            ap.vervallen_op, ap.vervallen_reden = now, "verlopen"
            if req.status == "goedgekeurd":
                req.status, req.bijgewerkt_op = "wacht_op_goedkeuring", now
                audit.record(
                    db,
                    actor_type="system",
                    actor_id="hub",
                    action="action.approval.expired",
                    target_type="action_request",
                    target_id=str(req.id),
                    details={"approval_id": str(ap.id), "action_id": req.action_id},
                )
        if req.status in OPEN and req.geldig_tot <= now:
            req.status, req.bijgewerkt_op = "verlopen", now
            for ap in goedkeuringen:
                if ap.vervallen_op is None:
                    ap.vervallen_op, ap.vervallen_reden = now, "voorstel_verlopen"
    db.flush()


# ------------------------------------------------------------------ voorstellen
def _fouten_dict(fouten: list[Any]) -> dict[str, Any]:
    return {"fouten": [f.as_dict() for f in fouten[:20]]}


def _weiger(
    db: Session,
    policy: Policy,
    principal: Principal,
    *,
    request_id: uuid.UUID,
    action_id: str,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
    reason: str,
    risk_claim: str | None,
    evidence_ids: list[str],
    cls: Classification,
    status: int,
    code: str,
    message: str,
    trace_id: str,
) -> NoReturn:
    """Leg een geweigerd voorstel vast (zonder parameterwaarden) en geef het foutantwoord."""
    now = utcnow()
    blok = [b.as_dict() for b in cls.blokkades] or [
        {"id": (list(cls.rule_ids) or [code])[0], "code": code, "reden": message}
    ]
    try:
        psha: str | None = execreq.parameters_sha256(parameters)
    except (TypeError, ValueError):
        psha = None
    klein = dict(target) if len(json.dumps(target, default=str)) <= 2048 else {}
    db.add(
        ActionRequest(
            id=request_id,
            aangemaakt_op=now,
            bijgewerkt_op=now,
            geldig_tot=now,
            actor_type="user",
            actor_id=principal.name,
            action_id=action_id[:96],
            target=klein,
            parameters={},
            reden=reason,
            evidence_ids=evidence_ids,
            risk_claim=risk_claim,
            risk_class=cls.risk_class,
            rule_ids=list(cls.rule_ids),
            policy_hash=policy.hash,
            uitvoerder=None,
            preview={"schema": SCHEMA, "geweigerd": True, "parameters_sha256": psha},
            blokkades=blok,
            status="geweigerd",
            resultaat={"code": code, "message": message},
            trace_id=trace_id[:64],
        )
    )
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="action.proposal.refused",
        target_type="action_request",
        target_id=str(request_id),
        details={
            "action_id": action_id[:96],
            "code": code,
            "risk_class": cls.risk_class,
            "rule_ids": list(cls.rule_ids),
            "risk_claim": risk_claim,
            "parameters_sha256": psha,
            "policy_hash": policy.hash,
        },
        trace_id=trace_id,
    )
    raise Bewaard(
        status,
        code,
        message,
        {
            "request_id": str(request_id),
            "risk_class": cls.risk_class,
            "rule_ids": list(cls.rule_ids),
            "blokkades": blok,
        },
    )


def _bestaan(actie: ActieDef, doel: Doel) -> None:
    """Dezelfde bestaanscontroles als de executor; hier al, zodat niemand iets goedkeurt wat niet kan."""
    if actie.doel == "app_nieuw":
        if doel.bestaat:
            raise HubError(409, "doel_bestaat_al", "Er bestaat al een app met deze naam; er is niets voorgesteld.")
        return
    if actie.doel in ("app", "dataset", "snapshot") and not doel.bestaat:
        raise HubError(409, "doel_bestaat_niet", "Het doel van deze actie bestaat niet (meer) op de NAS.")
    if actie.doel in ("dataset", "snapshot") and doel.extra_bestaat:
        raise HubError(409, "doel_bestaat_al", "De snapshot of sandbox-dataset bestaat al; er is niets voorgesteld.")


def _lees(
    db: Session,
    vault: Vault,
    settings: Settings,
    policy: Policy,
    actie: ActieDef,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
) -> Doel:
    try:
        return lees_doel(db, vault, settings, policy, actie, target, parameters)
    except DoelOnbekend as exc:
        raise HubError(
            409,
            "doel_onbekend",
            "De Hub kan het doel nu niet uitlezen op de NAS; onbekend telt nooit als ongewijzigd. Er is niets "
            "voorgesteld, goedgekeurd of uitgevoerd.",
            {"reason_code": exc.reason_code, "detail": exc.detail},
        ) from None


def stel_voor(
    db: Session,
    settings: Settings,
    vault: Vault,
    principal: Principal,
    *,
    request_id: uuid.UUID,
    action_id: str,
    target: dict[str, Any],
    parameters: dict[str, Any],
    reason: str,
    risk_claim: str | None,
    evidence_ids: list[str],
    expected_version: str | None,
    expires_in_seconds: int,
    trace_id: str,
) -> dict[str, Any]:
    policy = get_policy()
    if db.get(ActionRequest, request_id) is not None:
        raise HubError(409, "verzoek_bestaat_al", "Er bestaat al een actieverzoek met deze Idempotency-Key.")
    aid = action_id.strip().lower()
    gemeen: dict[str, Any] = {
        "request_id": request_id,
        "action_id": aid,
        "target": target,
        "parameters": parameters,
        "reason": reason,
        "risk_claim": risk_claim,
        "evidence_ids": evidence_ids,
        "trace_id": trace_id,
    }
    # Stap 1: het beleid zonder kennis van het doel. risk_claim telt nergens mee (EX18).
    cls = classify(policy, action_id=aid, target=target, parameters=parameters, actor_type="user")
    if cls.geweigerd:
        _weiger(
            db,
            policy,
            principal,
            cls=cls,
            status=403,
            code="actie_geweigerd",
            message="Het beleid weigert deze actie; er is niets voorgesteld.",
            **gemeen,
        )
    if cls.gereserveerd is not None:
        _weiger(
            db,
            policy,
            principal,
            cls=cls,
            status=501,
            code="capability_unavailable",
            message=cls.gereserveerd.reden_nl,
            **gemeen,
        )
    actie = policy.actie(aid)
    if actie is None or not cls.known:
        _weiger(
            db,
            policy,
            principal,
            cls=cls,
            status=403,
            code="actie_niet_toegestaan",
            message="Deze actie staat niet op de allowlist; er is niets voorgesteld.",
            **gemeen,
        )
    if actie.eigenaar is not None:
        _weiger(
            db,
            policy,
            principal,
            cls=cls,
            status=501,
            code="capability_unavailable",
            message=f"Deze actie voert {actie.eigenaar} zelf uit; die koppeling bestaat in deze versie nog niet.",
            **gemeen,
        )
    fouten = validate_target(actie, target)
    fouten += [] if fouten else validate_parameters(policy, actie, target, parameters)
    if fouten:
        raise HubError(
            422, "parameters_ongeldig", "Doel of parameters voldoen niet aan het schema.", _fouten_dict(fouten)
        )
    if aid == "app.install" and vault_refs(parameters):
        raise HubError(
            501,
            "capability_unavailable",
            "Geheimen uit de kluis invullen bij een installatie is in deze versie niet beschikbaar; er is niets "
            "voorgesteld.",
            {"reden": "vault_verwijzingen"},
        )
    # Stap 2: het doel zelf uitlezen en opnieuw classificeren met wat er werkelijk staat (kritiek, beschermd).
    doel = _lees(db, vault, settings, policy, actie, target, parameters)
    cls = classify(
        policy, action_id=aid, target=target, parameters=parameters, actor_type="user", herkend_als=doel.herkend_als
    )
    if cls.geweigerd:
        _weiger(
            db,
            policy,
            principal,
            cls=cls,
            status=403,
            code="actie_geweigerd",
            message="Het beleid weigert deze actie voor dit doel; er is niets voorgesteld.",
            **gemeen,
        )
    _bestaan(actie, doel)
    if expected_version is not None and expected_version != doel.etag:
        raise HubError(
            409,
            "doel_gewijzigd",
            "Het doel is anders dan verwacht; er is niets voorgesteld.",
            {"verwacht": expected_version, "gevonden": doel.etag},
        )
    preview, phash = bouw(policy, actie, cls, target, parameters, doel)
    now = utcnow()
    req = ActionRequest(
        id=request_id,
        aangemaakt_op=now,
        bijgewerkt_op=now,
        geldig_tot=now + timedelta(seconds=expires_in_seconds),
        actor_type="user",
        actor_id=principal.name,
        action_id=aid,
        target=target,
        parameters=parameters,
        reden=reason,
        evidence_ids=evidence_ids,
        risk_claim=risk_claim,
        risk_class=cls.risk_class,
        rule_ids=list(cls.rule_ids),
        policy_hash=policy.hash,
        uitvoerder=actie.uitvoerder,
        doel_sleutel=doel.sleutel,
        resource_etag=doel.etag,
        preview=preview,
        preview_hash=phash,
        blokkades=[],
        status="wacht_op_goedkeuring" if cls.requires_approval else "klaar",
        trace_id=trace_id[:64],
    )
    db.add(req)
    db.flush()
    req.blokkades, _ = blok_mod.dynamisch(db, settings, policy, actie, cls, req, now=now)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="action.proposal.created",
        target_type="action_request",
        target_id=str(req.id),
        details={
            "action_id": aid,
            "doel": doel.sleutel,
            "parameters_sha256": preview["parameters_sha256"],
            "risk_class": cls.risk_class,
            "rule_ids": list(cls.rule_ids),
            "risk_claim": risk_claim,
            "policy_hash": policy.hash,
            "preview_hash": phash,
            "resource_etag": doel.etag,
        },
        trace_id=trace_id,
    )
    db.flush()
    return weergave(db, req)


# ------------------------------------------------------------------ herberekenen
def _herbereken(
    db: Session, settings: Settings, vault: Vault, policy: Policy, req: ActionRequest, now: datetime
) -> tuple[ActieDef, Classification, Doel, dict[str, Any], str]:
    """Alles opnieuw, met het beleid en de NAS van nu. Past het voorstel niet meer, dan is het geweigerd."""

    def stop(message: str, cls: Classification | None, details: dict[str, Any]) -> NoReturn:
        req.status, req.bijgewerkt_op = "geweigerd", now
        req.resultaat = {"code": "actie_geweigerd", "message": message}
        if cls is not None:
            req.blokkades = [b.as_dict() for b in cls.blokkades]
        for ap in db.scalars(
            select(Approval).where(
                Approval.request_id == req.id, Approval.used_at.is_(None), Approval.vervallen_op.is_(None)
            )
        ).all():
            ap.vervallen_op, ap.vervallen_reden = now, "geweigerd"
        audit.record(
            db,
            actor_type="system",
            actor_id="hub",
            action="action.proposal.refused",
            target_type="action_request",
            target_id=str(req.id),
            details={"action_id": req.action_id, "code": "actie_geweigerd", "bij": "herberekening"},
        )
        raise Bewaard(403, "actie_geweigerd", message, {"request_id": str(req.id), **details})

    actie = policy.actie(req.action_id)
    kaal = classify(
        policy, action_id=req.action_id, target=req.target, parameters=req.parameters, actor_type=req.actor_type
    )
    if actie is None or not kaal.known or kaal.geweigerd or kaal.gereserveerd is not None or actie.eigenaar is not None:
        stop("Het beleid staat deze actie niet (meer) toe.", kaal, {"rule_ids": list(kaal.rule_ids)})
    fouten = validate_target(actie, req.target)
    fouten += [] if fouten else validate_parameters(policy, actie, req.target, req.parameters)
    if fouten:
        stop("Doel of parameters voldoen niet (meer) aan het schema van het beleid.", None, _fouten_dict(fouten))
    doel = _lees(db, vault, settings, policy, actie, req.target, req.parameters)
    cls = classify(
        policy,
        action_id=req.action_id,
        target=req.target,
        parameters=req.parameters,
        actor_type=req.actor_type,
        herkend_als=doel.herkend_als,
    )
    if cls.geweigerd:
        stop("Het beleid weigert deze actie voor dit doel.", cls, {"blokkades": [b.as_dict() for b in cls.blokkades]})
    _bestaan(actie, doel)
    preview, phash = bouw(policy, actie, cls, req.target, req.parameters, doel)
    return actie, cls, doel, preview, phash


def _neem_over(
    req: ActionRequest,
    policy: Policy,
    cls: Classification,
    doel: Doel,
    preview: dict[str, Any],
    phash: str,
    now: datetime,
) -> list[str]:
    """Zet de herberekende waarden in het voorstel; geeft de gebonden velden die anders waren."""
    anders = [
        veld
        for veld, oud, nieuw in (
            ("policy_hash", req.policy_hash, policy.hash),
            ("resource_etag", req.resource_etag, doel.etag),
            ("risk_class", req.risk_class, cls.risk_class),
            ("preview_hash", req.preview_hash, phash),
        )
        if oud != nieuw
    ]
    if anders:
        req.policy_hash, req.resource_etag, req.risk_class = policy.hash, doel.etag, cls.risk_class
        req.rule_ids, req.preview, req.preview_hash = list(cls.rule_ids), preview, phash
        req.doel_sleutel, req.bijgewerkt_op = doel.sleutel, now
    return anders


def _hashes(req: ActionRequest) -> dict[str, Any]:
    return {
        "request_id": str(req.id),
        "preview_hash": req.preview_hash,
        "resource_etag": req.resource_etag,
        "policy_hash": req.policy_hash,
        "risk_class": req.risk_class,
    }


# ------------------------------------------------------------------ goedkeuren en afwijzen
def keur_goed(
    db: Session,
    settings: Settings,
    vault: Vault,
    principal: Principal,
    req: ActionRequest,
    *,
    preview_hash: str,
    resource_etag: str,
    policy_hash: str,
    trace_id: str,
) -> dict[str, Any]:
    policy = get_policy()
    now = _nu()
    veeg(db, now)
    if req.status == "verlopen":
        raise Bewaard(409, "voorstel_verlopen", "Dit voorstel is verlopen; stel de actie opnieuw voor.", _hashes(req))
    if req.status != "wacht_op_goedkeuring":
        raise HubError(
            409,
            "status_past_niet",
            "Dit voorstel wacht niet op goedkeuring.",
            {"status": req.status, "goedkeuring_nodig": class_at_least(req.risk_class, "R2")},
        )
    actie, cls, _doel, preview, phash = _herbereken(db, settings, vault, policy, req, now)
    anders = _neem_over(req, policy, cls, _doel, preview, phash, now)
    if not cls.requires_approval:
        # Het doel is niet meer kritiek of het beleid is gewijzigd: er valt niets meer goed te keuren.
        req.status, req.bijgewerkt_op = "klaar", now
        raise Bewaard(
            409, "status_past_niet", "Deze actie vraagt geen goedkeuring meer.", {"status": "klaar", **_hashes(req)}
        )
    gezien = {"preview_hash": preview_hash, "resource_etag": resource_etag, "policy_hash": policy_hash}
    anders = sorted(set(anders) | {k for k, v in gezien.items() if v != getattr(req, k)})
    if anders:
        # De beheerder keek naar iets anders dan wat er nu staat: eerst de nieuwe preview bekijken.
        raise Bewaard(
            409,
            "preview_gewijzigd",
            "De preview is veranderd sinds je hem opvroeg; bekijk de nieuwe preview en keur die goed.",
            {"gewijzigd": anders, **_hashes(req)},
        )
    blok, checkpoint = blok_mod.dynamisch(db, settings, policy, actie, cls, req, now=now)
    req.blokkades, req.bijgewerkt_op = blok, now
    if blok:
        raise Bewaard(
            409,
            "actie_geblokkeerd",
            "Deze actie is nu geblokkeerd; een goedkeuring heft een blokkade niet op.",
            {"blokkades": blok, "request_id": str(req.id)},
        )
    for oud in db.scalars(
        select(Approval).where(
            Approval.request_id == req.id, Approval.used_at.is_(None), Approval.vervallen_op.is_(None)
        )
    ).all():
        oud.vervallen_op, oud.vervallen_reden = now, "vervangen"
    ap = Approval(
        id=uuid.uuid4(),
        request_id=req.id,
        preview_hash=req.preview_hash,
        resource_etag=req.resource_etag,
        policy_hash=req.policy_hash,
        risk_class=req.risk_class,
        approved_by=principal.name,
        approved_at=now,
        expires_at=now + timedelta(seconds=execreq.MAX_APPROVAL_SECONDS),
        one_time_nonce=uuid.uuid4(),
        backup_checkpoint_id=checkpoint,
        action_scope=execreq.action_scope(req.action_id, req.target, req.parameters),
    )
    db.add(ap)
    req.status = "goedgekeurd"
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="action.approval.granted",
        target_type="action_request",
        target_id=str(req.id),
        details={
            "approval_id": str(ap.id),
            "action_id": req.action_id,
            "doel": req.doel_sleutel,
            "risk_class": req.risk_class,
            "preview_hash": req.preview_hash,
            "resource_etag": req.resource_etag,
            "policy_hash": req.policy_hash,
            "expires_at": iso(ap.expires_at),
            "backup_checkpoint_id": checkpoint,
        },
        trace_id=trace_id,
    )
    db.flush()
    return weergave(db, req)


def wijs_af(db: Session, principal: Principal, req: ActionRequest, *, reden: str, trace_id: str) -> dict[str, Any]:
    now = _nu()
    veeg(db, now)
    if req.status not in ("wacht_op_goedkeuring", "goedgekeurd", "klaar"):
        raise HubError(409, "status_past_niet", "Dit voorstel kan niet meer worden afgewezen.", {"status": req.status})
    for ap in db.scalars(
        select(Approval).where(
            Approval.request_id == req.id, Approval.used_at.is_(None), Approval.vervallen_op.is_(None)
        )
    ).all():
        ap.vervallen_op, ap.vervallen_reden = now, "afgewezen"
    req.status, req.bijgewerkt_op = "afgewezen", now
    req.resultaat = {"code": "afgewezen", "message": reden, "door": principal.name}
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="action.approval.rejected",
        target_type="action_request",
        target_id=str(req.id),
        details={"action_id": req.action_id, "doel": req.doel_sleutel, "reden": reden},
        trace_id=trace_id,
    )
    db.flush()
    return weergave(db, req)


# ------------------------------------------------------------------ uitvoeren
def _event(db: Session, req: ActionRequest, uitkomst: str, extra: dict[str, Any] | None = None) -> None:
    emit(
        db,
        "action.run.succeeded" if uitkomst == "uitgevoerd" else "action.run.failed",
        "action_target",
        (req.doel_sleutel or req.action_id)[:128],
        {
            "uitkomst": uitkomst,
            "request_id": str(req.id),
            "action_id": req.action_id,
            "doel": req.doel_sleutel,
            "risk_class": req.risk_class,
            **(extra or {}),
        },
    )


def _sluit(
    db: Session,
    req: ActionRequest,
    status: str,
    resultaat: dict[str, Any],
    *,
    actor: str,
    extra: dict[str, Any] | None = None,
) -> None:
    now = utcnow()
    was_onbekend = req.status == "onbekend"
    req.status, req.resultaat, req.bijgewerkt_op = status, resultaat, now
    if status == "uitgevoerd":
        req.uitgevoerd_op = now
    audit.record(
        db,
        actor_type="user" if actor != "hub" else "system",
        actor_id=actor,
        action=f"action.execution.{AUDIT_WOORD.get(status, 'failed')}",
        target_type="action_request",
        target_id=str(req.id),
        details={
            "action_id": req.action_id,
            "doel": req.doel_sleutel,
            "risk_class": req.risk_class,
            "uitkomst": status,
            "code": resultaat.get("code"),
            "reden": resultaat.get("reden"),
            "methode": resultaat.get("methode"),
            "before_hash": resultaat.get("before_hash"),
            "after_hash": resultaat.get("after_hash"),
        },
    )
    _event(db, req, status, extra)
    if was_onbekend and status != "onbekend":
        # De onzekerheid is weg: het incident "uitkomst onbekend" van dit verzoek mag dicht.
        emit(
            db,
            "action.outcome.clarified",
            "action_request",
            str(req.id),
            {"uitkomst": status, "request_id": str(req.id), "action_id": req.action_id, "doel": req.doel_sleutel},
        )
    db.flush()


def _executor(db: Session, settings: Settings) -> tuple[Service, str]:
    svc = db.scalars(select(Service).where(Service.app_id == EXECUTOR_APP_ID, Service.status == "active")).first()
    if svc is None:
        raise HubError(
            409,
            "executor_niet_gekoppeld",
            "De executor is niet gekoppeld; er is niets uitgevoerd. Koppel hem op zijn eigen statuspagina.",
        )
    base, why = service_base_url(db, settings, svc)
    if base is None:
        raise HubError(
            409,
            "executor_adres_onbekend",
            "Het adres van de executor is niet gemeten (NAS-adres D03 + hostpoort uit de inventaris); er is niets "
            "uitgevoerd.",
            {"reason": why},
        )
    return svc, base


def _envelope(
    req: ActionRequest,
    ap: Approval | None,
    cls: Classification,
    policy: Policy,
    doel: Doel,
    nonce: uuid.UUID,
    now: datetime,
) -> dict[str, Any]:
    proposal = {
        "idempotency_key": str(req.id),
        "action_id": req.action_id,
        "target": req.target,
        "parameters": req.parameters,
        "reason": req.reden,
        "actor": {"type": req.actor_type, "id": req.actor_id},
        "expected_version": doel.etag,
        "risk_claim": req.risk_claim,
        "evidence_ids": list(req.evidence_ids),
        "expires_in_seconds": max(1, int((req.geldig_tot - req.aangemaakt_op).total_seconds())),
    }
    approval = None
    if ap is not None:
        approval = {
            "approval_id": str(ap.id),
            "request_id": str(req.id),
            "preview_hash": ap.preview_hash,
            "resource_etag": ap.resource_etag,
            "policy_hash": ap.policy_hash,
            "risk_class": ap.risk_class,
            "approved_by": ap.approved_by,
            "approved_at": execreq.iso(ap.approved_at),
            "expires_at": execreq.iso(ap.expires_at),
            "one_time_nonce": str(ap.one_time_nonce),
            "backup_checkpoint_id": ap.backup_checkpoint_id,
            "action_scope": ap.action_scope,
        }
    return {
        "proposal": proposal,
        "approval": approval,
        "policy_decision": {"risk_class": cls.risk_class, "rule_ids": list(cls.rule_ids), "policy_hash": policy.hash},
        "issued_at": execreq.iso(now),
        "expires_at": execreq.iso(now + timedelta(seconds=REQUEST_TTL)),
        "nonce": str(nonce),
    }


def _journaal(db: Session, settings: Settings, keyring: KeyRing, req: ActionRequest) -> tuple[str, dict[str, Any]]:
    """Vraag het journaal van de executor: ``(uitkomst, gegevens)``.

    Uitkomst: ``uitgevoerd`` | ``mislukt`` | ``afwijking`` | ``geen`` (bereikbaar, maar niets gestart) | ``open``
    (gestart, nog geen einde) | ``onbereikbaar``.
    """
    try:
        svc, base = _executor(db, settings)
        bearer, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
        res = servicecalls.call(
            base,
            "GET",
            f"/api/v1/executions/{req.id}",
            bearer=bearer,
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=settings.service_call_read_timeout,
        )
    except HubError as exc:
        return "onbereikbaar", {"reden": exc.code}
    except servicecalls.ServiceCallError as exc:
        return "onbereikbaar", {"reden": exc.reason}
    rows = res.body.get("uitvoeringen") if res.status == 200 and isinstance(res.body, dict) else None
    if not isinstance(rows, list):
        return "onbereikbaar", {"reden": f"http_{res.status}"}
    if not rows:
        return "geen", {"gestopt": bool((res.body or {}).get("gestopt"))}
    laatste = rows[-1] if isinstance(rows[-1], dict) else {}
    gegevens = {
        "bron": "journaal_executor",
        "methode": laatste.get("methode"),
        "before_hash": laatste.get("before_hash"),
        "after_hash": laatste.get("after_hash"),
        "detail": laatste.get("detail") or None,
        "gestart_op": laatste.get("started_at"),
        "klaar_op": laatste.get("finished_at"),
        "gestopt": bool((res.body or {}).get("gestopt")),
    }
    status = str(laatste.get("status") or "")
    return (status if status in ("uitgevoerd", "mislukt", "afwijking") else "open"), gegevens


def _antwoord(
    db: Session, req: ActionRequest, uitkomst: str, gegevens: dict[str, Any], actor: str
) -> tuple[int, dict[str, Any]]:
    """Leg een uitkomst uit het journaal vast en geef het antwoord (of het foutantwoord)."""
    if uitkomst == "uitgevoerd":
        _sluit(db, req, "uitgevoerd", {"status": "uitgevoerd", **gegevens}, actor=actor)
        return 200, weergave(db, req)
    if uitkomst == "afwijking":
        _sluit(db, req, "afwijking", {"code": "afwijking", "reden": gegevens.get("detail"), **gegevens}, actor=actor)
        raise Bewaard(
            409,
            "afwijking",
            "De toestand na de uitvoering wijkt af van de verwachting of is onbekend. De executor is gestopt; er is "
            "een incident gemaakt en er wordt niets herhaald.",
            {"request_id": str(req.id), "reden": gegevens.get("detail"), "gestopt": gegevens.get("gestopt")},
        )
    _sluit(db, req, "mislukt", {"code": "uitvoering_mislukt", "reden": gegevens.get("detail"), **gegevens}, actor=actor)
    raise Bewaard(
        502,
        "uitvoering_mislukt",
        "TrueNAS heeft de actie niet uitgevoerd; de toestand van het doel is onveranderd.",
        {"request_id": str(req.id), "reden": gegevens.get("detail")},
    )


def _onbekend(db: Session, req: ActionRequest, reden: str, actor: str) -> NoReturn:
    _sluit(db, req, "onbekend", {"code": "uitkomst_onbekend", "reden": reden}, actor=actor, extra={"reden": reden})
    raise Bewaard(
        502,
        "uitkomst_onbekend",
        "De executor gaf geen bruikbaar antwoord; of de actie is uitgevoerd, is onbekend. De Hub herhaalt niets. "
        "Vraag de uitkomst later op via het journaal van de executor.",
        {"request_id": str(req.id), "reden": reden},
    )


def _meld(db: Session, req: ActionRequest, principal: Principal, now: datetime) -> tuple[int, dict[str, Any]]:
    """``notification.send`` (R0): in de meldingenwachtrij; de worker verstuurt (rate-limit en stille uren gelden)."""
    p = req.parameters
    prio = p.get("prioriteit")
    prio = prio if isinstance(prio, int) else 2
    ernst = "kritiek" if prio >= 8 else "waarschuwing" if prio >= 5 else "info"
    kanalen = [
        c
        for c in db.scalars(select(NotificationChannel).where(NotificationChannel.ingeschakeld.is_(True)))
        if ERNST_RANK[ernst] >= ERNST_RANK.get(c.min_ernst, 0)
    ]
    req.gestart_op = now
    if not kanalen:
        req.status, req.bijgewerkt_op = "mislukt", now
        req.resultaat = {"code": "geen_kanaal", "ernst": ernst}
        audit.record(
            db,
            actor_type="user",
            actor_id=principal.name,
            action="action.execution.failed",
            target_type="action_request",
            target_id=str(req.id),
            details={"action_id": req.action_id, "code": "geen_kanaal", "ernst": ernst},
        )
        raise Bewaard(
            409,
            "geen_kanaal",
            "Er is geen ingeschakeld meldingskanaal dat deze ernst ontvangt; er is niets verstuurd.",
            {"request_id": str(req.id), "ernst": ernst},
        )
    ids = []
    for ch in kanalen:
        n = Notification(
            kanaal_id=ch.id,
            dedupe_sleutel=f"actie:{req.id}",
            bron="handmatig",
            soort="bericht",
            ernst=ernst,
            titel=" ".join(str(p.get("titel") or "").split())[:160],
            bericht=str(p.get("tekst") or ""),
            status="wachtrij",
            volgende_poging_op=now,
            aangemaakt_op=now,
            aangemaakt_door=principal.actor[:64],
        )
        db.add(n)
        db.flush()
        ids.append(str(n.id))
    req.status, req.bijgewerkt_op, req.uitgevoerd_op = "uitgevoerd", now, now
    # Eerlijk: "uitgevoerd" betekent hier dat de melding in de wachtrij staat; afleveren doet de worker.
    req.resultaat = {"status": "wachtrij", "meldingen": ids, "ernst": ernst, "kanalen": len(kanalen)}
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="action.execution.succeeded",
        target_type="action_request",
        target_id=str(req.id),
        details={"action_id": req.action_id, "risk_class": req.risk_class, "ernst": ernst, "kanalen": len(kanalen)},
    )
    db.flush()
    return 200, weergave(db, req)


def _vergrendel_doel(db: Session, action_id: str, doel_sleutel: str) -> None:
    """Eén uitvoering tegelijk per (actie, doel), tot het einde van de transactie (``pg_advisory_xact_lock``).

    De afkoeltijd en het maximum per uur tellen gestarte uitvoeringen. Zonder deze vergrendeling zien twee aparte
    voorstellen voor hetzelfde doel elkaars start niet als ze tegelijk worden uitgevoerd, en gaan ze er allebei door
    (ADR-0030 besluit 24: anti-flap geldt voor iedereen). De vergrendeling wordt vrijgegeven bij de commit die het
    voorstel op ``bezig`` zet, of bij een terugdraaiing."""
    digest = hashlib.sha256(f"hub:actie:{action_id}:{doel_sleutel}".encode()).digest()
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": int.from_bytes(digest[:8], "big", signed=True)})


def voer_uit(
    db: Session,
    settings: Settings,
    vault: Vault,
    keyring: KeyRing,
    principal: Principal,
    req: ActionRequest,
    *,
    trace_id: str,
) -> tuple[int, dict[str, Any]]:
    policy = get_policy()
    now = _nu()
    veeg(db, now)
    if req.status == "verlopen":
        raise Bewaard(409, "voorstel_verlopen", "Dit voorstel is verlopen; stel de actie opnieuw voor.", _hashes(req))
    if req.status == "wacht_op_goedkeuring":
        raise Bewaard(
            409,
            "goedkeuring_nodig",
            "Deze actie vraagt een geldige goedkeuring van een beheerder (hooguit 15 minuten oud).",
            {"status": req.status, **_hashes(req)},
        )
    if req.status not in ("klaar", "goedgekeurd"):
        raise HubError(
            409, "status_past_niet", "Dit voorstel kan niet (meer) worden uitgevoerd.", {"status": req.status}
        )
    if class_at_least(req.risk_class, "R2") and principal.role != Role.admin:
        raise HubError(403, "forbidden", "Alleen een beheerder voert een R2- of R3-actie uit.")
    ap = huidige_goedkeuring(db, req) if req.status == "goedgekeurd" else None
    actie, cls, doel, preview, phash = _herbereken(db, settings, vault, policy, req, now)
    if cls.requires_approval and principal.role != Role.admin:
        raise HubError(403, "forbidden", "Alleen een beheerder voert een R2- of R3-actie uit.")
    if ap is not None:
        gebonden = {
            "policy_hash": ap.policy_hash == policy.hash,
            "resource_etag": ap.resource_etag == doel.etag,
            "preview_hash": ap.preview_hash == phash,
            "risk_class": class_at_least(ap.risk_class, cls.risk_class),
            "action_scope": ap.action_scope == execreq.action_scope(req.action_id, req.target, req.parameters),
        }
        anders = sorted(k for k, ok in gebonden.items() if not ok)
        if anders or ap.used_at is not None or ap.vervallen_op is not None:
            if ap.used_at is not None:
                raise HubError(
                    409, "goedkeuring_al_gebruikt", "Deze goedkeuring is al eens gebruikt; keur opnieuw goed."
                )
            # EX19: er is iets veranderd sinds de goedkeuring → de goedkeuring vervalt, de nieuwe preview staat klaar.
            ap.vervallen_op, ap.vervallen_reden = now, ("gewijzigd:" + ",".join(anders))[:64]
            _neem_over(req, policy, cls, doel, preview, phash, now)
            req.status, req.bijgewerkt_op = ("wacht_op_goedkeuring" if cls.requires_approval else "klaar"), now
            audit.record(
                db,
                actor_type="system",
                actor_id="hub",
                action="action.approval.lapsed",
                target_type="action_request",
                target_id=str(req.id),
                details={"approval_id": str(ap.id), "action_id": req.action_id, "gewijzigd": anders},
                trace_id=trace_id,
            )
            raise Bewaard(
                409,
                "goedkeuring_vervallen",
                "Er is iets veranderd sinds de goedkeuring; de goedkeuring is vervallen en er is niets uitgevoerd. "
                "Bekijk de nieuwe preview en keur opnieuw goed.",
                {"gewijzigd": anders, **_hashes(req)},
            )
    else:
        oude_etag = req.resource_etag
        anders = _neem_over(req, policy, cls, doel, preview, phash, now)
        if cls.requires_approval:
            # Het doel is nu kritiek of het beleid is strenger: zonder goedkeuring gebeurt er niets.
            req.status, req.bijgewerkt_op = "wacht_op_goedkeuring", now
            raise Bewaard(
                409,
                "goedkeuring_nodig",
                "Deze actie vraagt nu een goedkeuring van een beheerder; er is niets uitgevoerd.",
                {"gewijzigd": anders, **_hashes(req)},
            )
        if "resource_etag" in anders:
            raise Bewaard(
                409,
                "doel_gewijzigd",
                "Het doel is veranderd sinds het voorstel; er is niets uitgevoerd. Bekijk de nieuwe preview en voer "
                "daarna opnieuw uit.",
                {"verwacht": oude_etag, "gevonden": doel.etag, **_hashes(req)},
            )
    _vergrendel_doel(db, req.action_id, req.doel_sleutel)
    blok, checkpoint = blok_mod.dynamisch(db, settings, policy, actie, cls, req, now=now)
    req.blokkades, req.bijgewerkt_op = blok, now
    if blok:
        # EX11/EX12: een blokkade geldt ook mét goedkeuring. De goedkeuring blijft tot zijn vervaltijd bruikbaar.
        raise Bewaard(
            409,
            "actie_geblokkeerd",
            "Deze actie is nu geblokkeerd; er is niets uitgevoerd.",
            {"blokkades": blok, "request_id": str(req.id)},
        )
    if ap is not None and cls.requires_backup and ap.backup_checkpoint_id != checkpoint:
        ap.vervallen_op, ap.vervallen_reden = now, "gewijzigd:backup_checkpoint_id"
        req.status = "wacht_op_goedkeuring"
        raise Bewaard(
            409,
            "goedkeuring_vervallen",
            "Het herstelpunt is veranderd sinds de goedkeuring; keur opnieuw goed.",
            {"gewijzigd": ["backup_checkpoint_id"], **_hashes(req)},
        )
    if actie.uitvoerder == "hub:gotify":
        return _meld(db, req, principal, now)
    if not actie.via_executor:
        raise HubError(501, "capability_unavailable", "Voor deze actie bestaat in deze versie nog geen uitvoerder.")
    svc, base = _executor(db, settings)

    # Atomair: eerst de eenmalige nonce van de goedkeuring verbruiken (EX20), dan het voorstel op 'bezig'. Wie tweede
    # komt, wijzigt nul rijen en krijgt 409; er gaat dan niets naar de executor.
    db.flush()
    nonce = uuid.uuid4()
    if ap is not None:
        gebruikt = db.execute(
            update(Approval)
            .where(Approval.id == ap.id, Approval.used_at.is_(None), Approval.vervallen_op.is_(None))
            .values(used_at=now)
        )
        if gebruikt.rowcount != 1:  # type: ignore[attr-defined]
            db.rollback()
            raise HubError(409, "goedkeuring_al_gebruikt", "Deze goedkeuring is al eens gebruikt; keur opnieuw goed.")
    gestart = db.execute(
        update(ActionRequest)
        .where(ActionRequest.id == req.id, ActionRequest.status.in_(("klaar", "goedgekeurd")))
        .values(status="bezig", gestart_op=now, bijgewerkt_op=now, execution_nonce=nonce)
    )
    if gestart.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise HubError(409, "status_past_niet", "Dit voorstel wordt al uitgevoerd of is al afgehandeld.")
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="action.execution.started",
        target_type="action_request",
        target_id=str(req.id),
        details={
            "action_id": req.action_id,
            "doel": req.doel_sleutel,
            "risk_class": cls.risk_class,
            "approval_id": str(ap.id) if ap is not None else None,
            "nonce": str(nonce),
            "policy_hash": policy.hash,
            "resource_etag": doel.etag,
        },
        trace_id=trace_id,
    )
    db.commit()
    db.refresh(req)
    if ap is not None:
        db.refresh(ap)

    verzoek = execreq.sign(_envelope(req, ap, cls, policy, doel, nonce, now), keyring.policy_signing)
    # Eigen controle vóór verzending: wat de executor gaat weigeren, sturen we niet eens op.
    nu = utcnow()
    eigen = check_envelope(policy, verzoek, [keyring.policy_signing.public_key()], now=nu)
    if eigen is None:
        _a, _c, eigen = check_decision(policy, verzoek, now=nu, herkend_als=doel.herkend_als, uitvoerder="executor")
    if eigen is not None:
        _sluit(db, req, "mislukt", {"code": eigen.code, "message": eigen.melding, "bij": "hub"}, actor=principal.name)
        raise Bewaard(
            409,
            "uitvoering_geweigerd",
            "De eigen controle van de Hub wees het uitvoeringsverzoek af; er is niets naar de executor gestuurd.",
            {"request_id": str(req.id), "code": eigen.code, "details": eigen.details},
        )
    bearer, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    try:
        res = servicecalls.call(
            base,
            "POST",
            "/api/v1/execute",
            bearer=bearer,
            idempotency_key=str(nonce),
            body=verzoek,
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=float(actie.timeout_seconden + ANTWOORD_MARGE),
        )
    except servicecalls.ServiceCallError as exc:
        uitkomst, gegevens = _journaal(db, settings, keyring, req)
        if uitkomst in ("uitgevoerd", "mislukt", "afwijking"):
            return _antwoord(db, req, uitkomst, gegevens, principal.name)
        _onbekend(db, req, f"executor_{exc.reason}", principal.name)
    return _verwerk(db, req, res, principal.name)


def _verwerk(db: Session, req: ActionRequest, res: servicecalls.CallResult, actor: str) -> tuple[int, dict[str, Any]]:
    body = res.body if isinstance(res.body, dict) else {}
    code = str(body.get("code") or "")
    ruw = body.get("details")
    details: dict[str, Any] = ruw if isinstance(ruw, dict) else {}
    if res.status == 200 and body.get("status") == "uitgevoerd":
        velden = (
            "methode",
            "before_hash",
            "after_hash",
            "resource_etag",
            "readback",
            "waarschuwingen",
            "policy_hash",
            "uitgevoerd_op",
        )
        _sluit(db, req, "uitgevoerd", {"status": "uitgevoerd", **{k: body.get(k) for k in velden}}, actor=actor)
        return 200, weergave(db, req)
    if res.status == 409 and code == "afwijking":
        resultaat = {"code": "afwijking", "message": body.get("message"), **details}
        _sluit(db, req, "afwijking", resultaat, actor=actor, extra={"reden": details.get("reden")})
        raise Bewaard(
            409,
            "afwijking",
            "De toestand na de uitvoering wijkt af van de verwachting of is onbekend. De executor is gestopt; er is "
            "een incident gemaakt en er wordt niets herhaald.",
            {"request_id": str(req.id), **details},
        )
    if res.status == 502 and code == "uitvoering_mislukt":
        _sluit(db, req, "mislukt", {"code": code, "message": body.get("message"), **details}, actor=actor)
        raise Bewaard(
            502,
            "uitvoering_mislukt",
            "TrueNAS heeft de actie niet uitgevoerd; de toestand van het doel is onveranderd.",
            {"request_id": str(req.id), **details},
        )
    if code and res.status != 500:
        # Een gestructureerde weigering van de executor: hij heeft niets uitgevoerd.
        _sluit(
            db,
            req,
            "mislukt",
            {"code": code, "message": body.get("message"), "details": details, "http_status": res.status},
            actor=actor,
        )
        raise Bewaard(
            501 if res.status == 501 else 409,
            "capability_unavailable" if res.status == 501 else "uitvoering_geweigerd",
            str(body.get("message"))
            if res.status == 501
            else "De executor heeft de actie geweigerd; er is niets uitgevoerd.",
            {"request_id": str(req.id), "executor": {"code": code, "message": body.get("message"), "details": details}},
        )
    _onbekend(db, req, f"executor_http_{res.status}", actor)


def haal_uitkomst_op(
    db: Session, settings: Settings, keyring: KeyRing, principal: Principal, req: ActionRequest
) -> tuple[int, dict[str, Any]]:
    """Een ``onbekend`` of blijven hangen ``bezig`` ophelderen met het journaal van de executor (alleen lezen)."""
    now = utcnow()
    policy = get_policy()
    actie = policy.actie(req.action_id)
    limiet = (actie.timeout_seconden if actie is not None else 1800) + ANTWOORD_MARGE + 60
    start = req.gestart_op or req.bijgewerkt_op
    if req.status == "bezig" and start + timedelta(seconds=limiet) > now:
        raise HubError(409, "nog_bezig", "Deze actie loopt nog; wacht op het antwoord van de executor.")
    if req.status not in ("onbekend", "bezig"):
        raise HubError(409, "status_past_niet", "De uitkomst van dit verzoek is al bekend.", {"status": req.status})
    uitkomst, gegevens = _journaal(db, settings, keyring, req)
    if uitkomst in ("uitgevoerd", "mislukt", "afwijking"):
        return _antwoord(db, req, uitkomst, gegevens, principal.name)
    if uitkomst == "geen" and start + timedelta(seconds=REQUEST_TTL + execreq.CLOCK_SKEW + 30) <= now:
        # Niets in het journaal en het ondertekende verzoek is verlopen: de executor kan het niet meer uitvoeren.
        _sluit(
            db,
            req,
            "mislukt",
            {"code": "niet_uitgevoerd", "reden": "geen_journaalregel", **gegevens},
            actor=principal.name,
        )
        return 200, weergave(db, req)
    raise HubError(
        409,
        "uitkomst_onbekend",
        "De uitkomst is nog niet vast te stellen; de Hub herhaalt niets.",
        {"request_id": str(req.id), "journaal": uitkomst, **gegevens},
    )
