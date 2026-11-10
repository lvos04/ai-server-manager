"""Gedeelde hulp voor de executortests: een gekoppelde ``hub-link.json`` met een gepinde Hub-sleutel en JWT's die
daarmee zijn ondertekend (contract 1.3 §4.2–§4.7)."""

from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from executor.app import create_app
from executor.config import Settings
from executor.firststart import ensure_secrets
from executor.hublink import HubLinkStore
from fastapi.testclient import TestClient

AUD = "ai-server-manager-executor"
UNLINK = "/connector/v1/hub-link/unlink"
# Toegestane Host voor formulier-POST's (§3.7 punt 4): een naam onder .local.
BASE = "http://executor.local"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def linked_fields(**change: Any) -> dict[str, Any]:
    """Minimaal leesbare velden van een gekoppelde toestand (§3.5)."""
    fields: dict[str, Any] = {
        "state": "gekoppeld",
        "app_id": AUD,
        "hub_url": "http://192.0.2.5:30400",
        "service_id": str(uuid.uuid4()),
        "via": "koppelcode",
        "first_linked_at": "2026-11-09T12:00:00Z",
        "linked_at": "2026-11-09T12:00:00Z",
        "confirmed_at": "2026-11-09T12:00:01Z",
        "service_token": "svc_" + "a" * 43,
        "service_token_last4": "aaaa",
        "pins": {
            "jwt": [],
            "policy": [],
            "keyset_fingerprint": "MEGG-8GFG-2E4Y-K2RQ",
            "rotation_sequence": 0,
        },
    }
    fields.update(change)
    return fields


class Hub:
    """Gepinde Hub-sleutel in een gekoppelde ``hub-link.json`` en ondertekende JWT's daarmee."""

    def __init__(self, data_dir: Path) -> None:
        self.key = Ed25519PrivateKey.generate()
        self.x = b64(self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
        self.sid = str(uuid.uuid4())
        settings = Settings(data_dir=data_dir)
        ensure_secrets(settings.secrets_dir)
        with HubLinkStore(settings.secrets_dir).update() as link:
            link.update(
                linked_fields(
                    service_id=self.sid,
                    pins={
                        "jwt": [
                            {
                                "kid": "k1",
                                "jwk": {"kty": "OKP", "crv": "Ed25519", "x": self.x},
                            }
                        ],
                        "policy": [],
                        "keyset_fingerprint": "MEGG-8GFG-2E4Y-K2RQ",
                        "rotation_sequence": 0,
                    },
                )
            )
        self.settings = settings

    def jwt(self, *, header: dict[str, Any] | None = None, **change: Any) -> str:
        t = int(time.time())
        claims: dict[str, Any] = {
            "iss": "hub",
            "aud": AUD,
            "sub": "hub",
            "token_use": "hub_service",
            "roles": ["service"],
            "service_id": self.sid,
            "iat": t,
            "nbf": t,
            "exp": t + 60,
            "jti": str(uuid.uuid4()),
        }
        claims.update(change)
        claims = {k: v for k, v in claims.items() if v is not None}
        head = b64(json.dumps(header or {"alg": "EdDSA", "typ": "JWT", "kid": "k1"}).encode())
        body = b64(json.dumps(claims).encode())
        return f"{head}.{body}.{b64(self.key.sign(f'{head}.{body}'.encode()))}"

    def user_jwt(self, roles: list[str]) -> str:
        return self.jwt(sub=str(uuid.uuid4()), token_use="user", roles=roles, service_id=None)


def client(hub: Hub) -> TestClient:
    return TestClient(create_app(hub.settings), base_url=BASE)


def auth(token: str, key: str | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}"}
    if key is not None:
        h["Idempotency-Key"] = key
    return h
