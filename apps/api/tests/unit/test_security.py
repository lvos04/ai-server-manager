"""Wachtwoorden, JWT/JWKS, vault en redactie."""

from __future__ import annotations

import base64
from pathlib import Path

import jwt
import pytest
from cryptography.exceptions import InvalidTag

from hub.firststart import ensure_secrets
from hub.keys import KeyRing
from hub.redact import redact, redact_text
from hub.security import ROLE_RANK, Role, hash_password, needs_rehash, normalize_pairing_code, verify_password
from hub.vault import Vault, VaultError, last4, make_ref


def test_argon2id() -> None:
    h = hash_password("een-lang-wachtwoord")
    assert h.startswith("$argon2id$")
    assert verify_password(h, "een-lang-wachtwoord")
    assert not verify_password(h, "fout")
    assert not verify_password(None, "een-lang-wachtwoord")
    assert not needs_rehash(h)


def test_rollen_volgorde() -> None:
    assert ROLE_RANK[Role.kind] < ROLE_RANK[Role.viewer] < ROLE_RANK[Role.operator] < ROLE_RANK[Role.admin]


def test_koppelcode_normalisatie() -> None:
    assert normalize_pairing_code("abcd-efgh-ijkl") == "ABCDEFGH1JK1"
    assert normalize_pairing_code("0O1I-L") == "00111"


@pytest.fixture
def keyring(tmp_path: Path) -> KeyRing:
    ensure_secrets(tmp_path / "s")
    return KeyRing.load(tmp_path / "s")


def test_jwt_kortlevend_en_verifieerbaar_via_jwks(keyring: KeyRing) -> None:
    token, _ = keyring.issue_user_jwt(subject="u1", audience="jelly-leon", roles=["kind"], ttl_seconds=120)
    claims = keyring.verify_user_jwt(token, audience="jelly-leon")
    assert claims["iss"] == "hub" and claims["roles"] == ["kind"] and claims["exp"] - claims["iat"] == 120
    jwk = keyring.jwks()["keys"][0]
    assert jwk["kty"] == "OKP" and jwk["crv"] == "Ed25519" and "d" not in jwk
    pub = jwt.PyJWK(jwk).key
    assert jwt.decode(token, pub, algorithms=["EdDSA"], audience="jelly-leon")["sub"] == "u1"
    with pytest.raises(jwt.InvalidAudienceError):
        keyring.verify_user_jwt(token, audience="iets-anders")
    with pytest.raises(ValueError):
        keyring.issue_user_jwt(subject="u1", audience="x", roles=[], ttl_seconds=121)


def test_policy_sleutel_verschilt_van_jwt_sleutel(keyring: KeyRing) -> None:
    assert keyring.policy_public_jwk()["x"] != keyring.jwks()["keys"][0]["x"]


def test_vault_aes_gcm_gebonden_aan_referentie() -> None:
    v = Vault(b"\x01" * 32)
    ref = make_ref("truenas", "readonly-api-key")
    nonce, ct = v.encrypt(ref, "geheime-waarde-1234")
    assert b"geheime" not in ct
    assert v.decrypt(ref, nonce, ct) == "geheime-waarde-1234"
    with pytest.raises(InvalidTag):
        v.decrypt(make_ref("andere", "naam"), nonce, ct)
    with pytest.raises(VaultError):
        make_ref("Hoofdletters", "x")
    with pytest.raises(VaultError):
        Vault(b"kort")
    assert last4("abcdefgh1234") == "1234" and last4("kort") == "****"
    assert base64.b64decode(base64.b64encode(b"x")) == b"x"


def test_redactie() -> None:
    data = {
        "api_key": "abc",
        "nested": {"password": "p", "ok": "zichtbaar"},
        "lijst": [{"token": "t"}],
        "vlag_token": True,
    }
    out = redact(data)
    assert out["api_key"] == "***" and out["nested"]["password"] == "***" and out["nested"]["ok"] == "zichtbaar"
    assert out["lijst"][0]["token"] == "***" and out["vlag_token"] is True
    assert redact_text("Authorization: Bearer abcdefghijklmnop") == "Authorization: Bearer ***"
    assert redact_text("https://user:pw@host/x") == "https://user:***@host/x"
