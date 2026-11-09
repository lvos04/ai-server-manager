"""Executor: verzoekgrootte (§5), jti-replaycache (§4.6), Idempotency-Key en rollen (§4.2) op de muterende route
``POST /connector/v1/hub-link/unlink``. Negatieve scenario's: chunked > 1 MiB vóór aanmelding, hergebruikte jti (ook
na een herstart), rol 'kind' wint, onbruikbare replaycache → 503 (fail-closed), JWT uit de toekomst."""

from __future__ import annotations

import base64
import json
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from executor.app import create_app
from executor.config import Settings
from executor.firststart import ensure_secrets
from executor.hublink import AuthFailed, HubLinkStore, verify_hub_jwt
from executor.replay import ReplayCache, ReplayUnavailable

AUD = "ai-server-manager-executor"
UNLINK = "/connector/v1/hub-link/unlink"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class Hub:
    """Gepinde Hub-sleutel in een gekoppelde ``hub-link.json`` en ondertekende JWT's daarmee."""

    def __init__(self, data_dir: Path) -> None:
        self.key = Ed25519PrivateKey.generate()
        self.x = _b64(self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
        self.sid = str(uuid.uuid4())
        settings = Settings(data_dir=data_dir)
        ensure_secrets(settings.secrets_dir)
        with HubLinkStore(settings.secrets_dir).update() as link:
            link.update(
                state="gekoppeld",
                app_id=AUD,
                hub_url="http://192.0.2.5:30400",
                service_id=self.sid,
                via="koppelcode",
                first_linked_at="2026-11-09T12:00:00Z",
                linked_at="2026-11-09T12:00:00Z",
                confirmed_at="2026-11-09T12:00:01Z",
                service_token="svc_" + "a" * 43,
                service_token_last4="aaaa",
                pins={
                    "jwt": [{"kid": "k1", "jwk": {"kty": "OKP", "crv": "Ed25519", "x": self.x}}],
                    "policy": [],
                    "keyset_fingerprint": "MEGG-8GFG-2E4Y-K2RQ",
                    "rotation_sequence": 0,
                },
            )
        self.settings = settings

    def jwt(self, **change: Any) -> str:
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
        head = _b64(json.dumps({"alg": "EdDSA", "typ": "JWT", "kid": "k1"}).encode())
        body = _b64(json.dumps(claims).encode())
        return f"{head}.{body}.{_b64(self.key.sign(f'{head}.{body}'.encode()))}"

    def user_jwt(self, roles: list[str]) -> str:
        return self.jwt(sub=str(uuid.uuid4()), token_use="user", roles=roles, service_id=None)


@pytest.fixture
def hub(tmp_path: Path) -> Hub:
    return Hub(tmp_path / "appdata")


def _client(hub: Hub) -> TestClient:
    return TestClient(create_app(hub.settings), base_url="http://executor.test")


def _auth(token: str, key: str | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}"}
    if key is not None:
        h["Idempotency-Key"] = key
    return h


def _chunks(total: int) -> Any:
    sent = 0
    while sent < total:
        n = min(64 * 1024, total - sent)
        sent += n
        yield b"x" * n


# ------------------------------------------------------------------ verzoekgrootte (§5)
def test_413_voor_routering_en_aanmelding_ook_chunked(hub: Hub) -> None:
    c = _client(hub)
    over = 1024 * 1024 + 1
    for method, path in (("POST", UNLINK), ("POST", "/koppelen"), ("POST", "/api/v1/execute"), ("PUT", "/bestaat")):
        r = c.request(method, path, content=_chunks(over), headers={"content-type": "application/json"})
        assert r.status_code == 413, f"{method} {path}: {r.status_code} {r.text[:120]}"
        assert r.json()["code"] == "payload_too_large" and r.json()["details"] == {"max_bytes": 1048576}
        assert r.json()["trace_id"]
        r = c.request(method, path, content=b"x" * over)  # met Content-Length: direct geweigerd
        assert r.status_code == 413, f"{method} {path} (Content-Length): {r.status_code}"
    # Precies 1 MiB mag door: de route beslist (zonder Hub-JWT → 401 met reden).
    r = c.post(UNLINK, content=_chunks(1024 * 1024))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token"
    assert c.get("/healthz").status_code == 200


# ------------------------------------------------------------------ jti-replay en idempotency (§4.6, §5)
def test_unlink_vraagt_idempotency_key_en_weigert_hergebruikte_jti(hub: Hub) -> None:
    c = _client(hub)
    token, key = hub.jwt(), str(uuid.uuid4())
    r = c.post(UNLINK, headers=_auth(token))
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_required"
    r = c.post(UNLINK, headers=_auth(token, "geen-uuid"))
    assert r.status_code == 400 and r.json()["code"] == "idempotency_key_invalid"
    first = c.post(UNLINK, headers=_auth(token, key))
    assert first.status_code == 501 and first.json()["code"] == "capability_unavailable"
    # Exacte herhaling (zelfde jti, methode, pad en key): het opgeslagen antwoord, geen tweede uitvoering.
    again = c.post(UNLINK, headers=_auth(token, key))
    assert again.status_code == 501 and again.headers["Idempotent-Replay"] == "true"
    assert again.json() == first.json()
    # Zelfde jti voor een andere mutatie (andere key) → 401 token_replayed.
    r = c.post(UNLINK, headers=_auth(token, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "token_replayed"
    # Lezen met dezelfde JWT mag binnen de levensduur vaker.
    for _ in range(3):
        assert c.get("/connector/v1/hub-link", headers=_auth(token)).status_code == 200
    # Persistent: ook na een herstart (nieuwe app op dezelfde /appdata) blijft de jti gebruikt.
    restarted = _client(hub)
    r = restarted.post(UNLINK, headers=_auth(token, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "token_replayed"
    # Een nieuwe JWT (nieuwe jti) is gewoon een nieuwe mutatie.
    assert restarted.post(UNLINK, headers=_auth(hub.jwt(), str(uuid.uuid4()))).status_code == 501
    assert hub.settings.replay_db.stat().st_mode & 0o077 == 0  # 0600


def test_replaycache_onbruikbaar_is_fail_closed(hub: Hub) -> None:
    hub.settings.replay_db.mkdir()  # een map waar een database hoort: SQLite kan niet openen
    c = _client(hub)
    r = c.post(UNLINK, headers=_auth(hub.jwt(), str(uuid.uuid4())))
    assert r.status_code == 503 and r.json()["code"] == "replay_check_unavailable"
    # Lezen hangt niet van de replaycache af.
    assert c.get("/connector/v1/hub-link", headers=_auth(hub.jwt())).status_code == 200


def test_rollen_kind_wint_en_admin_voor_ontkoppelen(hub: Hub) -> None:
    c = _client(hub)
    assert c.get("/connector/v1/hub-link", headers=_auth(hub.user_jwt(["viewer"]))).status_code == 200
    # 'kind' wint altijd van andere rollen in dezelfde JWT (§4.2); onbekende rollen tellen niet.
    for roles in (["kind", "admin"], ["kind"], ["onbekend"], []):
        r = c.get("/connector/v1/hub-link", headers=_auth(hub.user_jwt(roles)))
        assert r.status_code == 403, roles
    for roles in (["viewer"], ["operator"], ["admin", "kind"]):
        r = c.post(UNLINK, headers=_auth(hub.user_jwt(roles), str(uuid.uuid4())))
        assert r.status_code == 403 and r.json()["code"] == "forbidden", roles
    assert c.post(UNLINK, headers=_auth(hub.user_jwt(["admin"]), str(uuid.uuid4()))).status_code == 501


def test_niet_gekoppeld_of_andere_sleutel_ook_op_de_mutatie(hub: Hub, tmp_path: Path) -> None:
    c = _client(hub)
    # Gewisselde Hub-sleutel: onbekende kid → unknown_key; zelfde kid met een andere sleutel → invalid_token.
    other = Hub(tmp_path / "ander")
    forged = other.jwt(service_id=hub.sid)
    r = c.post(UNLINK, headers=_auth(forged, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "invalid_token"
    head = _b64(json.dumps({"alg": "EdDSA", "typ": "JWT", "kid": "nieuwe-kid"}).encode())
    body = forged.split(".")[1]
    unknown = f"{head}.{body}.{_b64(other.key.sign(f'{head}.{body}'.encode()))}"
    r = c.post(UNLINK, headers=_auth(unknown, str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "unknown_key"
    with HubLinkStore(hub.settings.secrets_dir).update() as link:
        link.update(state="ontkoppeld", service_token=None, pins=None)
    r = c.post(UNLINK, headers=_auth(hub.jwt(), str(uuid.uuid4())))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "not_linked"


def test_jwt_uit_de_toekomst_of_met_bool_tijden_is_ongeldig(hub: Hub) -> None:
    link = HubLinkStore(hub.settings.secrets_dir).read()
    t = int(time.time())
    for change in ({"iat": t + 300, "nbf": t, "exp": t + 360}, {"iat": True}, {"exp": t - 10, "iat": t}):
        with pytest.raises(AuthFailed) as exc:
            verify_hub_jwt(hub.jwt(**change), link, audience=AUD)
        assert exc.value.reason == "invalid_token", change


def test_replaycache_ruimt_op_na_exp_plus_speling(tmp_path: Path) -> None:
    cache = ReplayCache(tmp_path / "r.sqlite3")
    kw: dict[str, Any] = {
        "iss": "hub",
        "jti": "j1",
        "exp": 1000,
        "method": "POST",
        "path": "/x",
        "idempotency_key": "k",
    }
    assert cache.claim(**kw, now=900).kind == "new"
    assert cache.claim(**kw, now=901).kind == "in_progress"  # nog geen opgeslagen antwoord
    cache.store_result(iss="hub", jti="j1", status=501, body={"code": "capability_unavailable"})
    repeat = cache.claim(**kw, now=902)
    assert repeat.kind == "repeat" and repeat.status == 501 and repeat.body == {"code": "capability_unavailable"}
    assert cache.claim(**{**kw, "path": "/y"}, now=903).kind == "replayed"
    # Na exp + 30 s is de rij weg (de JWT zelf is dan verlopen: token_expired vóór deze controle).
    assert cache.claim(**{**kw, "path": "/y"}, now=1031).kind == "new"
    with pytest.raises(ReplayUnavailable):
        ReplayCache(tmp_path / "bestaat-niet" / "r.sqlite3").claim(**kw)
