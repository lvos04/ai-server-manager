"""Fake eigenaar-connector van ``home-control-hub`` (alleen tests) volgens contract 1.3 §6 en §8 (tweede tabel).

Zo hoort de eigenaar zich te gedragen, met testgegevens: ``POST /connector/v1/propose`` geeft een voorstel met
``preview_hash`` en ``resource_etag``; ``POST /connector/v1/apply`` controleert zelf opnieuw, net als de executor: de
dienst-JWT van de Hub, de handtekening tegen de gepinde policy-sleutel, vervaltijd en policy-hash
(:func:`asm_policy.verify.check_envelope`), allowlist, actor, schema en goedkeuring (:func:`check_decision`), en dat de
goedkeuring bij een eigen voorstel hoort (``preview_hash`` en ``expected_version``). Pas daarna volgt het vaste
antwoord ``apply_reply``; standaard ``501 capability_unavailable``, zoals de echte eigenaar nu (SSO-uitvoering is daar
nog geblokkeerd). ``apply_route = False`` bootst een eigenaar zonder de route ``apply`` na (404).
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import jwt
from asm_policy import Policy
from asm_policy.canonical import canonical_sha256
from asm_policy.verify import check_decision, check_envelope
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from fakes.fake_http import FakeHTTP, Reply, Seen

APP_ID = "home-control-hub"
UITVOERDER = f"eigenaar:{APP_ID}"
BACKUP = {"sso.oidc.hub.register": True, "sso.sessions.revoke": False, "automation.flows.restore": False}


def _fout(status: int, code: str, message: str = "Geweigerd.", details: dict[str, Any] | None = None) -> Reply:
    return Reply(status, {"code": code, "message": message, "details": details or {}, "trace_id": "fake"})


class FakeEigenaar(FakeHTTP):
    def __init__(self, jwt_key: Ed25519PublicKey, policy_key: Ed25519PublicKey, policy: Policy) -> None:
        super().__init__()
        self.jwt_key, self.policy_key, self.policy = jwt_key, policy_key, policy
        self.etag = "e" * 64
        self.voorstellen: dict[str, dict[str, Any]] = {}  # preview_hash → voorstel
        self.geweigerd: list[str] = []
        self.geaccepteerd: list[dict[str, Any]] = []
        self.apply_route = True
        self.apply_reply = _fout(501, "capability_unavailable", "Uitvoeren is voor deze actie niet beschikbaar.")
        self.propose_reply: Reply | None = None  # een vast antwoord op propose (storingsproef)

    def _jwt(self, seen: Seen) -> bool:
        try:
            claims = jwt.decode(
                seen.headers.get("authorization", "")[7:],
                self.jwt_key,
                algorithms=["EdDSA"],
                audience=APP_ID,
                issuer="hub",
            )
        except jwt.PyJWTError as exc:
            self.geweigerd.append(type(exc).__name__)
            return False
        return claims.get("token_use") == "hub_service" and claims.get("sub") == "hub"

    def handle(self, seen: Seen) -> Reply:
        if seen.method == "POST" and seen.path == "/connector/v1/apply" and not self.apply_route:
            return Reply(404, {"detail": "Not Found"})
        if not self._jwt(seen):
            return _fout(401, "unauthorized")
        body = json.loads(seen.body or b"{}")
        if seen.method == "POST" and seen.path == "/connector/v1/propose":
            return self.propose_reply or self._propose(body)
        if seen.method == "POST" and seen.path == "/connector/v1/apply":
            return self._apply(body)
        return Reply(404, {"detail": "Not Found"})

    def _propose(self, body: dict[str, Any]) -> Reply:
        aid = body.get("action_id")
        if aid not in BACKUP:
            return _fout(422, "onbekende_actie")
        diff = [{"object": "sessies", "operation": "intrekken", "parameters": body.get("parameters")}]
        voorstel = {
            "proposal_id": str(uuid.uuid4()),
            "action_id": aid,
            "target": {"system": "authentik"},
            "parameters": body.get("parameters"),
            "resource_etag": self.etag,
            "diff": diff,
            "requires_backup": BACKUP[aid],
        }
        voorstel["preview_hash"] = canonical_sha256([aid, body.get("parameters"), diff, self.etag]).removeprefix(
            "sha256:"
        )
        self.voorstellen[voorstel["preview_hash"]] = voorstel
        return Reply(201, voorstel)

    def _apply(self, body: dict[str, Any]) -> Reply:
        from hub.timeutil import utcnow

        now = utcnow()
        fout = check_envelope(self.policy, body, [self.policy_key], now=now)
        if fout is None:
            _a, _c, fout = check_decision(self.policy, body, now=now, herkend_als=None, uitvoerder=UITVOERDER)
        if fout is not None:
            self.geweigerd.append(fout.code)
            return _fout(fout.status, fout.code, fout.melding, fout.details)
        approval = body.get("approval") or {}
        eigen = self.voorstellen.get(str(approval.get("preview_hash", "")).removeprefix("sha256:"))
        if eigen is None or body["proposal"]["expected_version"] != f"sha256:{eigen['resource_etag']}":
            self.geweigerd.append("goedkeuring_past_niet")
            return _fout(409, "goedkeuring_past_niet")
        self.geaccepteerd.append(body)
        return self.apply_reply
