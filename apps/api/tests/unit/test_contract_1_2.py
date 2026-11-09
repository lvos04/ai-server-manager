"""Unit-tests voor contract 1.2: JWT-soorten (§4.2/§4.3), noodlogin (§4.1), register (H14) en Hub → dienst (§5)."""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import jwt
import pytest

from hub import breakglass
from hub.firststart import ensure_secrets
from hub.keys import TOKEN_USE_HUB_SERVICE, TOKEN_USE_USER, KeyRing
from hub.registry import app_name_candidates, expected_repository
from hub.security import is_valid_pairing_code, normalize_pairing_code
from hub.servicecalls import ServiceCallError, call

RFC6238_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # ASCII "12345678901234567890" (RFC 6238 bijlage B, SHA-1)


@pytest.fixture
def keyring(tmp_path: Path) -> KeyRing:
    ensure_secrets(tmp_path / "secrets", new_setup_code=False)
    return KeyRing.load(tmp_path / "secrets")


# ------------------------------------------------------------------ JWT-soorten
def test_gebruikers_jwt_heeft_token_use_user_en_jti(keyring: KeyRing) -> None:
    token, _ = keyring.issue_user_jwt(
        subject=str(uuid.uuid4()), audience="jelly-leon", roles=["viewer"], ttl_seconds=60
    )
    claims = keyring.verify_user_jwt(token, audience="jelly-leon")
    assert claims["token_use"] == TOKEN_USE_USER == "user"
    assert uuid.UUID(claims["jti"]).version == 4 and claims["exp"] - claims["iat"] == 60 and claims["nbf"]
    with pytest.raises(ValueError, match="120"):
        keyring.issue_user_jwt(subject="x", audience="jelly-leon", roles=["viewer"], ttl_seconds=121)
    with pytest.raises(ValueError, match="service"):
        keyring.issue_user_jwt(subject="x", audience="jelly-leon", roles=["service"], ttl_seconds=60)


def test_dienst_jwt_van_de_hub(keyring: KeyRing) -> None:
    sid = str(uuid.uuid4())
    token, expires = keyring.issue_hub_service_jwt(audience="home-control-hub", service_id=sid)
    header = jwt.get_unverified_header(token)
    assert header["alg"] == "EdDSA" and header["kid"] == keyring.jwks()["keys"][0]["kid"]
    claims = keyring.verify_user_jwt(token, audience="home-control-hub")
    assert claims["sub"] == "hub" and claims["token_use"] == TOKEN_USE_HUB_SERVICE == "hub_service"
    assert claims["roles"] == ["service"] and claims["service_id"] == sid and claims["iss"] == "hub"
    assert 0 < claims["exp"] - claims["iat"] <= 120 and expires > datetime.now(UTC)
    other, _ = keyring.issue_hub_service_jwt(audience="home-control-hub", service_id=sid)
    assert jwt.decode(other, options={"verify_signature": False})["jti"] != claims["jti"]  # per aanroep nieuw
    with pytest.raises(ValueError):
        keyring.issue_hub_service_jwt(audience="home-control-hub", service_id="geen-uuid")
    with pytest.raises(ValueError):
        keyring.issue_hub_service_jwt(audience="home-control-hub", service_id=sid, ttl_seconds=121)


# ------------------------------------------------------------------ koppelcode
@pytest.mark.parametrize(
    ("code", "ok"),
    [
        ("ABCD-EFGH-JKMN", True),
        ("abcd efgh jkmn", True),
        ("0123-4567-89AB", True),
        ("OIL0-OIL0-OIL0", True),  # O→0, I/L→1
        ("ABCD-EFGH-JKM", False),  # 11 tekens
        ("ABCD-EFGH-JKMNP", False),  # 13 tekens
        ("UUUU-UUUU-UUUU", False),  # U zit niet in het Crockford-alfabet
        ("ÄBCD-EFGH-JKMN", False),
    ],
)
def test_koppelcode_normalisatie(code: str, ok: bool) -> None:
    assert is_valid_pairing_code(normalize_pairing_code(code)) is ok


# ------------------------------------------------------------------ TOTP (RFC 6238 bijlage B)
@pytest.mark.parametrize(
    ("t", "expected"),
    [(59, "94287082"), (1111111109, "07081804"), (1111111111, "14050471"), (1234567890, "89005924"),
     (2000000000, "69279037"), (20000000000, "65353130")],
)  # fmt: skip
def test_totp_rfc6238_testvectoren(t: int, expected: str) -> None:
    assert breakglass.totp_at(RFC6238_SECRET, t // 30, digits=8) == expected


def test_totp_verificatie_venster_en_eenmalig() -> None:
    now = datetime.fromtimestamp(1234567890, UTC)
    step = breakglass.time_step(now)
    code = breakglass.totp_at(RFC6238_SECRET, step)
    assert breakglass.verify_totp(RFC6238_SECRET, code, now, None) == step
    assert breakglass.verify_totp(RFC6238_SECRET, code, now, step) is None  # al gebruikt
    assert breakglass.verify_totp(RFC6238_SECRET, breakglass.totp_at(RFC6238_SECRET, step - 1), now, None) == step - 1
    assert breakglass.verify_totp(RFC6238_SECRET, breakglass.totp_at(RFC6238_SECRET, step - 2), now, None) is None
    assert breakglass.verify_totp(RFC6238_SECRET, "12345", now, None) is None
    assert breakglass.verify_totp(RFC6238_SECRET, "abcdef", now, None) is None
    secret = breakglass.generate_secret()
    assert len(secret) == 32 and breakglass.otpauth_uri(secret, "nood").startswith("otpauth://totp/")


# ------------------------------------------------------------------ bron-IP
@pytest.mark.parametrize(
    ("ip", "private"),
    [
        ("10.1.2.3", True),
        ("172.16.0.5", True),
        ("172.31.255.1", True),
        ("192.168.1.20", True),
        ("100.64.0.1", True),
        ("fd12:3456::1", True),
        ("::ffff:192.168.1.20", True),
        ("172.32.0.1", False),
        ("8.8.8.8", False),
        ("192.0.2.10", False),
        ("127.0.0.1", False),
        ("169.254.1.1", False),
        ("fe80::1", False),
        ("2001:db8::1", False),
        ("testclient", False),
        ("", False),
    ],
)
def test_prive_bereiken(ip: str, private: bool) -> None:
    assert breakglass.is_private_source(ip) is private


def test_docker_gateway_heuristiek() -> None:
    assert breakglass.looks_like_docker_gateway("172.17.0.1")
    assert breakglass.looks_like_docker_gateway("172.18.0.1")
    assert not breakglass.looks_like_docker_gateway("172.17.0.5")
    assert not breakglass.looks_like_docker_gateway("192.168.1.1")


# ------------------------------------------------------------------ register (H14)
def test_appnaam_kandidaten_op_image_repository() -> None:
    apps = [
        {"naam": "mijn-hch", "images": [{"repository": "ghcr.io/lvos04/home-control-hub"}]},
        {"naam": "home-control-hub", "images": [{"repository": "docker.io/library/nginx"}]},
        {"naam": "hch2", "images": [{"repository": "ghcr.io/lvos04/home-control-hub"}]},
        {"naam": "kapot", "images": "geen lijst"},
    ]
    assert expected_repository("home-control-hub") == "ghcr.io/lvos04/home-control-hub"
    # Op image, niet op naam: de app die toevallig zo heet maar nginx draait telt niet.
    assert app_name_candidates(apps, "home-control-hub") == ["hch2", "mijn-hch"]
    assert app_name_candidates(None, "home-control-hub") == []


# ------------------------------------------------------------------ Hub → dienst (http.client)
class _Handler(BaseHTTPRequestHandler):
    calls: list[dict[str, Any]] = []  # noqa: RUF012 — testserver

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        _Handler.calls.append({"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(length)})
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://192.0.2.1/elders")
            self.end_headers()
            return
        payload = json.dumps({"code": "unauthorized", "details": {"reason": "not_linked"}}).encode()
        self.send_response(401 if self.path == "/unlink" else 200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args: Any) -> None:
        return


@pytest.fixture
def server() -> Iterator[str]:
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    _Handler.calls.clear()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def test_dienstaanroep_volgt_geen_redirect_en_leest_reden(server: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://192.0.2.99:9")  # proxy-omgeving wordt genegeerd
    res = call(server, "POST", "/unlink", bearer="jwt-x", idempotency_key="k-1", body={})
    assert res.status == 401 and res.code == "unauthorized" and res.reason == "not_linked"
    sent = _Handler.calls[-1]["headers"]
    assert sent["Authorization"] == "Bearer jwt-x" and sent["Idempotency-Key"] == "k-1"
    with pytest.raises(ServiceCallError) as exc:
        call(server, "POST", "/redirect", bearer="jwt-x")
    assert exc.value.reason == "redirect_niet_gevolgd"
    assert all(c["path"] != "/elders" for c in _Handler.calls)
    with pytest.raises(ServiceCallError) as exc:
        call("http://127.0.0.1:9", "POST", "/x", bearer="t", connect_timeout=1)
    assert exc.value.reason in ("niet_bereikbaar", "tijdslimiet")
    for bad in ("https://127.0.0.1:1", "http://user:pw@127.0.0.1:1", "ftp://x", "http://x/?a=1"):
        with pytest.raises(ServiceCallError):
            call(bad, "POST", "/x", bearer="t")
