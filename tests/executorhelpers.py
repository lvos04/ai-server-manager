"""Gedeelde hulp voor de executortests: een gekoppelde ``hub-link.json`` met een gepinde Hub-sleutel en JWT's die
daarmee zijn ondertekend (contract 1.3 §4.2–§4.7), een gepinde policy-sleutel voor ondertekende ``ExecutionRequest``s
(§8) en de fake TrueNAS met een schrijfsleutel (§3.9). Alleen testwaarden; nooit echte NAS-gegevens."""

from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any

from asm_policy import load_policy
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from executor.app import create_app
from executor.config import Settings
from executor.firststart import ensure_secrets
from executor.hublink import HubLinkStore
from executor.naslink import NasLinkStore
from executor.truenas import fetch_fingerprint
from fakes.fake_truenas import FakeTrueNAS, KeyProfile
from fastapi.testclient import TestClient
from policyhelpers import POLICY_DIR, approval_for, execution_request

AUD = "ai-server-manager-executor"
POLICY = load_policy(POLICY_DIR)
READ_KEY = "readonly-test-key-0123456789"
WRITE_KEY = "schrijf-test-key-0123456789abcd"
NAS_HOST = "127.0.0.1"
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

    def __init__(self, data_dir: Path, **instellingen: Any) -> None:
        raw = (serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.key = Ed25519PrivateKey.generate()
        self.x = b64(self.key.public_key().public_bytes(*raw))
        # Aparte policy-sleutel (§4.5): alleen daarmee telt de handtekening onder een ExecutionRequest.
        self.policy_key = Ed25519PrivateKey.generate()
        self.policy_x = b64(self.policy_key.public_key().public_bytes(*raw))
        self.sid = str(uuid.uuid4())
        settings = Settings(data_dir=data_dir, **instellingen)
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
                        "policy": [{"kid": "p1", "jwk": {"kty": "OKP", "crv": "Ed25519", "x": self.policy_x}}],
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


# ---------------------------------------------------------------------- TrueNAS (fake) en ondertekende verzoeken
def write_nas(**kwargs: Any) -> FakeTrueNAS:
    """Fake TrueNAS met een alleen-lezen-sleutel en een schrijfsleutel (FULL_ADMIN). Nog niet gestart."""
    keys = {READ_KEY: KeyProfile(), WRITE_KEY: KeyProfile(roles=["FULL_ADMIN"], write=True)}
    return FakeTrueNAS(keys=keys, noise=False, **kwargs)


def nas_hub(data_dir: Path, nas: FakeTrueNAS, **instellingen: Any) -> Hub:
    """Gekoppelde executor die de fake als TrueNAS gebruikt (adres via de instelling, zoals ``EXECUTOR_TRUENAS_HOST``).
    Het beleid komt uit de repo en is daar beschrijfbaar; in het image is het alleen-lezen."""
    basis: dict[str, Any] = {
        "truenas_host": NAS_HOST,
        "truenas_port": nas.port,
        "truenas_timeout_seconds": 5,
        "readback_wait_seconds": 0.6,
        "readback_poll_seconds": 0.05,
        "allow_writable_policy": True,
    }
    basis.update(instellingen)
    return Hub(data_dir, **basis)


def set_write_key(hub: Hub, nas: FakeTrueNAS, key: str = WRITE_KEY, roles: list[str] | None = None) -> str:
    """De schrijfsleutel rechtstreeks vastleggen (zonder het formulier): adres, vingerafdruk en versleutelde sleutel."""
    fingerprint = fetch_fingerprint(NAS_HOST, nas.port)
    NasLinkStore(hub.settings.secrets_dir).save_key(NAS_HOST, nas.port, fingerprint, key, roles or ["FULL_ADMIN"])
    return fingerprint


def signed(
    hub: Hub, prop: dict[str, Any], *, risk_class: str, approval: dict[str, Any] | None = None, **change: Any
) -> dict[str, Any]:
    return execution_request(
        hub.policy_key, prop, policy_hash=POLICY.hash, risk_class=risk_class, approval=approval, **change
    )


def approved(hub: Hub, prop: dict[str, Any], *, risk_class: str = "R2", **change: Any) -> dict[str, Any]:
    """Ondertekend verzoek met een passende goedkeuring; ``change`` wijzigt velden van de goedkeuring."""
    basis: dict[str, Any] = {"backup_checkpoint_id": str(uuid.uuid4())}
    basis.update(change)
    approval = approval_for(prop, policy_hash=POLICY.hash, risk_class=risk_class, **basis)
    return signed(hub, prop, risk_class=risk_class, approval=approval)


def execute(c: TestClient, hub: Hub, request: Any, key: str | None = None) -> Any:
    return c.post("/api/v1/execute", json=request, headers=auth(hub.jwt(), key or str(uuid.uuid4())))
