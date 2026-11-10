"""OIDC (B01-006): groep→rol, terugkeerpad, issuer-regels en PKCE — zuivere functies."""

from __future__ import annotations

import base64
import hashlib

import pytest

from hub.oidc import client
from hub.oidc.service import map_role, safe_return
from hub.security import Role

M = [
    {"groep": "admins", "rol": "admin"},
    {"groep": "beheer", "rol": "operator"},
    {"groep": "kijkers", "rol": "viewer"},
    {"groep": "kinderen", "rol": "kind"},
    {"groep": "fout", "rol": "superuser"},
]


def test_groep_naar_rol() -> None:
    assert map_role(["kijkers", "beheer"], M) == Role.operator
    assert map_role(["admins", "kinderen"], M) == Role.kind  # kind wint altijd (contract §4.2)
    assert map_role(["onbekend"], M) is None  # nooit een standaardrol
    assert map_role(["fout"], M) is None  # onbekende rol telt niet
    assert map_role([], []) is None


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("/apps", "/apps"),
        ("/apps/3?tab=logs#a", "/apps/3?tab=logs#a"),
        ("//evil.lan/x", "/"),
        ("https://evil.lan", "/"),
        ("apps", "/"),
        ("/a\\b", "/"),
        (None, "/"),
        # Browsers verwijderen tab/CR/LF uit een URL: "/<tab>/evil.lan" wordt "//evil.lan" (ander domein).
        ("/\t/evil.lan", "/"),
        ("/\n/evil.lan", "/"),
        ("/\r/evil.lan", "/"),
        ("/ /evil.lan", "/"),
        ("/\x00", "/"),
        ("/caf\u00e9", "/"),
        ("/" + "a" * 300, "/"),
    ],
)
def test_terugkeerpad_alleen_eigen_pad(raw: str | None, want: str) -> None:
    assert safe_return(raw) == want


def test_issuer_regels() -> None:
    assert client.validate_issuer("https://auth.thuis.lan/application/o/hub/", allow_loopback=False)
    with pytest.raises(client.OidcError) as e:
        client.validate_issuer("http://auth.thuis.lan/application/o/hub/", allow_loopback=False)
    assert e.value.reden == "issuer_niet_https"
    with pytest.raises(client.OidcError):
        client.validate_issuer("http://127.0.0.1:9000/x/", allow_loopback=False)
    assert client.validate_issuer("http://127.0.0.1:9000/x/", allow_loopback=True)
    with pytest.raises(client.OidcError) as e:
        client.validate_issuer("https://user:pw@auth.thuis.lan/", allow_loopback=False)
    assert e.value.reden == "issuer_ongeldig"


def test_pkce_s256() -> None:
    verifier, challenge = client.new_pkce()
    assert 43 <= len(verifier) <= 128
    want = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == want and client.new_pkce()[0] != verifier
