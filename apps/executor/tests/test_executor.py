"""Executor P0: gezondheid, statuspagina 'nog niet gekoppeld', allowlist weigert alles, eigen geheimen."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from executor.allowlist import ALLOWLIST, check
from executor.app import create_app
from executor.config import Settings
from executor.firststart import IDENTITY, VAULT_KEY, FirstStartError, ensure_secrets


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    s = Settings(data_dir=tmp_path)
    ensure_secrets(s.secrets_dir)
    return TestClient(create_app(s))


def test_gezondheid_en_status(client: TestClient) -> None:
    assert client.get("/healthz").json()["status"] == "ok"
    r = client.get("/readyz")
    assert r.status_code == 200 and r.json()["gekoppeld"] is False
    st = client.get("/api/v1/status").json()
    assert st["gekoppeld"] is False and st["allowlist"] == [] and st["identiteit"]["crv"] == "Ed25519"
    assert "d" not in st["identiteit"]
    page = client.get("/")
    assert page.status_code == 200 and "Niet gekoppeld" in page.text and 'lang="nl"' in page.text
    # Peil-statuspaginasjabloon (C-55): platformnaam, geen groen voor 'niet gekoppeld', koppelformulier met de
    # drie velden van contract 1.2 §3.7.
    assert "Onderdeel van TrueNAS Home Platform" in page.text and 'pil-gezond">Niet gekoppeld' not in page.text
    for veld in ('name="hub_adres"', 'name="koppelcode"', 'name="hub_vingerafdruk"'):
        assert veld in page.text


def test_readyz_zonder_geheimen(tmp_path: Path) -> None:
    c = TestClient(create_app(Settings(data_dir=tmp_path)))
    assert c.get("/readyz").status_code == 503


@pytest.mark.parametrize(
    "action",
    [
        "app.restart",
        "app.install",
        "zfs.snapshot.create",
        "notification.send",
        "shell.exec",
        "sudo",
        "docker.run",
        "onbekend",
    ],
)
def test_alles_geweigerd(client: TestClient, action: str) -> None:
    r = client.post("/api/v1/execute", json={"action_id": action, "parameters": {}})
    assert r.status_code == 403
    assert r.json()["code"] in ("action_not_allowed", "action_forbidden") and r.json()["trace_id"]
    assert not check(action).allowed
    assert frozenset() == ALLOWLIST


def test_geen_shell_of_docker_routes(client: TestClient) -> None:
    paths = set(client.get("/api/openapi.json").json()["paths"])
    assert paths == {
        "/healthz",
        "/readyz",
        "/api/v1/status",
        "/api/v1/execute",
        "/connector/v1/hub-link",
        "/connector/v1/hub-link/unlink",
    }
    assert client.post("/api/v1/shell", json={"cmd": "id"}).status_code == 404


def test_geheimen_nooit_overschreven(tmp_path: Path) -> None:
    d = tmp_path / "secrets"
    assert sorted(ensure_secrets(d)) == sorted([IDENTITY, VAULT_KEY])
    before = (d / IDENTITY).read_bytes()
    assert ensure_secrets(d) == []
    assert (d / IDENTITY).read_bytes() == before
    assert stat.S_IMODE((d / VAULT_KEY).stat().st_mode) == 0o600 and stat.S_IMODE(d.stat().st_mode) == 0o700
    (d / VAULT_KEY).write_bytes(b"kapot")
    with pytest.raises(FirstStartError):
        ensure_secrets(d)
