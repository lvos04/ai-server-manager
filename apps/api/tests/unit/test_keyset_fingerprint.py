"""Contract 1.2 §4.5: RFC 7638-thumbprint en sleutelset-vingerafdruk met de testvectoren uit het contract.

Deze vectoren staan letterlijk in ``docs/platform-v2/PLATFORM_CONTRACTEN.md``; elke dienst toetst er zijn eigen
implementatie aan. Alleen publieke sleutels (RFC 8037 A.1 en twee vaste testsleutels).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from hub.keys import KeyRing, jwk_thumbprint, keyset_fingerprint, normalize_fingerprint, public_jwk

X_RFC8037 = "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo"
X_POLICY = "A6EHv_POEL4dcN0Y50vAmWfk1jCbpQ1fHdyGZBJVMbg"
X_JWT2 = "Kay64UG8yvCyLhqU000LxzYeUm0L_hLIl5S8kyKWbdc"
CONTRACT = Path(__file__).resolve().parents[4] / "docs" / "platform-v2" / "PLATFORM_CONTRACTEN.md"


def jwk(x: str) -> dict[str, str]:
    return {"kty": "OKP", "crv": "Ed25519", "x": x}


def test_thumbprint_gelijk_aan_rfc_8037() -> None:
    assert jwk_thumbprint(jwk(X_RFC8037)) == "kPrK_qmxVWaYVA9wwBF6Iuo3vVzz7TxHCTwXBygrS4k"
    assert jwk_thumbprint(jwk(X_POLICY)) == "1IG2tMH7J2wbJZnOf8LJzQitKf7LMvoAElsuDMVM54Y"
    assert jwk_thumbprint(jwk(X_JWT2)) == "AkXIZFzonb59ZmGwyKgi3H3BwMi6amevqdKQiLZhdtc"
    # Extra velden (kid, use, alg) tellen niet mee in RFC 7638.
    assert jwk_thumbprint({**jwk(X_RFC8037), "kid": "abc", "use": "sig", "alg": "EdDSA"}) == jwk_thumbprint(
        jwk(X_RFC8037)
    )


def test_testvectoren_uit_het_contract() -> None:
    assert keyset_fingerprint([jwk(X_RFC8037)], jwk(X_POLICY)) == "MEGG-8GFG-2E4Y-K2RQ"
    # Volgorde van de JWT-sleutels maakt niet uit (gesorteerd op bytewaarde van de thumbprint).
    assert keyset_fingerprint([jwk(X_RFC8037), jwk(X_JWT2)], jwk(X_POLICY)) == "CYRC-JS8C-14AN-JR17"
    assert keyset_fingerprint([jwk(X_JWT2), jwk(X_RFC8037)], jwk(X_POLICY)) == "CYRC-JS8C-14AN-JR17"


def test_contracttekst_bevat_dezelfde_vectoren() -> None:
    tekst = CONTRACT.read_text(encoding="utf-8")
    for waarde in ("MEGG-8GFG-2E4Y-K2RQ", "CYRC-JS8C-14AN-JR17", X_RFC8037, X_POLICY, X_JWT2):
        assert waarde in tekst


def test_policy_en_jwt_niet_uitwisselbaar() -> None:
    assert keyset_fingerprint([jwk(X_POLICY)], jwk(X_RFC8037)) != keyset_fingerprint([jwk(X_RFC8037)], jwk(X_POLICY))


@pytest.mark.parametrize(
    "fout",
    [
        {"kty": "RSA", "crv": "Ed25519", "x": X_RFC8037},
        {"kty": "OKP", "crv": "X25519", "x": X_RFC8037},
        {"kty": "OKP", "crv": "Ed25519"},
        {"kty": "OKP", "crv": "Ed25519", "x": X_RFC8037, "d": "geheim"},
        {"kty": "OKP", "crv": "Ed25519", "x": "te-kort"},
        {"kty": "OKP", "crv": "Ed25519", "x": X_RFC8037 + "="},
    ],
)
def test_ongeldige_jwk_geweigerd(fout: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        jwk_thumbprint(fout)


def test_lege_jwt_set_geweigerd() -> None:
    with pytest.raises(ValueError):
        keyset_fingerprint([], jwk(X_POLICY))


def test_normalisatie_van_menselijke_invoer() -> None:
    assert normalize_fingerprint("megg 8gfg-2e4y-k2rq") == normalize_fingerprint("MEGG-8GFG-2E4Y-K2RQ")
    assert normalize_fingerprint("O1IL") == "0111"


def test_keyring_vingerafdruk_over_eigen_sleutels() -> None:
    jwt_key, policy_key, identity = (Ed25519PrivateKey.generate() for _ in range(3))
    ring = KeyRing(jwt_signing=jwt_key, policy_signing=policy_key, identity=identity)
    verwacht = keyset_fingerprint([public_jwk(jwt_key.public_key())], public_jwk(policy_key.public_key()))
    assert ring.keyset_fingerprint() == verwacht
    assert len(verwacht) == 19 and verwacht.count("-") == 3
