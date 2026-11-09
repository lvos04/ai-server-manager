"""Sleutelbeheer: Ed25519-sleutels uit ``/appdata/secrets``, JWKS en kortlevende dienst-JWT's (contract §4)."""

from __future__ import annotations

import base64
import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ISSUER = "hub"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def raw_public(key: Ed25519PublicKey) -> bytes:
    return key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)


def key_id(key: Ed25519PublicKey) -> str:
    return hashlib.sha256(raw_public(key)).hexdigest()[:16]


def public_jwk(key: Ed25519PublicKey, *, use: str = "sig") -> dict[str, str]:
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": _b64url(raw_public(key)),
        "kid": key_id(key),
        "use": use,
        "alg": "EdDSA",
    }


def public_pem(key: Ed25519PublicKey) -> str:
    return key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


def load_private(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError(f"{path.name} is geen Ed25519-sleutel")
    return key


@dataclass(frozen=True)
class KeyRing:
    jwt_signing: Ed25519PrivateKey
    policy_signing: Ed25519PrivateKey
    identity: Ed25519PrivateKey

    @classmethod
    def load(cls, secrets_dir: Path) -> KeyRing:
        return cls(
            jwt_signing=load_private(secrets_dir / "jwt-signing.ed25519"),
            policy_signing=load_private(secrets_dir / "policy-signing.ed25519"),
            identity=load_private(secrets_dir / "hub-identity.ed25519"),
        )

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        return {"keys": [public_jwk(self.jwt_signing.public_key())]}

    def policy_public_jwk(self) -> dict[str, str]:
        return public_jwk(self.policy_signing.public_key())

    def issue_user_jwt(
        self, *, subject: str, audience: str, roles: list[str], ttl_seconds: int, now: datetime | None = None
    ) -> tuple[str, datetime]:
        if ttl_seconds > 120:
            raise ValueError("dienst-JWT mag maximaal 120 s geldig zijn (contract §4)")
        issued = (now or datetime.now(UTC)).replace(microsecond=0)
        expires = issued + timedelta(seconds=ttl_seconds)
        claims: dict[str, Any] = {
            "iss": ISSUER,
            "aud": audience,
            "sub": subject,
            "roles": roles,
            "iat": int(issued.timestamp()),
            "nbf": int(issued.timestamp()),
            "exp": int(expires.timestamp()),
            "jti": str(uuid.uuid4()),
        }
        token = jwt.encode(
            claims, self.jwt_signing, algorithm="EdDSA", headers={"kid": key_id(self.jwt_signing.public_key())}
        )
        return token, expires

    def verify_user_jwt(self, token: str, *, audience: str) -> dict[str, Any]:
        """Hulpfunctie voor tests en voor diensten-SDK's: verifieer met de eigen publieke sleutel."""
        return jwt.decode(
            token,
            self.jwt_signing.public_key(),
            algorithms=["EdDSA"],
            audience=audience,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
