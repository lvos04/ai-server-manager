"""Sleutelbeheer: Ed25519-sleutels uit ``/appdata/secrets``, JWKS en kortlevende dienst-JWT's (contract §4)."""

from __future__ import annotations

import base64
import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping
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


CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
KEYSET_FINGERPRINT_PREFIX = "jl-hub-keyset-v1"


def jwk_thumbprint(jwk: Mapping[str, Any]) -> str:
    """RFC 7638-thumbprint (SHA-256, base64url) van een publieke Ed25519-JWK (contract 1.2 §4.5)."""
    x = jwk.get("x")
    if jwk.get("kty") != "OKP" or jwk.get("crv") != "Ed25519" or not isinstance(x, str) or "d" in jwk:
        raise ValueError("alleen een publieke Ed25519-JWK (kty=OKP, crv=Ed25519, zonder 'd')")
    try:
        raw = base64.urlsafe_b64decode(x + "=" * (-len(x) % 4))
    except ValueError as exc:
        raise ValueError("x is geen base64url") from exc
    if len(raw) != 32 or _b64url(raw) != x:
        raise ValueError("x moet 32 bytes in canonieke base64url zijn")
    canonical = json.dumps({"crv": "Ed25519", "kty": "OKP", "x": x}, separators=(",", ":"), sort_keys=True)
    return _b64url(hashlib.sha256(canonical.encode("utf-8")).digest())


def _crockford(data: bytes) -> str:
    bits = "".join(f"{byte:08b}" for byte in data)
    bits += "0" * (-len(bits) % 5)
    return "".join(CROCKFORD_ALPHABET[int(bits[i : i + 5], 2)] for i in range(0, len(bits), 5))


def keyset_fingerprint(jwt_keys: Iterable[Mapping[str, Any]], policy_key: Mapping[str, Any]) -> str:
    """Sleutelset-vingerafdruk voor mensen (contract 1.2 §4.5): 80 bit, Crockford-base32, ``XXXX-XXXX-XXXX-XXXX``."""
    thumbprints = sorted(jwk_thumbprint(k) for k in jwt_keys)
    if not thumbprints:
        raise ValueError("minstens één JWT-sleutel nodig")
    text = f"{KEYSET_FINGERPRINT_PREFIX}\njwt:{','.join(thumbprints)}\npolicy:{jwk_thumbprint(policy_key)}"
    code = _crockford(hashlib.sha256(text.encode("utf-8")).digest()[:10])
    return "-".join(code[i : i + 4] for i in range(0, 16, 4))


def normalize_fingerprint(value: str) -> str:
    """Invoer van een mens vergelijkbaar maken: hoofdletters, zonder streepjes/spaties, ``O→0`` en ``I/L→1``."""
    cleaned = "".join(ch for ch in value.upper() if ch.isalnum())
    return cleaned.replace("O", "0").replace("I", "1").replace("L", "1")


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

    def keyset_fingerprint(self) -> str:
        """Vingerafdruk over de JWKS + policy-sleutel die een dienst bij enrollment pint (contract 1.2 §4.5)."""
        return keyset_fingerprint(self.jwks()["keys"], self.policy_public_jwk())

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
