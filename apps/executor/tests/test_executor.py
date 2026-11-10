"""Executor: gezondheid, statuspagina 'nog niet gekoppeld', allowlist weigert alles (na aanmelding), eigen geheimen,
onleesbaar koppelbestand (contract 1.3 §3.5: fail-closed, /readyz blijft 200)."""

from __future__ import annotations

import stat
import uuid
from pathlib import Path

import pytest
from executorhelpers import Hub, auth
from executorhelpers import client as hub_client
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
def test_alles_geweigerd(tmp_path: Path, action: str) -> None:
    hub = Hub(tmp_path / "appdata")
    c = hub_client(hub)
    # Zonder aanmelding: 401 (eerst authenticatie, contract 1.3 §4.7); daarna weigert de allowlist alles.
    assert c.post("/api/v1/execute", json={"action_id": action}).status_code == 401
    r = c.post(
        "/api/v1/execute", json={"action_id": action, "parameters": {}}, headers=auth(hub.jwt(), str(uuid.uuid4()))
    )
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


@pytest.mark.parametrize(
    "inhoud",
    [
        b"{kapot",
        b"[]",
        b'{"schema_version": "2.0", "state": "nooit_gekoppeld"}',
        b'{"schema_version": "1.3"}',
        b'{"schema_version": "1.3", "state": "gekoppeld"}',
        b'{"schema_version": "1.3", "state": "ontkoppeld"}',
    ],
)
def test_onleesbaar_koppelbestand_is_fail_closed(tmp_path: Path, inhoud: bytes) -> None:
    hub = Hub(tmp_path / "appdata")
    path = hub.settings.secrets_dir / "hub-link.json"
    path.write_bytes(inhoud)
    c = hub_client(hub)
    # /readyz blijft 200: de koppeling telt daar niet mee (§5); de reden staat in de details.
    r = c.get("/readyz")
    assert r.status_code == 200 and r.json()["gekoppeld"] is False
    assert {"name": "koppeling", "status": "onleesbaar", "code": "koppelstatus_onleesbaar"} in r.json()["checks"]
    # Geen vertrouwen in Hub-JWT's (401 not_linked) en geen koppelformulier.
    r = c.get("/connector/v1/hub-link", headers=auth(hub.jwt()))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "not_linked"
    page = c.get("/")
    assert 'name="koppelcode"' not in page.text and "koppelstatus_onleesbaar" in page.text
    assert "/appdata/secrets/hub-link.json" in page.text and 'role="alert"' not in page.text  # bestaande toestand
    st = c.get("/api/v1/status").json()
    assert st["koppeling"]["last_error"]["code"] == "koppelstatus_onleesbaar" and st["gereed"] is False
    assert path.read_bytes() == inhoud  # nooit stil teruggezet


def test_verkeerde_rechten_of_eigenaar_is_onleesbaar(tmp_path: Path) -> None:
    hub = Hub(tmp_path / "appdata")
    path = hub.settings.secrets_dir / "hub-link.json"
    path.chmod(0o644)
    r = hub_client(hub).get("/connector/v1/hub-link", headers=auth(hub.jwt()))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "not_linked"
    path.chmod(0o600)
    assert hub_client(hub).get("/connector/v1/hub-link", headers=auth(hub.jwt())).status_code == 200
    # Een symlink naar een (geldig) bestand telt ook als onleesbaar.
    target = tmp_path / "elders.json"
    target.write_bytes(path.read_bytes())
    target.chmod(0o600)
    path.unlink()
    path.symlink_to(target)
    r = hub_client(hub).get("/connector/v1/hub-link", headers=auth(hub.jwt()))
    assert r.status_code == 401 and r.json()["details"]["reason"] == "not_linked"


def test_gereed_alleen_gekoppeld_en_bevestigd(tmp_path: Path) -> None:
    hub = Hub(tmp_path / "appdata")
    c = hub_client(hub)
    assert c.get("/api/v1/status").json()["gereed"] is True
    from executor.hublink import HubLinkStore

    with HubLinkStore(hub.settings.secrets_dir).update() as link:
        link["confirmed_at"] = None
    assert c.get("/api/v1/status").json()["gereed"] is False
    assert c.get("/readyz").status_code == 200  # /readyz hangt niet van de koppeling af
