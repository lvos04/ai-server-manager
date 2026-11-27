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
import threading
import uuid
from typing import Any

import jwt
from asm_policy import Policy
from asm_policy.canonical import canonical_json, canonical_sha256
from asm_policy.verify import check_decision, check_envelope
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from fakes.fake_http import FakeHTTP, Reply, Seen

APP_ID = "home-control-hub"
UITVOERDER = f"eigenaar:{APP_ID}"
BACKUP = {"sso.oidc.hub.register": True, "sso.sessions.revoke": False, "automation.flows.restore": False}


def _fout(status: int, code: str, message: str = "Geweigerd.", details: dict[str, Any] | None = None) -> Reply:
    return Reply(status, {"code": code, "message": message, "details": details or {}, "trace_id": "fake"})


class FakeEigenaar(FakeHTTP):
    def __init__(
        self,
        jwt_key: Ed25519PublicKey,
        policy_key: Ed25519PublicKey,
        policy: Policy,
        service_id: str,
    ) -> None:
        super().__init__()
        self.jwt_key, self.policy_key, self.policy = jwt_key, policy_key, policy
        self.service_id = service_id
        self.gebruikte_jtis: set[str] = set()
        self.gebruikte_nonces: set[str] = set()
        self.gebruikte_goedkeuringen: set[str] = set()
        self._slot = threading.Lock()
        self.etag = "e" * 64
        self.voorstellen: dict[str, dict[str, Any]] = {}  # preview_hash → voorstel
        self.geweigerd: list[str] = []
        self.geaccepteerd: list[dict[str, Any]] = []
        self.apply_route = True
        self.apply_reply = _fout(
            501,
            "capability_unavailable",
            "Uitvoeren is voor deze actie niet beschikbaar.",
        )
        self.propose_reply: Reply | None = None  # een vast antwoord op propose (storingsproef)

    def _jwt(self, seen: Seen) -> bool:
        bearer = seen.headers.get("authorization", "")
        if not bearer.startswith("Bearer "):
            return False
        try:
            claims = jwt.decode(
                bearer[7:],
                self.jwt_key,
                algorithms=["EdDSA"],
                audience=APP_ID,
                issuer="hub",
                options={"require": ["exp", "iat", "nbf", "jti"], "strict_aud": True},
            )
        except jwt.PyJWTError as exc:
            self.geweigerd.append(type(exc).__name__)
            return False
        if (
            claims.get("token_use"),
            claims.get("sub"),
            claims.get("roles"),
            claims.get("service_id"),
        ) != ("hub_service", "hub", ["service"], self.service_id):
            return False
        jti = claims.get("jti")
        if not isinstance(jti, str) or not 1 <= len(jti) <= 128:
            return False
        with self._slot:
            if jti in self.gebruikte_jtis:
                return False
            self.gebruikte_jtis.add(jti)
        return True

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
        if aid == "automation.flows.restore":
            diff = [
                {
                    "object": "node_red",
                    "operation": "terugzetten",
                    "key": body["parameters"].get("snapshot_id"),
                    "changes": [
                        {
                            "field": "checksum_sha256",
                            "before": self.etag,
                            "after": "2" * 64,
                        }
                    ],
                }
            ]
        else:
            diff = [
                {
                    "object": "sessies",
                    "operation": "intrekken",
                    "parameters": body["parameters"],
                }
            ]
        voorstel = {
            "proposal_id": str(uuid.uuid4()),
            "action_id": aid,
            "target": body["target"],
            "parameters": body["parameters"],
            "resource_etag": self.etag,
            "diff": diff,
            "requires_backup": BACKUP[aid],
        }
        voorstel["preview_hash"] = canonical_sha256(
            [aid, body["target"], body["parameters"], diff, self.etag]
        ).removeprefix("sha256:")
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
        voorstel = body["proposal"]
        if (
            eigen is None
            or voorstel["expected_version"] != f"sha256:{eigen['resource_etag']}"
            or eigen["action_id"] != voorstel["action_id"]
            or canonical_json(eigen["target"]) != canonical_json(voorstel["target"])
            or canonical_json(eigen["parameters"]) != canonical_json(voorstel["parameters"])
        ):
            self.geweigerd.append("goedkeuring_past_niet")
            return _fout(409, "goedkeuring_past_niet")
        with self._slot:
            if body["nonce"] in self.gebruikte_nonces or approval["approval_id"] in self.gebruikte_goedkeuringen:
                return _fout(409, "al_gebruikt")
            self.gebruikte_nonces.add(body["nonce"])
            self.gebruikte_goedkeuringen.add(approval["approval_id"])
            self.geaccepteerd.append(body)
        return self.apply_reply
