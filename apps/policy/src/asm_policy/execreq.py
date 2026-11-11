"""``ExecutionRequest`` ondertekenen en controleren (contract 1.3 §8; formaat vastgelegd in ADR-0030 en
``docs/EXECUTION_REQUEST.md``).

Vorm (alle tijden ``YYYY-MM-DDTHH:MM:SSZ``, UTC)::

    {"proposal": ActionProposal, "approval": Approval | null,
     "policy_decision": {"risk_class", "rule_ids", "policy_hash"},
     "issued_at", "expires_at", "nonce": "<uuid>", "signature": "<base64url, zonder =>"}

``signature`` = Ed25519 (policy-sleutel van de Hub) over de canonieke JSON (:mod:`asm_policy.canonical`) van het object
**zonder** het veld ``signature``. Er staat geen sleutel-ID in: een ontvanger probeert elke gepinde policy-sleutel
(``pins.policy``, hooguit twee tijdens een rotatie). Een via HTTP opgehaalde sleutel voegt nooit vertrouwen toe.

``approval.action_scope`` = ``{"action_id", "target", "parameters_sha256"}``: de goedkeuring hoort bij precies deze
actie, dit doel en deze parameters; ``approval.resource_etag`` is gelijk aan ``proposal.expected_version``.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from asm_policy.canonical import canonical_json, canonical_sha256
from asm_policy.loader import RISK_CLASSES

MAX_APPROVAL_SECONDS = 15 * 60
MAX_REQUEST_SECONDS = 15 * 60
CLOCK_SKEW = 30
TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ETAG_RE = re.compile(r"^(sha256:[0-9a-f]{64}|absent|dataset:[^\s]{1,200}|snapshot:[^\s]{1,264}|geen|eigenaar)$")
PROPOSAL_KEYS = {
    "idempotency_key",
    "action_id",
    "target",
    "parameters",
    "reason",
    "actor",
    "expected_version",
    "risk_claim",
    "evidence_ids",
    "expires_in_seconds",
}
APPROVAL_KEYS = {
    "approval_id",
    "request_id",
    "preview_hash",
    "resource_etag",
    "policy_hash",
    "risk_class",
    "approved_by",
    "approved_at",
    "expires_at",
    "one_time_nonce",
    "backup_checkpoint_id",
    "action_scope",
}
REQUEST_KEYS = {"proposal", "approval", "policy_decision", "issued_at", "expires_at", "nonce", "signature"}


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    if b64url(raw) != text:
        raise ValueError("geen canonieke base64url")
    return raw


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not TS_RE.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def parameters_sha256(parameters: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(parameters))


def action_scope(action_id: str, target: Mapping[str, Any], parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {"action_id": action_id, "target": dict(target), "parameters_sha256": parameters_sha256(parameters)}


def signing_bytes(request: Mapping[str, Any]) -> bytes:
    return canonical_json({k: v for k, v in request.items() if k != "signature"})


def sign(request: Mapping[str, Any], key: Ed25519PrivateKey) -> dict[str, Any]:
    body = {k: v for k, v in request.items() if k != "signature"}
    return {**body, "signature": b64url(key.sign(canonical_json(body)))}


def verify_signature(request: Mapping[str, Any], keys: Iterable[Ed25519PublicKey]) -> bool:
    sig = request.get("signature")
    if not isinstance(sig, str) or not sig:
        return False
    try:
        raw = b64url_decode(sig)
        message = signing_bytes(request)
    except (ValueError, TypeError):
        return False
    for key in keys:
        try:
            key.verify(raw, message)
            return True
        except InvalidSignature:
            continue
    return False


def structure_errors(request: Any) -> list[dict[str, str]]:
    """Vormcontrole (strikt; onbekende velden zijn een fout). Inhoudelijke controles doet de ontvanger."""
    errs: list[dict[str, str]] = []

    def bad(veld: str, fout: str) -> None:
        errs.append({"veld": veld, "fout": fout})

    if not isinstance(request, Mapping):
        return [{"veld": "", "fout": "verwacht een object"}]
    for k in set(request) - REQUEST_KEYS:
        bad(k, "onbekend veld")
    for k in REQUEST_KEYS - set(request):
        bad(k, "verplicht veld ontbreekt")
    p = request.get("proposal")
    if not isinstance(p, Mapping):
        bad("proposal", "verwacht een object")
    else:
        for k in set(p) - PROPOSAL_KEYS:
            bad(f"proposal.{k}", "onbekend veld")
        for k in ("idempotency_key", "action_id", "target", "parameters", "actor", "expected_version"):
            if k not in p:
                bad(f"proposal.{k}", "verplicht veld ontbreekt")
        if not isinstance(p.get("action_id"), str):
            bad("proposal.action_id", "verwacht tekst")
        if not isinstance(p.get("target"), Mapping):
            bad("proposal.target", "verwacht een object")
        if not isinstance(p.get("parameters"), Mapping):
            bad("proposal.parameters", "verwacht een object")
        if not (isinstance(p.get("idempotency_key"), str) and UUID_RE.fullmatch(p["idempotency_key"])):
            bad("proposal.idempotency_key", "verwacht een UUID")
        if not (isinstance(p.get("expected_version"), str) and ETAG_RE.fullmatch(p["expected_version"])):
            bad("proposal.expected_version", "ongeldige versie/ETag")
        actor = p.get("actor")
        if not (isinstance(actor, Mapping) and isinstance(actor.get("type"), str) and isinstance(actor.get("id"), str)):
            bad("proposal.actor", "verwacht {type, id}")
    a = request.get("approval")
    if a is not None:
        if not isinstance(a, Mapping):
            bad("approval", "verwacht een object of null")
        else:
            for k in set(a) - APPROVAL_KEYS:
                bad(f"approval.{k}", "onbekend veld")
            for k in APPROVAL_KEYS - set(a):
                bad(f"approval.{k}", "verplicht veld ontbreekt")
            for k in ("approval_id", "request_id", "one_time_nonce"):
                if not (isinstance(a.get(k), str) and UUID_RE.fullmatch(a[k])):
                    bad(f"approval.{k}", "verwacht een UUID")
            for k in ("preview_hash", "policy_hash"):
                if not (isinstance(a.get(k), str) and SHA_RE.fullmatch(a[k])):
                    bad(f"approval.{k}", "verwacht sha256:<hex>")
            if a.get("risk_class") not in RISK_CLASSES:
                bad("approval.risk_class", "R0–R3")
            for k in ("approved_at", "expires_at"):
                if parse_ts(a.get(k)) is None:
                    bad(f"approval.{k}", "verwacht YYYY-MM-DDTHH:MM:SSZ")
            if not isinstance(a.get("approved_by"), str) or not a.get("approved_by"):
                bad("approval.approved_by", "verwacht tekst")
            if a.get("backup_checkpoint_id") is not None and not isinstance(a.get("backup_checkpoint_id"), str):
                bad("approval.backup_checkpoint_id", "verwacht tekst of null")
            if not isinstance(a.get("action_scope"), Mapping):
                bad("approval.action_scope", "verwacht een object")
    d = request.get("policy_decision")
    if not isinstance(d, Mapping) or set(d) != {"risk_class", "rule_ids", "policy_hash"}:
        bad("policy_decision", "verwacht precies {risk_class, rule_ids, policy_hash}")
    else:
        if d.get("risk_class") not in RISK_CLASSES:
            bad("policy_decision.risk_class", "R0–R3")
        if not (isinstance(d.get("rule_ids"), list) and all(isinstance(r, str) for r in d["rule_ids"])):
            bad("policy_decision.rule_ids", "verwacht een lijst")
        if not (isinstance(d.get("policy_hash"), str) and SHA_RE.fullmatch(d["policy_hash"])):
            bad("policy_decision.policy_hash", "verwacht sha256:<hex>")
    for k in ("issued_at", "expires_at"):
        if parse_ts(request.get(k)) is None:
            bad(k, "verwacht YYYY-MM-DDTHH:MM:SSZ")
    if not (isinstance(request.get("nonce"), str) and UUID_RE.fullmatch(request["nonce"])):
        bad("nonce", "verwacht een UUID")
    if not isinstance(request.get("signature"), str):
        bad("signature", "verwacht tekst")
    return errs
