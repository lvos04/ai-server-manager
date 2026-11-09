"""Koppeling executor ↔ Hub (contract 1.2): testvectoren §4.5, exact enroll-verzoek §3.3, antwoordcontroles,
opslag in hub-link.json (§3.5), herstart (§3.6) en de controlevolgorde/redenen van §4.7."""

from __future__ import annotations

import base64
import json
import stat
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from executor.hublink import (
    AuthFailed,
    EnrollFailed,
    HubLinkStore,
    check_enroll_response,
    enroll_request,
    jwk_thumbprint,
    keyset_fingerprint,
    public_status,
    resume_after_restart,
    valid_fingerprint,
    valid_pairing_code,
    validate_hub_url,
    verify_hub_jwt,
)

JWT_X = "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo"  # RFC 8037 A.1
POLICY_X = "A6EHv_POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg"
JWT2_X = "Kay64UG8yvCyLhqU000LxzYeUm0L_hLIl5S8kyKWbdc"


def _okp(x: str) -> dict[str, str]:
    return {"kty": "OKP", "crv": "Ed25519", "x": x}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def test_testvectoren_contract_4_5() -> None:
    assert jwk_thumbprint(_okp(JWT_X)) == "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k"
    assert jwk_thumbprint(_okp(POLICY_X)) == "1IG2tMH7J2wbJZnOf8LJzQitKf7LMvoAElsuDMVM54Y"
    assert jwk_thumbprint(_okp(JWT2_X)) == "AkXIZFzonb59ZmGwyKgi3H3BwMi6amevqdKQiLZhdtc"
    assert keyset_fingerprint([_okp(JWT_X)], _okp(POLICY_X)) == "MEGG-8GFG-2E4Y-K2RQ"
    assert keyset_fingerprint([_okp(JWT_X), _okp(JWT2_X)], _okp(POLICY_X)) == "CYRC-JS8C-14AN-JR17"
    assert keyset_fingerprint([_okp(JWT2_X), _okp(JWT_X)], _okp(POLICY_X)) == "CYRC-JS8C-14AN-JR17"
    assert valid_fingerprint("megg 8gfg 2e4y k2rq") and not valid_fingerprint("MEGG-8GFG-2E4Y")
    assert valid_pairing_code("abcd-efgh-jkmn") and not valid_pairing_code("UUUU-UUUU-UUUU")


def test_enroll_verzoek_heeft_exact_de_velden_van_3_3() -> None:
    body = enroll_request("ai-server-manager-executor", "ABCD-EFGH-JKMN", "0.1.0", {**_okp(JWT_X), "use": "sig"})
    assert set(body) == {"app_id", "pairing_code", "version", "base_url", "public_key_jwk"}
    assert body["base_url"] is None
    # Geen use/alg; kid = RFC 7638-thumbprint
    assert body["public_key_jwk"] == {**_okp(JWT_X), "kid": "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k"}


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("http://192.0.2.5:30400", True),
        ("https://hub.thuis:443", True),
        ("http://[fd00::5]:30400", True),
        ("http://192.0.2.5:30400/", True),
        ("http://192.0.2.5:30400/api", False),
        ("http://192.0.2.5:30400?x=1", False),
        ("http://user:pw@192.0.2.5", False),
        ("ftp://192.0.2.5", False),
        ("http://127.0.0.1:30400", False),
        ("http://localhost:30400", False),
        ("http://169.254.1.1", False),
        ("http://[fe80::1]", False),
        ("http://0.0.0.0", False),
        ("http://[::]", False),
        ("http://192.0.2.5:99999", False),
    ],
)
def test_hub_adres_regels(url: str, ok: bool) -> None:
    if ok:
        assert validate_hub_url(url).startswith(("http://", "https://"))
    else:
        with pytest.raises(ValueError):
            validate_hub_url(url)
    assert validate_hub_url("http://127.0.0.1:1", allow_loopback=True) == "http://127.0.0.1:1"


def _jwk(x: str) -> dict[str, str]:
    return {**_okp(x), "kid": x[:16], "use": "sig", "alg": "EdDSA"}


def _response(**change: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": "1.2",
        "service_id": str(uuid.uuid4()),
        "app_id": "ai-server-manager-executor",
        "service_token": "svc_" + "a" * 43,
        "token_type": "Bearer",
        "hub_issuer": "hub",
        "jwks": {"keys": [_jwk(JWT_X)]},
        "policy_public_key": _jwk(POLICY_X),
        "keyset_fingerprint": "MEGG-8GFG-2E4Y-K2RQ",
        "jwks_url": "/api/v1/auth/jwks",
        "events_inbox_url": "/api/v1/events/inbox",
        "key_rotation_url": "/api/v1/auth/key-rotations",
        "enrollment_replayed": False,
        "onbekend_extra_veld": "wordt genegeerd",
    }
    body.update(change)
    return body


def test_antwoordcontroles() -> None:
    pins = check_enroll_response(_response(), "ai-server-manager-executor", "megg-8gfg-2e4y-k2rq")
    assert pins["keyset_fingerprint"] == "MEGG-8GFG-2E4Y-K2RQ" and pins["rotation_sequence"] == 0
    assert pins["jwt"][0]["thumbprint"] == "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k"
    assert pins["policy"][0]["jwk"] == _okp(POLICY_X)
    with pytest.raises(EnrollFailed) as exc:
        check_enroll_response(_response(), "ai-server-manager-executor", "CYRC-JS8C-14AN-JR17")
    assert exc.value.code == "hub_vingerafdruk_onjuist"
    bad_cases: list[dict[str, Any]] = [
        {"schema_version": "2.0"},
        {"app_id": "andere-app"},
        {"service_id": "geen-uuid"},
        {"service_token": "token"},
        {"token_type": "Basic"},
        {"hub_issuer": "nep"},
        {"jwks": {"keys": []}},
        {"jwks": {"keys": [{**_jwk(JWT_X), "d": "geheim"}]}},
        {"jwks": {"keys": [{**_jwk(JWT_X), "use": "enc"}]}},
        {"jwks": {"keys": [_jwk(JWT_X), _jwk(JWT_X)]}},  # kid niet uniek
        {"policy_public_key": {**_jwk(POLICY_X), "alg": "RS256"}},
        {"keyset_fingerprint": "CYRC-JS8C-14AN-JR17"},  # klopt niet met de sleutels zelf
        {"enrollment_replayed": "nee"},
        {"key_rotation_url": None},
    ]
    for change in bad_cases:
        with pytest.raises(EnrollFailed) as exc:
            check_enroll_response(_response(**change), "ai-server-manager-executor", "MEGG-8GFG-2E4Y-K2RQ")
        assert exc.value.code == "hub_antwoord_ongeldig", change
    with pytest.raises(EnrollFailed):
        check_enroll_response([], "ai-server-manager-executor", "MEGG-8GFG-2E4Y-K2RQ")


def test_opslag_atomair_0600_en_witte_lijst(tmp_path: Path) -> None:
    store = HubLinkStore(tmp_path / "secrets")
    assert store.read()["state"] == "nooit_gekoppeld"
    with store.update() as link:
        link.update(
            state="gekoppeld",
            service_token="svc_" + "b" * 43,
            service_token_last4="bbbb",
            pending={
                "kind": "koppelcode",
                "secret_sha256": "f" * 64,
                "hub_url": "http://x",
                "started_at": "",
                "attempts": 1,
            },
            pins={"jwt": [], "policy": [], "keyset_fingerprint": "MEGG-8GFG-2E4Y-K2RQ", "rotation_sequence": 0},
        )
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    assert stat.S_IMODE(store.dir.stat().st_mode) == 0o700
    assert not list(store.dir.glob(".hub-link.json.*"))  # geen tijdelijke bestanden achtergelaten
    pub = public_status(store.read())
    text = json.dumps(pub)
    assert "svc_" not in text and "f" * 64 not in text and pub["koppelen_bezig"] is True
    assert pub["keyset_fingerprint"] == "MEGG-8GFG-2E4Y-K2RQ"
    resume_after_restart(store)  # koppelcode is na een herstart weg
    link = store.read()
    assert link["pending"] is None and link["last_error"]["code"] == "koppelen_onderbroken"
    assert link["state"] == "gekoppeld" and link["service_token"]  # bestaande koppeling ongemoeid


# ------------------------------------------------------------------ inkomende JWT
def _signer() -> tuple[Ed25519PrivateKey, str]:
    key = Ed25519PrivateKey.generate()
    x = _b64(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    return key, x


def _jws(key: Ed25519PrivateKey, kid: str, claims: dict[str, Any], alg: str = "EdDSA") -> str:
    head = _b64(json.dumps({"alg": alg, "typ": "JWT", "kid": kid}).encode())
    body = _b64(json.dumps(claims).encode())
    return f"{head}.{body}.{_b64(key.sign(f'{head}.{body}'.encode()))}"


def _claims(sid: str, **change: Any) -> dict[str, Any]:
    t = int(time.time())
    c: dict[str, Any] = {
        "iss": "hub",
        "aud": "ai-server-manager-executor",
        "sub": "hub",
        "token_use": "hub_service",
        "roles": ["service"],
        "service_id": sid,
        "iat": t,
        "nbf": t,
        "exp": t + 60,
        "jti": str(uuid.uuid4()),
    }
    c.update(change)
    return {k: v for k, v in c.items() if v is not None}


def test_inkomende_hub_jwt_redenen_en_volgorde() -> None:
    key, x = _signer()
    other, _ = _signer()
    sid = str(uuid.uuid4())
    link = {"state": "gekoppeld", "service_id": sid, "pins": {"jwt": [{"kid": "k1", "jwk": _okp(x)}], "policy": []}}
    aud = "ai-server-manager-executor"
    assert verify_hub_jwt(_jws(key, "k1", _claims(sid)), link, audience=aud)["sub"] == "hub"
    user = _claims(sid, sub=str(uuid.uuid4()), token_use="user", roles=["viewer"], service_id=None)
    assert verify_hub_jwt(_jws(key, "k1", user), link, audience=aud)["token_use"] == "user"
    t = int(time.time())
    cases: list[tuple[str, dict[str, Any], str]] = [
        (_jws(key, "k1", _claims(sid)), {"state": "ingetrokken"}, "revoked"),
        (_jws(key, "k1", _claims(sid)), {"state": "ontkoppeld"}, "not_linked"),
        (_jws(key, "k1", _claims(sid)), {"state": "nooit_gekoppeld", "pins": None}, "not_linked"),
        ("svc_" + "c" * 43, {}, "service_token_not_accepted"),
        (_jws(key, "onbekend", _claims(sid)), {}, "unknown_key"),
        (_jws(other, "k1", _claims(sid)), {}, "invalid_token"),  # zelfde kid, andere sleutel: vergelijk op x
        (_jws(key, "k1", _claims(sid), alg="HS256"), {}, "invalid_token"),
        ("geen.jwt", {}, "invalid_token"),
        (_jws(key, "k1", _claims(sid, aud="home-control-hub")), {}, "invalid_token"),
        (_jws(key, "k1", _claims(sid, iss="nep")), {}, "invalid_token"),
        (_jws(key, "k1", _claims(sid, exp=t + 121)), {}, "invalid_token"),  # exp − iat > 120 s
        (_jws(key, "k1", _claims(sid, iat=t - 300, nbf=t - 300, exp=t - 240)), {}, "token_expired"),
        (_jws(key, "k1", _claims(sid, token_use=None)), {}, "token_use_invalid"),
        (_jws(key, "k1", _claims(sid, token_use="iets")), {}, "token_use_invalid"),
        (_jws(key, "k1", _claims(sid, sub="iemand")), {}, "token_use_invalid"),
        (_jws(key, "k1", _claims(sid, roles=["service", "admin"])), {}, "token_use_invalid"),
        (_jws(key, "k1", _claims(str(uuid.uuid4()))), {}, "token_use_invalid"),  # andere service_id
        (_jws(key, "k1", {**user, "roles": ["service"]}), {}, "token_use_invalid"),
        (_jws(key, "k1", _claims(sid, jti=None)), {}, "jti_missing"),
    ]
    for token, change, reason in cases:
        with pytest.raises(AuthFailed) as exc:
            verify_hub_jwt(token, {**link, **change}, audience=aud)
        assert exc.value.reason == reason, (change, reason)
