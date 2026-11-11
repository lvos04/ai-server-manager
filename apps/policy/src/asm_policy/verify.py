"""Inhoudelijke controle van een ``ExecutionRequest`` (contract 1.3 §8, ADR-0030).

De executor (en elke eigenaar-connector) vertrouwt het verzoek van de Hub niet op zijn woord maar controleert zelf
opnieuw: handtekening, vervaltijd, policy-hash, allowlist, parameterschema, risicoklasse en de goedkeuring. De Hub
draait dezelfde functies vlak vóór het versturen, zodat een fout in de Hub nooit als "de executor weigerde" opduikt.

Twee stappen, omdat de tweede het doel uit een eigen readback nodig heeft:

1. :func:`check_envelope` — vorm, handtekening, tijden, policy-hash. Geen netwerk.
2. :func:`check_decision` — allowlist, doel- en parameterschema, eigen classificatie (met ``herkend_als`` uit de eigen
   readback), risicoklasse ≥ eigen herberekening, en bij R2/R3 de gebonden goedkeuring.

Wat alleen de uitvoerder kan weten (nonce al gebruikt, ETag van het doel nu, toestand van de pool) hoort hier niet.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from asm_policy import execreq
from asm_policy.engine import Classification, class_at_least, classify
from asm_policy.loader import ActieDef, Policy
from asm_policy.params import validate_parameters, validate_target


@dataclass(frozen=True)
class Weigering:
    """Een weigering met een stabiele code; ``status`` is de HTTP-status die de uitvoerder teruggeeft."""

    status: int
    code: str
    melding: str
    details: dict[str, Any] = field(default_factory=dict)


def check_envelope(
    policy: Policy, request: Any, keys: Iterable[Ed25519PublicKey], *, now: datetime
) -> Weigering | None:
    fouten = execreq.structure_errors(request)
    if fouten:
        return Weigering(
            422,
            "execution_request_ongeldig",
            "Het uitvoeringsverzoek heeft niet de juiste vorm.",
            {"fouten": fouten[:20]},
        )
    if not execreq.verify_signature(request, keys):
        return Weigering(
            403, "handtekening_ongeldig", "De handtekening van de Hub klopt niet met de gepinde policy-sleutel."
        )
    skew = timedelta(seconds=execreq.CLOCK_SKEW)
    issued = execreq.parse_ts(request["issued_at"])
    expires = execreq.parse_ts(request["expires_at"])
    if issued is None or expires is None:  # pragma: no cover - al gecontroleerd in structure_errors
        return Weigering(422, "execution_request_ongeldig", "Ongeldige tijd.")
    if issued > now + skew:
        return Weigering(403, "verzoek_nog_niet_geldig", "Het uitvoeringsverzoek is in de toekomst uitgegeven.")
    if expires <= now:
        return Weigering(403, "verzoek_verlopen", "Het uitvoeringsverzoek is verlopen.")
    if expires <= issued or (expires - issued).total_seconds() > execreq.MAX_REQUEST_SECONDS:
        return Weigering(403, "verzoek_geldigheid_ongeldig", "Een uitvoeringsverzoek is hooguit 15 minuten geldig.")
    if request["policy_decision"]["policy_hash"] != policy.hash:
        return Weigering(
            409,
            "policy_hash_verschilt",
            "Het beleid van de Hub is niet hetzelfde als dat van de uitvoerder; er is niets uitgevoerd.",
            {"eigen_policy_hash": policy.hash},
        )
    return None


def check_decision(
    policy: Policy,
    request: Mapping[str, Any],
    *,
    now: datetime,
    herkend_als: str | Iterable[str] | None,
    uitvoerder: str,
) -> tuple[ActieDef | None, Classification | None, Weigering | None]:
    prop = request["proposal"]
    actie = policy.actie(str(prop["action_id"]))
    eigen = classify(
        policy,
        action_id=str(prop["action_id"]),
        target=prop["target"],
        parameters=prop["parameters"],
        actor_type=str(prop["actor"]["type"]),
        herkend_als=herkend_als,
    )
    if eigen.geweigerd:
        return (
            actie,
            eigen,
            Weigering(
                403,
                "actie_geweigerd",
                "Het beleid weigert deze actie.",
                {"blokkades": [b.as_dict() for b in eigen.blokkades]},
            ),
        )
    if eigen.gereserveerd is not None:
        return actie, eigen, Weigering(501, "capability_unavailable", eigen.gereserveerd.reden_nl)
    if actie is None or not eigen.known:
        return None, eigen, Weigering(403, "actie_niet_toegestaan", "Deze actie staat niet op de allowlist.")
    if actie.uitvoerder != uitvoerder:
        return actie, eigen, Weigering(403, "actie_niet_toegestaan", "Deze actie hoort niet bij deze uitvoerder.")
    fouten = validate_target(actie, prop["target"])
    fouten += [] if fouten else validate_parameters(policy, actie, prop["target"], prop["parameters"])
    if fouten:
        return (
            actie,
            eigen,
            Weigering(
                422,
                "parameters_ongeldig",
                "Doel of parameters voldoen niet aan het schema.",
                {"fouten": [f.as_dict() for f in fouten[:20]]},
            ),
        )
    besluit = request["policy_decision"]
    if not class_at_least(str(besluit["risk_class"]), eigen.risk_class):
        return (
            actie,
            eigen,
            Weigering(
                403,
                "risicoklasse_te_laag",
                "De risicoklasse in het verzoek is lager dan de eigen herberekening.",
                {"eigen_risk_class": eigen.risk_class},
            ),
        )
    approval = request.get("approval")
    if not eigen.requires_approval:
        return actie, eigen, None
    if not isinstance(approval, Mapping):
        return actie, eigen, Weigering(403, "goedkeuring_ontbreekt", "Deze actie vraagt een menselijke goedkeuring.")
    fout = approval_problem(policy, prop, approval, eigen, now=now)
    return actie, eigen, fout


def approval_problem(
    policy: Policy, prop: Mapping[str, Any], approval: Mapping[str, Any], eigen: Classification, *, now: datetime
) -> Weigering | None:
    """Een goedkeuring hoort bij precies deze actie, dit doel, deze parameters, deze ETag en dit beleid (EX19)."""
    skew = timedelta(seconds=execreq.CLOCK_SKEW)
    approved = execreq.parse_ts(approval.get("approved_at"))
    expires = execreq.parse_ts(approval.get("expires_at"))
    if approved is None or expires is None:
        return Weigering(422, "execution_request_ongeldig", "Ongeldige tijd in de goedkeuring.")
    if approved > now + skew:
        return Weigering(403, "goedkeuring_ongeldig", "De goedkeuring ligt in de toekomst.")
    if expires <= now:
        return Weigering(403, "goedkeuring_verlopen", "De goedkeuring is verlopen (hooguit 15 minuten geldig).")
    if expires <= approved or (expires - approved).total_seconds() > execreq.MAX_APPROVAL_SECONDS:
        return Weigering(403, "goedkeuring_ongeldig", "Een goedkeuring is hooguit 15 minuten geldig.")
    gebonden = {
        "policy_hash": approval.get("policy_hash") == policy.hash,
        "resource_etag": approval.get("resource_etag") == prop.get("expected_version"),
        "action_scope": approval.get("action_scope")
        == execreq.action_scope(str(prop["action_id"]), prop["target"], prop["parameters"]),
        "risk_class": class_at_least(str(approval.get("risk_class")), eigen.risk_class),
    }
    anders = sorted(k for k, ok in gebonden.items() if not ok)
    if anders:
        return Weigering(
            409,
            "goedkeuring_past_niet",
            "De goedkeuring hoort niet (meer) bij deze actie; keur opnieuw goed.",
            {"gewijzigd": anders},
        )
    if eigen.requires_backup and not approval.get("backup_checkpoint_id"):
        return Weigering(
            409, "backup_checkpoint_ontbreekt", "Deze actie vraagt een geverifieerd herstelpunt in de goedkeuring."
        )
    return None
