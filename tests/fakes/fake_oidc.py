"""In-repo OIDC-fakes (alleen tests): een identity provider in de vorm van Authentik en de SSO-routes van
home-control-hub. Gemodelleerd naar OIDC Core/Discovery en RFC 7636 (PKCE); de padvorm volgt Authentik
(``/application/o/<slug>/``). NIET GEVALIDEERD tegen een echte Authentik.

``FakeOidc`` levert discovery, JWKS (RS256, met ``kid``), ``/authorize`` (geeft direct een code voor de ingestelde
gebruiker, zoals na een geslaagde login bij Authentik), ``/token`` (controleert code, redirect_uri, clientgeheim en de
PKCE-verifier) en ``/userinfo``. Storingen/aanvallen: ``claims_override`` (bv. verkeerde ``iss``/``aud``/``nonce``),
``sign_with`` (``RS256`` | ``HS256`` | ``none`` | ``andere_sleutel``), ``rotate_key()``, ``offline()`` (via FakeHTTP) en
``token_status``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from fakes.fake_http import FakeHTTP, Reply, Seen

SLUG = "hub"


def _b64(n: int) -> str:
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _key() -> tuple[Any, dict[str, str]]:
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub = priv.public_key().public_numbers()
    kid = secrets.token_hex(8)
    return priv, {"kty": "RSA", "kid": kid, "use": "sig", "alg": "RS256", "n": _b64(pub.n), "e": _b64(pub.e)}


@dataclass
class Gebruiker:
    sub: str = "authentik-sub-0001"
    preferred_username: str = "leon"
    name: str = "Leon"
    email: str = "leon@example.org"
    groups: list[str] = field(default_factory=lambda: ["hub-admins"])


class FakeOidc(FakeHTTP):
    def __init__(
        self,
        client_id: str = "hub-client",
        client_secret: str = "Client-Geheim-1234567890-abcdefghij",  # noqa: S107 - alleen tests
    ) -> None:
        super().__init__()
        self.client_id, self.client_secret = client_id, client_secret
        self.priv, self.jwk = _key()
        self.user = Gebruiker()
        self.codes: dict[str, dict[str, Any]] = {}
        self.claims_override: dict[str, Any] = {}
        self.sign_with = "RS256"
        self.groups_in_id_token = True
        self.token_status: int | None = None
        self.pkce_methods = ["plain", "S256"]
        self.algs = ["RS256"]
        self.issued_tokens: list[str] = []

    @property
    def issuer(self) -> str:
        return f"{self.url}/application/o/{SLUG}/"

    def rotate_key(self) -> None:
        self.priv, self.jwk = _key()

    def metadata(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": f"{self.url}/application/o/authorize/",
            "token_endpoint": f"{self.url}/application/o/token/",
            "userinfo_endpoint": f"{self.url}/application/o/userinfo/",
            "end_session_endpoint": f"{self.url}/application/o/{SLUG}/end-session/",
            "jwks_uri": f"{self.url}/application/o/{SLUG}/jwks/",
            "response_types_supported": ["code", "id_token", "id_token token", "code token"],
            "code_challenge_methods_supported": self.pkce_methods,
            "id_token_signing_alg_values_supported": self.algs,
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "subject_types_supported": ["public"],
        }

    def _id_token(self, nonce: str | None) -> str:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": self.issuer,
            "sub": self.user.sub,
            "aud": self.client_id,
            "exp": now + 300,
            "iat": now,
            "auth_time": now,
            "nonce": nonce,
            "preferred_username": self.user.preferred_username,
            "name": self.user.name,
            "email": self.user.email,
        }
        if self.groups_in_id_token:
            claims["groups"] = list(self.user.groups)
        claims.update(self.claims_override)
        claims = {k: v for k, v in claims.items() if v is not None}
        if self.sign_with == "HS256":
            return jwt.encode(claims, self.client_secret, algorithm="HS256")
        if self.sign_with == "none":
            head = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
            body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
            return f"{head}.{body}."
        key = self.priv if self.sign_with == "RS256" else rsa.generate_private_key(public_exponent=65537, key_size=2048)
        return jwt.encode(claims, key, algorithm="RS256", headers={"kid": self.jwk["kid"]})

    def authorize(self, url: str) -> str:
        """Simuleert een geslaagde login bij de identity provider: geeft de callback-URL met code en state."""
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        assert q["response_type"] == "code" and q["client_id"] == self.client_id
        assert q["code_challenge_method"] == "S256" and q["code_challenge"]
        code = secrets.token_urlsafe(24)
        self.codes[code] = {
            "redirect_uri": q["redirect_uri"],
            "challenge": q["code_challenge"],
            "nonce": q.get("nonce"),
            "used": False,
            "scope": q.get("scope"),
        }
        return f"{q['redirect_uri']}?{urlencode({'code': code, 'state': q['state']})}"

    def _client_ok(self, seen: Seen, form: dict[str, str]) -> bool:
        auth = seen.headers.get("authorization", "")
        if auth.lower().startswith("basic "):
            from urllib.parse import unquote

            cid, _, sec = base64.b64decode(auth[6:]).decode().partition(":")
            return unquote(cid) == self.client_id and unquote(sec) == self.client_secret
        return form.get("client_id") == self.client_id and form.get("client_secret") == self.client_secret

    def handle(self, seen: Seen) -> Reply:
        p = seen.path
        if p == f"/application/o/{SLUG}/.well-known/openid-configuration":
            return Reply(200, self.metadata())
        if p == f"/application/o/{SLUG}/jwks/":
            return Reply(200, {"keys": [self.jwk]})
        if p == "/application/o/token/" and seen.method == "POST":
            if self.token_status is not None:
                return Reply(self.token_status, {"error": "server_error"})
            form = {k: v[0] for k, v in parse_qs(seen.body.decode()).items()}
            if not self._client_ok(seen, form):
                return Reply(401, {"error": "invalid_client"})
            entry = self.codes.get(form.get("code", ""))
            if form.get("grant_type") != "authorization_code" or entry is None or entry["used"]:
                return Reply(400, {"error": "invalid_grant"})
            entry["used"] = True
            verifier = form.get("code_verifier", "")
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
            if challenge != entry["challenge"] or form.get("redirect_uri") != entry["redirect_uri"]:
                return Reply(400, {"error": "invalid_grant", "error_description": "pkce of redirect_uri"})
            access = secrets.token_urlsafe(24)
            self.issued_tokens.append(access)
            return Reply(
                200,
                {
                    "access_token": access,
                    "token_type": "Bearer",
                    "expires_in": 300,
                    "id_token": self._id_token(entry["nonce"]),
                },
            )
        if p == "/application/o/userinfo/":
            auth = seen.headers.get("authorization", "")
            if not auth.startswith("Bearer ") or auth[7:] not in self.issued_tokens:
                return Reply(401, {"error": "invalid_token"})
            return Reply(
                200,
                {
                    "sub": self.user.sub,
                    "preferred_username": self.user.preferred_username,
                    "groups": list(self.user.groups),
                },
            )
        return Reply(404, {"detail": "Not found."})


class FakeHchSso(FakeHTTP):
    """SSO-routes van home-control-hub (alleen wat de Hub leest), met echte controle van de Hub-JWT's."""

    def __init__(self, public_key: Any, service_id: str) -> None:
        super().__init__()
        self.public_key, self.service_id = public_key, service_id
        self.least_privilege = "deels_gecontroleerd"
        self.rights_status = "verouderd"
        self.rejected: list[str] = []

    def _claims(self, seen: Seen) -> dict[str, Any] | None:
        try:
            return dict(
                jwt.decode(
                    seen.headers.get("authorization", "").removeprefix("Bearer "),
                    self.public_key,
                    algorithms=["EdDSA"],
                    audience="home-control-hub",
                )
            )
        except jwt.PyJWTError as exc:
            self.rejected.append(type(exc).__name__)
            return None

    def handle(self, seen: Seen) -> Reply:
        claims = self._claims(seen)
        if claims is None:
            return Reply(401, {"code": "unauthorized", "message": "Nee.", "details": {"reason": "invalid_token"}})
        if seen.path == "/integrations/v1/sso/authentik":
            if claims.get("token_use") != "hub_service" or claims.get("service_id") != self.service_id:
                return Reply(
                    401, {"code": "unauthorized", "message": "Nee.", "details": {"reason": "token_use_invalid"}}
                )
            return Reply(
                200,
                {
                    "detection": {
                        "status": "degraded",
                        "token": {
                            "least_privilege": self.least_privilege,
                            "message_nl": "Rolrechten niet volledig te controleren.",
                        },
                    }
                },
            )
        if seen.path == "/integrations/v1/sso/rights":
            if claims.get("token_use") != "user" or "admin" not in claims.get("roles", []):
                return Reply(403, {"code": "forbidden", "message": "Alleen admin.", "details": {}})
            return Reply(
                200,
                {
                    "status": self.rights_status,
                    "freshness": {
                        "status": self.rights_status,
                        "message_nl": "Verouderd: huidige rechten in Authentik zijn onbekend.",
                    },
                    "rights": {"leon": {"groups": ["hub-admins"]}},
                },
            )
        if seen.path == "/integrations/v1/sso/role-mappings":
            return Reply(
                200,
                {
                    "items": [{"app_id": "ai-server-manager", "authentik_group": "hub-admins", "role": "admin"}],
                    "next_cursor": None,
                },
            )
        return Reply(404, {"code": "not_found", "message": "Niet gevonden.", "details": {}})
