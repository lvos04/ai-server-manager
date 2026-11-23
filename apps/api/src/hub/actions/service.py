"""Acties voorstellen, goedkeuren en uitvoeren (contract 1.3 §8, B01-007, B01-003; ADR-0030).

Stroom: voorstel → deterministische classificatie (``risk_claim`` wordt genegeerd) → eigen readback van het doel →
preview met ``preview_hash`` → bij R2/R3 een goedkeuring die vastzit aan preview, ETag en beleid → vlak vóór verzending
alles opnieuw → ondertekend ``ExecutionRequest`` naar de executor → uitkomst eerlijk vastleggen. Een actie van een
eigenaar-connector (§8, tweede tabel) loopt net zo, met het voorstel van de eigenaar (``/connector/v1/propose``) als
doel en ``/connector/v1/apply`` van de eigenaar als uitvoerder.

Vaste regels in dit bestand:

- De Hub voert zelf niets uit op de NAS; hij leest alleen (alleen-lezen-sleutel) en stuurt een ondertekend verzoek.
- Verandert een gebonden veld tussen goedkeuring en uitvoering, dan vervalt de goedkeuring (EX19).
- De eenmalige nonce van een goedkeuring wordt atomair verbruikt vóór verzending (EX20); er is geen tweede poging.
- Een storing of onduidelijk antwoord is nooit een succes: de status wordt ``onbekend`` tot het journaal van de
  executor uitsluitsel geeft. De Hub herhaalt een uitvoering nooit vanzelf. "Uitgevoerd" telt alleen met volledig
  bewijs in de juiste vorm (:func:`_bewijs_uitgevoerd`; S-P2-040, R-VEILIG-2).
- Van een antwoord of journaalregel van de executor neemt de Hub alleen velden uit een vaste lijst over, elk met een
  vaste vorm en lengte; zijn eigen velden zet hij zelf (:func:`_van_executor`; S-P2-040, R-VEILIG-3).
- Parameterwaarden komen niet in de audit, de events of de API-antwoorden (alleen hun SHA-256 en de preview). Na
  afloop van een voorstel wist de Hub ook de waarden van omgevingsvariabelen uit zijn eigen database
  (:func:`_wis_waarden`).
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import math
import re
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, NoReturn

from asm_policy import Policy, execreq
from asm_policy.canonical import CanonicalError, canonical_json
from asm_policy.engine import Classification, class_at_least, classify
from asm_policy.loader import ActieDef
from asm_policy.params import HOST_IDS, validate_parameters, validate_target, vault_refs
from asm_policy.verify import check_decision, check_envelope
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from hub import audit, servicecalls
from hub.actions import blokkades as blok_mod
from hub.actions.beleid import get_policy
from hub.actions.doel import Doel, DoelOnbekend, lees_doel
from hub.actions.preview import SCHEMA, bouw, eigen_opdracht, toon_bewaarde_preview
from hub.catalog import kluis
from hub.config import Settings
from hub.deps import Principal
from hub.errors import HubError
from hub.events.envelope import emit
from hub.keys import KeyRing
from hub.models import ActionRequest, Approval, Notification, NotificationChannel, Service
from hub.monitoring.alerts import ERNST_RANK
from hub.redact import redact, redact_log_text, redact_text
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


#: velden die een doel kan hebben (``asm_policy.params.validate_target``); waarden alleen met vaste vorm
DOEL_VELDEN = ("host_id", "app_id", "dataset", "snapshot", "resource")
_DOEL_WAARDE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@/:-]{0,199}$")


def veilig_doel(target: Any) -> dict[str, Any]:
    """Positieve witte lijst voor het doel van een geweigerd voorstel (R-VEILIG-1): dat doel is nooit door het schema
    gegaan, dus alleen bekende velden met een eenvoudige vaste vorm; de rest verdwijnt."""
    if not isinstance(target, Mapping):
        return {}
    return {k: v for k, v in target.items() if k in DOEL_VELDEN and isinstance(v, str) and _DOEL_WAARDE_RE.fullmatch(v)}


def weergave(db: Session, req: ActionRequest) -> dict[str, Any]:
    ap = huidige_goedkeuring(db, req)
    return {
        "request_id": str(req.id),
        "status": req.status,
        "action_id": req.action_id,
        # Ook bij het lezen van bestaande voorstellen (R-VEILIG-1): geweigerd = alleen veilige doelvelden.
        "target": veilig_doel(req.target) if req.status == "geweigerd" else req.target,
        "parameters_sha256": (req.preview or {}).get("parameters_sha256"),
        "reason": redact_text(req.reden or ""),
        "actor": {"type": req.actor_type, "id": req.actor_id},
        "evidence_ids": redact(req.evidence_ids),
        "risk_class": req.risk_class,
        "risk_claim": req.risk_claim,
        "risk_claim_genegeerd": req.risk_claim is not None,
        "rule_ids": req.rule_ids,
        "goedkeuring_nodig": class_at_least(req.risk_class, "R2"),
        "policy_hash": req.policy_hash,
        "uitvoerder": req.uitvoerder,
        "resource_etag": req.resource_etag or None,
        "preview_hash": req.preview_hash or None,
        "preview": toon_bewaarde_preview(req.preview) if req.preview_hash else None,
        "blokkades": req.blokkades,
        "goedkeuring": _goedkeuring_dict(ap) if ap is not None else None,
        "resultaat": redact(req.resultaat),  # ook een resultaat van vóór R-VEILIG-3
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


# Vrije tekst in de waarden van de standaard Custom App (``IX_VALUES_KEYS``) waarin een gebruiker een geheim kan zetten,
# bijvoorbeeld een wachtwoord als argument (S-P2-010, bouwpunt 6e).
VRIJE_TEKST_VELDEN = ("command", "entrypoint", "labels", "notes")


def _wis_waarden(req: ActionRequest) -> None:
    """Na afloop van een voorstel heeft de Hub de waarden van omgevingsvariabelen en de vrije tekst in ``command``,
    ``entrypoint``, ``labels`` en ``notes`` niet meer nodig: hij voert nooit iets opnieuw uit. Ze verdwijnen dan uit
    ``parameters``, zodat de database van de Hub (en zijn back-up) ze niet voor altijd in klare tekst bewaart; de namen
    van de variabelen blijven en ``vrije_tekst_gewist`` noemt de gewiste velden. ``parameters_sha256`` in de preview en
    de audit blijft gelijk (ADR-0030 besluit 28). Sinds S-P2-040 (R-VEILIG-1) toont de preview ``labels`` en ``notes``
    mét waarde; na afloop verdwijnt die waarde ook uit de bewaarde preview (``{"waarde_gewist": true}``). De
    ``preview_hash`` blijft de hash van de preview die is voorgesteld en goedgekeurd (ADR-0030 besluit 32)."""
    if isinstance(req.preview, dict):
        gemaskeerd = toon_bewaarde_preview(req.preview)
        if gemaskeerd != req.preview:
            req.preview = gemaskeerd
    params = req.parameters if isinstance(req.parameters, dict) else {}
    ac = params.get("app_create")
    values = ac.get("values") if isinstance(ac, dict) else None
    if not isinstance(values, dict):
        return
    envs = values.get("envs")
    env_waarden = isinstance(envs, list) and any(isinstance(e, dict) and "value" in e for e in envs)
    vrij = [k for k in VRIJE_TEKST_VELDEN if k in values]
    if not env_waarden and not vrij:
        return
    nieuw = copy.deepcopy(params)
    nv = nieuw["app_create"]["values"]
    for e in nv.get("envs") if env_waarden else []:
        if isinstance(e, dict) and "value" in e:
            del e["value"]
            e["waarde_gewist"] = True
    for k in vrij:
        del nv[k]
    if vrij:
        nv["vrije_tekst_gewist"] = sorted(set(vrij) | set(nv.get("vrije_tekst_gewist") or []))
    req.parameters = nieuw
    getoond = (req.preview or {}).get("wijziging") if isinstance(req.preview, dict) else None
    waarden = getoond.get("waarden") if isinstance(getoond, dict) else None
    if isinstance(waarden, dict) and any(k in waarden for k in vrij):
        preview = copy.deepcopy(req.preview)
        for k in vrij:
            if k in preview["wijziging"]["waarden"]:
                preview["wijziging"]["waarden"][k] = {"waarde_gewist": True}
        req.preview = preview


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
            _wis_waarden(req)
            for ap in goedkeuringen:
                if ap.vervallen_op is None:
                    ap.vervallen_op, ap.vervallen_reden = now, "voorstel_verlopen"
    db.flush()


# ------------------------------------------------------------------ voorstellen
EIGEN_OPDRACHT_NL = (
    "Een eigen opdracht (command of entrypoint) bij een installatie kan de Hub nog niet veilig tonen; er is niets "
    "voorgesteld of goedgekeurd. Dat kan pas met het installatiescherm (ADR-0030 besluit 32)."
)


def _fouten_dict(fouten: list[Any]) -> dict[str, Any]:
    return {"fouten": [f.as_dict() for f in fouten[:20]]}


def _weiger(
    db: Session,
    policy: Policy,
    actor: tuple[str, str],
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
    klein = veilig_doel(target)
    db.add(
        ActionRequest(
            id=request_id,
            aangemaakt_op=now,
            bijgewerkt_op=now,
            geldig_tot=now,
            actor_type=actor[0],
            actor_id=actor[1],
            action_id=action_id[:96],
            target=klein,
            parameters={},
            reden=redact_text(reason),
            evidence_ids=redact(evidence_ids),
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
        actor_type=actor[0],
        actor_id=actor[1],
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
    *,
    keyring: KeyRing | None = None,
    reden: str = "",
) -> Doel:
    if actie.eigenaar is not None:
        return _eigenaar_voorstel(db, settings, keyring, actie, target, parameters, reden)
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


def controleer_kloonrol(action_id: str, principal: Principal | None) -> None:
    if action_id.strip().lower() == "zfs.snapshot.clone_to_sandbox" and (
        principal is None or principal.kind != "user" or principal.role != Role.admin
    ):
        raise HubError(403, "forbidden", "Alleen een beheerder mag een zandbakkloon voorstellen of uitvoeren.")


def voorcontrole(
    db: Session,
    action_id: str,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
    principal: Principal | None = None,
) -> None:
    """Controles vóór elk voorstel van buiten de Hub (gebruiker of flow); een eigen plan van de Hub slaat ze over."""
    controleer_kloonrol(action_id, principal)
    if "catalog_binding" in parameters:
        # Een catalogusbinding komt alleen uit een eigen plan van de Hub (§8.2), nooit van de aanvrager.
        raise HubError(
            422,
            "catalog_binding_alleen_via_plan",
            "Een catalogusinstallatie loopt via /api/v1/catalog/plans; een eigen catalog_binding wordt geweigerd.",
        )
    doelnaam = target.get("app_id")
    if (
        (action_id == "app.update" and "image" in parameters)
        or (action_id == "app.rollback" and "herstel_van" in parameters)
    ) and kluis.gemarkeerd(db, str(doelnaam)):
        # §8.3: zonder recept met alleen verwijzingen zou app.config de ingevulde geheimen in het journaal brengen.
        raise HubError(
            409,
            "kluisplekken_recept_ontbreekt",
            "Deze app kreeg bij de installatie geheimen uit de kluis. Bijwerken of terugzetten via de waarden kan pas "
            "met het recept met alleen verwijzingen; er is niets voorgesteld.",
        )


def stel_voor(
    db: Session,
    settings: Settings,
    vault: Vault,
    principal: Principal | None,
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
    keyring: KeyRing | None = None,
    actor: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """Zonder ``actor`` is de aangemelde gebruiker de actor; een flow (B01-008) geeft ``("flow", <id>)`` en krijgt
    precies dezelfde classificatie, gates en goedkeuring, met de regels voor een niet-menselijke actor."""
    if actor is None:
        if principal is None:
            raise ValueError("stel_voor zonder gebruiker vraagt een actor")
        actor = ("user", principal.name)
    actor_type = actor[0]
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
    cls = classify(policy, action_id=aid, target=target, parameters=parameters, actor_type=actor_type)
    if cls.geweigerd:
        _weiger(
            db,
            policy,
            actor,
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
            actor,
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
            actor,
            cls=cls,
            status=403,
            code="actie_niet_toegestaan",
            message="Deze actie staat niet op de allowlist; er is niets voorgesteld.",
            **gemeen,
        )
    fouten = validate_target(actie, target)
    fouten += [] if fouten else validate_parameters(policy, actie, target, parameters)
    if fouten:
        raise HubError(
            422, "parameters_ongeldig", "Doel of parameters voldoen niet aan het schema.", _fouten_dict(fouten)
        )
    if aid == "app.install" and vault_refs(parameters) and "catalog_binding" not in parameters:
        # Met een catalogusbinding heeft validate_parameters de plekken al tegen de eigen regel getoetst (§8.3).
        raise HubError(
            501,
            "capability_unavailable",
            "Geheimen uit de kluis invullen bij een installatie is in deze versie niet beschikbaar; er is niets "
            "voorgesteld.",
            {"reden": "vault_verwijzingen"},
        )
    opdracht = eigen_opdracht(aid, parameters)
    if opdracht:
        raise HubError(
            501, "capability_unavailable", EIGEN_OPDRACHT_NL, {"reden": "eigen_opdracht", "velden": opdracht}
        )
    # Stap 2: het doel zelf uitlezen en opnieuw classificeren met wat er werkelijk staat (kritiek, beschermd).
    doel = _lees(db, vault, settings, policy, actie, target, parameters, keyring=keyring, reden=reason)
    cls = _met_eigenaar(
        classify(
            policy,
            action_id=aid,
            target=target,
            parameters=parameters,
            actor_type=actor_type,
            herkend_als=doel.herkend_als,
        ),
        doel,
    )
    if cls.geweigerd:
        _weiger(
            db,
            policy,
            actor,
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
        actor_type=actor_type,
        actor_id=actor[1],
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
        actor_type=actor_type,
        actor_id=actor[1],
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
    db: Session,
    settings: Settings,
    vault: Vault,
    policy: Policy,
    req: ActionRequest,
    now: datetime,
    keyring: KeyRing | None = None,
) -> tuple[ActieDef, Classification, Doel, dict[str, Any], str]:
    """Alles opnieuw, met het beleid en de NAS van nu. Past het voorstel niet meer, dan is het geweigerd."""

    def stop(
        message: str,
        cls: Classification | None,
        details: dict[str, Any],
        *,
        status: int = 403,
        code: str = "actie_geweigerd",
    ) -> NoReturn:
        req.status, req.bijgewerkt_op = "geweigerd", now
        req.resultaat = {"code": code, "message": message}
        _wis_waarden(req)
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
            details={"action_id": req.action_id, "code": code, "bij": "herberekening"},
        )
        raise Bewaard(status, code, message, {"request_id": str(req.id), **details})

    actie = policy.actie(req.action_id)
    kaal = classify(
        policy, action_id=req.action_id, target=req.target, parameters=req.parameters, actor_type=req.actor_type
    )
    if actie is None or not kaal.known or kaal.geweigerd or kaal.gereserveerd is not None:
        stop("Het beleid staat deze actie niet (meer) toe.", kaal, {"rule_ids": list(kaal.rule_ids)})
    fouten = validate_target(actie, req.target)
    fouten += [] if fouten else validate_parameters(policy, actie, req.target, req.parameters)
    if fouten:
        stop("Doel of parameters voldoen niet (meer) aan het schema van het beleid.", None, _fouten_dict(fouten))
    opdracht = eigen_opdracht(req.action_id, req.parameters)
    if opdracht:
        # Een open voorstel van vóór S-P2-040: de preview toonde die opdracht niet (R-VEILIG-1, optie C).
        details = {"reden": "eigen_opdracht", "velden": opdracht}
        stop(EIGEN_OPDRACHT_NL, None, details, status=501, code="capability_unavailable")
    doel = _lees(db, vault, settings, policy, actie, req.target, req.parameters, keyring=keyring, reden=req.reden)
    cls = _met_eigenaar(
        classify(
            policy,
            action_id=req.action_id,
            target=req.target,
            parameters=req.parameters,
            actor_type=req.actor_type,
            herkend_als=doel.herkend_als,
        ),
        doel,
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
    keyring: KeyRing | None = None,
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
    actie, cls, _doel, preview, phash = _herbereken(db, settings, vault, policy, req, now, keyring)
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
    _wis_waarden(req)
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
            **(extra or {}),
            # De eigen velden van de Hub komen na ``extra``: niets uit een executorantwoord overschrijft ze.
            "uitkomst": uitkomst,
            "request_id": str(req.id),
            "action_id": req.action_id,
            "doel": req.doel_sleutel,
            "risk_class": req.risk_class,
        },
    )


# ------------------------------------------------------------------ wat de Hub van de executor overneemt
# Een antwoord of journaalregel van de executor komt over gewoon HTTP (HTTPS volgt met B10/B13) en is dus invoer van
# buiten. De Hub neemt alleen velden uit een vaste lijst over, elk met een vaste vorm en lengte; zijn eigen velden
# (code, request_id, doel, uitkomst, action_id, risk_class) zet hij zelf (S-P2-040, R-VEILIG-3; ADR-0030 besluit 32).
# Een reden is altijd een code met een vast tekenpatroon, zoals de executor ze geeft (``staat_verschilt``,
# ``job_mislukt [FAILED]``, ``OperationalError``), anders ``onbekende_reden``: zo komen vrije tekst, stuurtekens en een
# NUL-teken nergens in resultaat, audit, event of foutantwoord.
REDEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}(?: \[[A-Z][A-Z0-9_]{0,39}\])?")
ONBEKENDE_REDEN = "onbekende_reden"
CODE_RE = re.compile(r"[a-z][a-z0-9_]{0,63}")
METHODE_RE = re.compile(r"[a-z][a-z0-9_]{0,31}(?:\.[a-z][a-z0-9_]{0,31}){1,3}")
HASH_RE = re.compile(r"sha256:[0-9a-f]{64}")
ETAG_RE = re.compile(r"sha256:[0-9a-f]{64}|(?:dataset|snapshot):[A-Za-z0-9_.:/@-]{1,280}")
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
KLASSE_RE = re.compile(r"R[0-3]")
STUURTEKEN_RE = re.compile(r"[\x00-\x1f\x7f]")
MAX_STRUCTUUR = 8 * 1024  # tekens JSON voor readback, afwijkingen, fouten en blokkades
MAX_DIEPTE = 8
MAX_LIJST = 20
MAX_MELDING = 500
BEWIJS_ONVOLLEDIG = "executor_bewijs_onvolledig"


def _reden(waarde: Any) -> str | None:
    if waarde is None or waarde == "":
        return None
    return waarde if isinstance(waarde, str) and REDEN_RE.fullmatch(waarde) else ONBEKENDE_REDEN


def _vorm(waarde: Any, patroon: re.Pattern[str]) -> str | None:
    return waarde if isinstance(waarde, str) and patroon.fullmatch(waarde) else None


def _reeks(waarde: Any, patroon: re.Pattern[str]) -> list[str] | None:
    if not isinstance(waarde, list) or len(waarde) > MAX_LIJST:
        return None
    return waarde if all(isinstance(w, str) and patroon.fullmatch(w) for w in waarde) else None


def _tijd(waarde: Any) -> str | None:
    return waarde if isinstance(waarde, str) and execreq.parse_ts(waarde) is not None else None


def _tijdstip(waarde: Any) -> int | None:
    """Een tijdstip uit het journaal (seconden sinds 1970)."""
    return waarde if isinstance(waarde, int) and not isinstance(waarde, bool) and waarde >= 0 else None


def _schoon(waarde: Any, diepte: int = 0) -> bool:
    if diepte > MAX_DIEPTE:
        return False
    if isinstance(waarde, str):
        return not STUURTEKEN_RE.search(waarde)
    if waarde is None or isinstance(waarde, bool | int):
        return True
    if isinstance(waarde, float):
        return math.isfinite(waarde)
    if isinstance(waarde, list):
        return all(_schoon(w, diepte + 1) for w in waarde)
    if isinstance(waarde, dict):
        return all(isinstance(k, str) and _schoon(k) and _schoon(w, diepte + 1) for k, w in waarde.items())
    return False


def _structuur(waarde: Any, soort: type) -> Any:
    """Een object of lijst (readback, afwijkingen, fouten, blokkades): alleen JSON-typen, geen stuurtekens, niet te diep
    en hooguit :data:`MAX_STRUCTUUR` tekens; anders ``None``."""
    if not isinstance(waarde, soort) or not _schoon(waarde):
        return None
    # Geneste geheime waarden (client_secret, token, …) worden *** vóór opslag (R-VEILIG-3).
    return redact(waarde) if len(json.dumps(waarde, ensure_ascii=False)) <= MAX_STRUCTUUR else None


def _melding(waarde: Any) -> str | None:
    """De Nederlandse melding van de executor: hooguit :data:`MAX_MELDING` tekens, zonder stuurtekens en streng
    geschoond (``redact_log_text``); anders ``None``."""
    if not isinstance(waarde, str) or not waarde or len(waarde) > MAX_MELDING or STUURTEKEN_RE.search(waarde):
        return None
    return redact_log_text(waarde, max_len=MAX_MELDING)


# Per veld de vorm die de Hub overneemt; een veld dat niet in deze tabel staat, neemt hij nooit over.
EXECUTOR_VELDEN: dict[str, Any] = {
    "reden": _reden,
    "afwijkingen": lambda w: _structuur(w, list),
    "fouten": lambda w: _structuur(w, list),
    "blokkades": lambda w: _structuur(w, list),
    "methode": lambda w: _vorm(w, METHODE_RE),
    "methoden": lambda w: _reeks(w, METHODE_RE),
    "before_hash": lambda w: _vorm(w, HASH_RE),
    "after_hash": lambda w: _vorm(w, HASH_RE),
    "gewijzigd": lambda w: _reeks(w, CODE_RE),
    "eigen_risk_class": lambda w: _vorm(w, KLASSE_RE),
    "sinds": _tijd,
    "request_id": lambda w: _vorm(w, UUID_RE),
}
AFWIJKING_VELDEN = ("reden", "afwijkingen", "methode", "before_hash", "after_hash")
MISLUKT_VELDEN = ("reden", "methode", "before_hash", "after_hash")
# Details van een weigering (executor of ``asm_policy.verify``); ``request_id`` is hier het verzoek waardoor de
# executor stopte (``executor_gestopt``), genest onder ``executor`` en dus nooit in plaats van het eigen request_id.
WEIGERING_VELDEN = ("reden", "fouten", "blokkades", "gewijzigd", "eigen_risk_class", "methoden", "sinds", "request_id")


def _van_executor(bron: Mapping[str, Any], velden: tuple[str, ...], *, alleen_aanwezig: bool = False) -> dict[str, Any]:
    """De velden uit ``velden`` in hun vaste vorm (``None`` als de vorm niet klopt), plus ``gestopt`` als echte ja/nee.
    Met ``alleen_aanwezig`` alleen de velden die in ``bron`` staan."""
    uit = {k: EXECUTOR_VELDEN[k](bron.get(k)) for k in velden if not alleen_aanwezig or k in bron}
    if isinstance(bron.get("gestopt"), bool):
        uit["gestopt"] = bron["gestopt"]
    return uit


def _stopgegevens(reden: Any, gestopt: Any) -> dict[str, Any]:
    """``reden`` en ``gestopt`` uit een executorantwoord of uit het journaal, voor het event ``action.run.failed`` (en
    daarmee voor het incident). Alleen een code en een echte ja/nee: ``gestopt`` komt alleen mee als de executor het
    zelf zegt, nooit afgeleid (S-P2-030; S-P2-040)."""
    uit: dict[str, Any] = {"reden": _reden(reden)}
    if isinstance(gestopt, bool):
        uit["gestopt"] = gestopt
    return uit


def _readback_bevestigt(req: ActionRequest, readback: dict[str, Any], after_hash: str) -> bool:
    """Toets de teruggelezen toestand aan de actie waarvoor de goedkeuring is verbruikt."""
    if req.action_id == "automation.flows.restore":
        snapshot_id = _vorm(readback.get("snapshot_id"), UUID_RE)
        return (
            readback.get("gelezen") is True
            and readback.get("gelijk_aan_momentopname") is True
            and snapshot_id is not None
            and snapshot_id == req.parameters.get("snapshot_id")
            and readback.get("checksum_sha256") == after_hash.removeprefix("sha256:")
        )
    if req.action_id == "sso.sessions.revoke":
        aantal = readback.get("ingetrokken_sessies")
        return readback.get("gelezen", True) is True and type(aantal) is int and aantal >= 0
    return True


def _bewijs_uitgevoerd(body: Mapping[str, Any], policy_hash: str, req: ActionRequest) -> dict[str, Any] | None:
    """Het resultaat van een geslaagde uitvoering, of ``None`` als het bewijs niet volledig is (S-P2-040, R-VEILIG-2):
    ``methode``, ``before_hash``, ``after_hash``, ``uitgevoerd_op`` en ``policy_hash`` (gelijk aan het eigen beleid)
    moeten er in de juiste vorm zijn. Zonder dat is "uitgevoerd" een onduidelijk antwoord, nooit een succes. Het
    antwoord moet ook aantoonbaar bij dit verzoek horen (``request_id`` en ``action_id``) en een readback als object
    hebben (S-P2-080, R-VEILIG-2)."""
    readback = _structuur(body.get("readback"), dict)
    if body.get("request_id") != str(req.id) or body.get("action_id") != req.action_id or readback is None:
        return None
    after_hash = _vorm(body.get("after_hash"), HASH_RE)
    if after_hash is None or not _readback_bevestigt(req, readback, after_hash):
        return None
    bewijs = {
        "methode": _vorm(body.get("methode"), METHODE_RE),
        "before_hash": _vorm(body.get("before_hash"), HASH_RE),
        "after_hash": after_hash,
        "policy_hash": policy_hash if body.get("policy_hash") == policy_hash else None,
        "uitgevoerd_op": _tijd(body.get("uitgevoerd_op")),
    }
    if any(w is None for w in bewijs.values()):
        return None
    return {
        "status": "uitgevoerd",
        **bewijs,
        "resource_etag": _vorm(body.get("resource_etag"), ETAG_RE),
        "readback": readback,
        "waarschuwingen": _reeks(body.get("waarschuwingen"), CODE_RE),
    }


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
    _wis_waarden(req)  # het verzoek is al naar de executor of geweigerd; de Hub stuurt het nooit opnieuw
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


# ------------------------------------------------------------------ eigenaar-connector (§6, §8 tweede tabel)
EIGENAAR_PROPOSE = "/connector/v1/propose"
EIGENAAR_APPLY = "/connector/v1/apply"
EIGENAAR_HASH_RE = re.compile(r"(?:sha256:)?([0-9a-f]{64})")
# Een ontbrekende route of functie bij de eigenaar is eerlijk capability_unavailable (§4.4, §6).
ONTBREEKT = (404, 405, 501)


def _met_eigenaar(cls: Classification, doel: Doel) -> Classification:
    """``requires_backup`` uit het voorstel van de eigenaar of uit het beleid (§8): alleen strenger, nooit losser."""
    if doel.eigenaar is not None and doel.eigenaar["requires_backup"] and not cls.requires_backup:
        return dataclasses.replace(cls, requires_backup=True)
    return cls


def _eigenaar(db: Session, settings: Settings, app_id: str) -> tuple[Service, str]:
    svc = db.scalars(select(Service).where(Service.app_id == app_id, Service.status == "active")).first()
    if svc is None:
        raise HubError(
            409,
            "eigenaar_niet_gekoppeld",
            f"De eigenaar van deze actie ({app_id}) is niet gekoppeld; er is niets voorgesteld of uitgevoerd.",
            {"eigenaar": app_id},
        )
    base, why = service_base_url(db, settings, svc)
    if base is None:
        raise HubError(
            409,
            "eigenaar_adres_onbekend",
            "Het adres van de eigenaar is niet gemeten (NAS-adres D03 + hostpoort uit de inventaris); er is niets "
            "voorgesteld of uitgevoerd.",
            {"eigenaar": app_id, "reason": why},
        )
    return svc, base


def _eigenaar_onbekend(reden: str) -> HubError:
    return HubError(
        409,
        "doel_onbekend",
        "De eigenaar gaf geen bruikbaar voorstel; onbekend telt nooit als ongewijzigd. Er is niets voorgesteld, "
        "goedgekeurd of uitgevoerd.",
        {"reason_code": reden},
    )


def _zelfde_eigenaarsaanvraag(
    body: Mapping[str, Any], target: Mapping[str, Any], parameters: Mapping[str, Any]
) -> bool:
    eigen_doel = body.get("target")
    standaardhost = {"host_id": HOST_IDS[0]}
    if not isinstance(eigen_doel, dict) or eigen_doel.get("host_id", HOST_IDS[0]) not in HOST_IDS:
        return False
    if (standaardhost | eigen_doel) != (standaardhost | dict(target)):
        return False
    try:
        # De ondertekening onderscheidt ook false en 0 in geneste parameters.
        return canonical_json(body.get("parameters")) == canonical_json(dict(parameters))
    except CanonicalError:
        return False


def _eigenaar_voorstel(
    db: Session,
    settings: Settings,
    keyring: KeyRing | None,
    actie: ActieDef,
    target: Mapping[str, Any],
    parameters: Mapping[str, Any],
    reden: str,
) -> Doel:
    """Het voorstel van de eigenaar (``POST /connector/v1/propose``, §6) als doel: zijn ``resource_etag`` en
    ``preview_hash`` binden de goedkeuring, want de eigenaar controleert bij ``apply`` dat die bij zijn eigen voorstel
    horen. Van het antwoord neemt de Hub alleen vaste velden in vaste vorm over (zoals bij de executor)."""
    eigenaar = str(actie.eigenaar)
    if keyring is None:  # pragma: no cover - elke route geeft de sleutels mee
        raise _eigenaar_onbekend("geen_sleutels")
    svc, base = _eigenaar(db, settings, eigenaar)
    bearer, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    try:
        res = servicecalls.call(
            base,
            "POST",
            EIGENAAR_PROPOSE,
            bearer=bearer,
            idempotency_key=str(uuid.uuid4()),  # elke herberekening is een nieuw voorstel bij de eigenaar
            body={
                "action_id": actie.action_id,
                "target": dict(target),
                "parameters": dict(parameters),
                "reason": reden[:300],
            },
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=settings.service_call_read_timeout,
        )
    except servicecalls.ServiceCallError as exc:
        raise _eigenaar_onbekend(f"eigenaar_{_reden(exc.reason) or ONBEKENDE_REDEN}") from None
    body = res.body if isinstance(res.body, dict) else {}
    if res.status in ONTBREEKT:
        raise HubError(
            501,
            "capability_unavailable",
            f"{eigenaar} biedt voor deze actie (nog) geen voorstel aan; er is niets voorgesteld.",
            {"eigenaar": eigenaar, "http_status": res.status},
        )
    code = _vorm(body.get("code"), CODE_RE)
    if 400 <= res.status < 500 and code is not None:
        raise HubError(
            409,
            "eigenaar_weigerde_voorstel",
            f"{eigenaar} weigerde het voorstel; er is niets voorgesteld.",
            {"eigenaar": eigenaar, "http_status": res.status, "code": code},
        )
    if res.status not in (200, 201):
        raise _eigenaar_onbekend(f"eigenaar_http_{res.status}")
    ph = EIGENAAR_HASH_RE.fullmatch(body["preview_hash"]) if isinstance(body.get("preview_hash"), str) else None
    et = EIGENAAR_HASH_RE.fullmatch(body["resource_etag"]) if isinstance(body.get("resource_etag"), str) else None
    voorstel_id = _vorm(body.get("proposal_id"), UUID_RE)
    diff = _structuur(body.get("diff"), list)
    backup = body.get("requires_backup")
    if (
        ph is None
        or et is None
        or voorstel_id is None
        or diff is None
        or not isinstance(backup, bool)
        or body.get("action_id") != actie.action_id
    ):
        raise _eigenaar_onbekend("eigenaar_antwoord_ongeldig")
    if actie.action_id in ("automation.flows.restore", "sso.sessions.revoke") and not _zelfde_eigenaarsaanvraag(
        body, target, parameters
    ):
        raise _eigenaar_onbekend("eigenaar_aanvraag_wijkt_af")
    return Doel(
        "eigenaar",
        eigenaar,
        f"sha256:{et.group(1)}",
        True,
        eigenaar={
            "voorstel_id": voorstel_id,
            "preview_hash": f"sha256:{ph.group(1)}",
            "requires_backup": backup,
            "diff": diff,
        },
    )


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
            # De eigenaar toetst zijn eigen preview_hash (§8); de Hub-hash ervan bond de goedkeuring al (R-VEILIG-1).
            "preview_hash": doel.eigenaar["preview_hash"] if doel.eigenaar is not None else ap.preview_hash,
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

    Dezelfde vaste vormen als bij een antwoord (S-P2-040, R-VEILIG-2 en -3): een rij van een ander verzoek of een andere
    actie telt als ``open``, en een rij ``uitgevoerd`` telt alleen met ``methode``, ``before_hash``, ``after_hash`` en
    een einde in de juiste vorm; anders ook ``open`` (de uitkomst blijft onbekend). Het journaal heeft geen
    ``policy_hash``: de executor controleert die zelf vóór hij iets uitvoert.
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
    gestopt = (res.body or {}).get("gestopt")
    stop = {"gestopt": gestopt} if isinstance(gestopt, bool) else {}
    if not rows:
        return "geen", stop
    laatste = rows[-1] if isinstance(rows[-1], dict) else {}
    gegevens = {
        "bron": "journaal_executor",
        "methode": _vorm(laatste.get("methode"), METHODE_RE),
        "before_hash": _vorm(laatste.get("before_hash"), HASH_RE),
        "after_hash": _vorm(laatste.get("after_hash"), HASH_RE),
        "detail": _reden(laatste.get("detail")),
        "gestart_op": _tijdstip(laatste.get("started_at")),
        "klaar_op": _tijdstip(laatste.get("finished_at")),
        **stop,
    }
    status = laatste.get("status")
    eigen = laatste.get("request_id") == str(req.id) and laatste.get("action_id") == req.action_id
    if not eigen or status not in ("uitgevoerd", "mislukt", "afwijking"):
        return "open", gegevens
    bewijs = (gegevens["methode"], gegevens["before_hash"], gegevens["after_hash"], gegevens["klaar_op"])
    if status == "uitgevoerd" and None in bewijs:
        return "open", gegevens
    return str(status), gegevens


def _antwoord(
    db: Session, req: ActionRequest, uitkomst: str, gegevens: dict[str, Any], actor: str
) -> tuple[int, dict[str, Any]]:
    """Leg een uitkomst uit het journaal vast en geef het antwoord (of het foutantwoord)."""
    if uitkomst == "uitgevoerd":
        _sluit(db, req, "uitgevoerd", {"status": "uitgevoerd", **gegevens}, actor=actor)
        return 200, weergave(db, req)
    stop = _stopgegevens(gegevens.get("detail"), gegevens.get("gestopt"))
    if uitkomst == "afwijking":
        _sluit(db, req, "afwijking", {**gegevens, "code": "afwijking", "reden": stop["reden"]}, actor=actor, extra=stop)
        raise Bewaard(
            409,
            "afwijking",
            "De toestand na de uitvoering wijkt af van de verwachting of is onbekend. De executor is gestopt; er is "
            "een incident gemaakt en er wordt niets herhaald.",
            {**stop, "request_id": str(req.id)},
        )
    _sluit(
        db, req, "mislukt", {**gegevens, "code": "uitvoering_mislukt", "reden": stop["reden"]}, actor=actor, extra=stop
    )
    raise Bewaard(
        502,
        "uitvoering_mislukt",
        "TrueNAS heeft de actie niet uitgevoerd; de toestand van het doel is onveranderd.",
        {"request_id": str(req.id), "reden": stop["reden"]},
    )


def _onbekend(db: Session, req: ActionRequest, reden: str, actor: str, *, eigenaar: bool = False) -> NoReturn:
    reden = _reden(reden) or ONBEKENDE_REDEN
    _sluit(db, req, "onbekend", {"code": "uitkomst_onbekend", "reden": reden}, actor=actor, extra={"reden": reden})
    raise Bewaard(
        502,
        "uitkomst_onbekend",
        "De eigenaar gaf geen bruikbaar antwoord; of de actie is uitgevoerd, is onbekend. De Hub herhaalt niets. "
        "Controleer de toestand bij de eigenaar zelf."
        if eigenaar
        else "De executor gaf geen bruikbaar antwoord; of de actie is uitgevoerd, is onbekend. De Hub herhaalt niets. "
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
    actie, cls, doel, preview, phash = _herbereken(db, settings, vault, policy, req, now, keyring)
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
    if actie.eigenaar is not None:
        svc, base = _eigenaar(db, settings, actie.eigenaar)
    elif actie.via_executor:
        svc, base = _executor(db, settings)
    else:
        raise HubError(501, "capability_unavailable", "Voor deze actie bestaat in deze versie nog geen uitvoerder.")
    kluis.controleer_revisies(db, req)  # een niet-bestaand kluispad: weigering vóór ondertekening (S-P2-070)

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
        _a, _c, eigen = check_decision(
            policy, verzoek, now=nu, herkend_als=doel.herkend_als, uitvoerder=actie.uitvoerder
        )
    if eigen is not None:
        _sluit(db, req, "mislukt", {"code": eigen.code, "message": eigen.melding, "bij": "hub"}, actor=principal.name)
        raise Bewaard(
            409,
            "uitvoering_geweigerd",
            "De eigen controle van de Hub wees het uitvoeringsverzoek af; er is niets naar de executor gestuurd.",
            {"request_id": str(req.id), "code": eigen.code, "details": eigen.details},
        )
    kluis.leg_afgifte_vast(db, req, ap, verzoek)  # §8.3: de hash van precies dit verzoek, vóór verzending
    bearer, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    try:
        res = servicecalls.call(
            base,
            "POST",
            EIGENAAR_APPLY if actie.eigenaar is not None else "/api/v1/execute",
            bearer=bearer,
            idempotency_key=str(nonce),
            body=verzoek,
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=float(actie.timeout_seconden + ANTWOORD_MARGE),
        )
    except servicecalls.ServiceCallError as exc:
        if actie.eigenaar is not None:
            # Een eigenaar heeft (nog) geen journaal voor de Hub: de uitkomst blijft onbekend, de Hub herhaalt niets.
            _onbekend(db, req, f"eigenaar_{exc.reason}", principal.name, eigenaar=True)
        uitkomst, gegevens = _journaal(db, settings, keyring, req)
        if uitkomst in ("uitgevoerd", "mislukt", "afwijking"):
            return _antwoord(db, req, uitkomst, gegevens, principal.name)
        _onbekend(db, req, f"executor_{exc.reason}", principal.name)
    gecodeerd = isinstance(res.body, dict) and _vorm(res.body.get("code"), CODE_RE) is not None
    if actie.eigenaar is not None and (res.status in (404, 405) or (res.status == 501 and not gecodeerd)):
        # De eigenaar kent de route apply (nog) niet: niets uitgevoerd, eerlijk capability_unavailable (§6).
        _sluit(
            db,
            req,
            "mislukt",
            {"code": "capability_unavailable", "http_status": res.status, "bij": "eigenaar"},
            actor=principal.name,
        )
        raise Bewaard(
            501,
            "capability_unavailable",
            f"{actie.eigenaar} kan deze actie (nog) niet uitvoeren; er is niets uitgevoerd.",
            {"request_id": str(req.id), "eigenaar": actie.eigenaar, "http_status": res.status},
        )
    return _verwerk(db, req, res, principal.name, policy.hash, eigenaar=actie.eigenaar is not None)


def _verwerk(
    db: Session,
    req: ActionRequest,
    res: servicecalls.CallResult,
    actor: str,
    policy_hash: str,
    *,
    eigenaar: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Het antwoord van de executor vastleggen. Alleen velden uit de vaste lijst (:func:`_van_executor`); de eigen
    velden van de Hub (``code``, ``request_id``, …) komen altijd ná die velden en zijn dus niet te overschrijven."""
    body = res.body if isinstance(res.body, dict) else {}
    code = body.get("code")
    ruw = body.get("details")
    details: dict[str, Any] = ruw if isinstance(ruw, dict) else {}
    melding = _melding(body.get("message"))
    if res.status == 200 and body.get("status") == "uitgevoerd":
        resultaat = _bewijs_uitgevoerd(body, policy_hash, req)
        if resultaat is None:
            # R-VEILIG-2: "uitgevoerd" zonder volledig bewijs is een onduidelijk antwoord, nooit een succes.
            _onbekend(db, req, BEWIJS_ONVOLLEDIG, actor, eigenaar=eigenaar)
        _sluit(db, req, "uitgevoerd", resultaat, actor=actor)
        return 200, weergave(db, req)
    if res.status == 409 and code == "afwijking":
        velden = _van_executor(details, AFWIJKING_VELDEN)
        stop = _stopgegevens(velden["reden"], velden.get("gestopt"))
        _sluit(db, req, "afwijking", {**velden, "code": "afwijking", "message": melding}, actor=actor, extra=stop)
        raise Bewaard(
            409,
            "afwijking",
            "De toestand na de uitvoering wijkt af van de verwachting of is onbekend. De executor is gestopt; er is "
            "een incident gemaakt en er wordt niets herhaald.",
            {**velden, "request_id": str(req.id)},
        )
    if not eigenaar and res.status == 502 and code == "uitvoering_mislukt":
        velden = _van_executor(details, MISLUKT_VELDEN)
        stop = _stopgegevens(velden["reden"], velden.get("gestopt"))
        _sluit(
            db, req, "mislukt", {**velden, "code": "uitvoering_mislukt", "message": melding}, actor=actor, extra=stop
        )
        raise Bewaard(
            502,
            "uitvoering_mislukt",
            "TrueNAS heeft de actie niet uitgevoerd; de toestand van het doel is onveranderd.",
            {**velden, "request_id": str(req.id)},
        )
    # Alleen een expliciete weigering telt als "niets uitgevoerd": een 4xx of 501 met code, of de eigen 502/503-codes
    # van de executor. Elke andere 5xx (time-out, gateway) bewijst niets: onbekend (R-VEILIG-4).
    weigering = 400 <= res.status < 500 or res.status == 501 or (not eigenaar and res.status in (502, 503))
    if isinstance(code, str) and CODE_RE.fullmatch(code) and weigering:
        # Een gestructureerde weigering van de executor: hij heeft niets uitgevoerd.
        schoon = _van_executor(details, WEIGERING_VELDEN, alleen_aanwezig=True)
        _sluit(
            db,
            req,
            "mislukt",
            {"code": code, "message": melding, "details": schoon, "http_status": res.status},
            actor=actor,
        )
        wie = "eigenaar" if eigenaar else "executor"
        raise Bewaard(
            501 if res.status == 501 else 409,
            "capability_unavailable" if res.status == 501 else "uitvoering_geweigerd",
            (melding or f"Deze functie bestaat bij de {wie} nog niet; er is niets uitgevoerd.")
            if res.status == 501
            else f"De {wie} heeft de actie geweigerd; er is niets uitgevoerd.",
            {"request_id": str(req.id), wie: {"code": code, "message": melding, "details": schoon}},
        )
    # Ook een code buiten het vaste patroon (vrije tekst, stuurtekens): geen bruikbaar antwoord.
    _onbekend(db, req, f"{'eigenaar' if eigenaar else 'executor'}_http_{res.status}", actor, eigenaar=eigenaar)


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
    if actie is not None and actie.eigenaar is not None:
        # shortcut: de eigenaar biedt de Hub (nog) geen journaal; de uitkomst blijft onbekend tot er een is (VERSIE 2).
        raise HubError(
            409,
            "uitkomst_onbekend",
            "De eigenaar heeft geen journaal voor de Hub; de uitkomst is niet vast te stellen. De Hub herhaalt niets.",
            {"request_id": str(req.id), "journaal": "geen_journaal_eigenaar"},
        )
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
