"""Executor: gezondheid, statuspagina 'nog niet gekoppeld', alleen ondertekende acties van de allowlist (na
aanmelding), eigen geheimen, onleesbaar koppelbestand (contract 1.3 §3.5: fail-closed, /readyz blijft 200)."""

from __future__ import annotations

import stat
import uuid
from pathlib import Path

import pytest
from executorhelpers import POLICY, Hub, auth, execute, signed
from executorhelpers import client as hub_client
from fastapi.testclient import TestClient
from policyhelpers import HOST, proposal

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
    assert st["gekoppeld"] is False and st["identiteit"]["crv"] == "Ed25519"
    assert "d" not in st["identiteit"]
    # Allowlist v1 en policy_hash komen uit het ingebakken beleid (contract 1.3 §8); zonder koppeling en zonder
    # schrijfsleutel voert de executor niets uit.
    assert st["allowlist"] == POLICY.executor_allowlist() and st["policy"]["hash"] == POLICY.hash
    assert st["uitvoeren"] == {"mogelijk": False, "reden": "niet_gekoppeld"}
    assert st["schrijfsleutel"] == {"ingesteld": False, "onleesbaar": False, "laatste4": None, "ingesteld_op": None}
    assert st["truenas"] == {"adres": None, "poort": None, "tls_vingerafdruk": None} and st["gestopt"] is None
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


def test_execute_eerst_aanmelden_dan_vorm(tmp_path: Path) -> None:
    hub = Hub(tmp_path / "appdata", allow_writable_policy=True)
    c = hub_client(hub)
    # Zonder aanmelding: 401 (eerst authenticatie, contract 1.3 §4.7).
    assert c.post("/api/v1/execute", json={"action_id": "app.restart"}).status_code == 401
    # Een gebruikers-JWT is geen dienst-JWT van de Hub.
    r = c.post("/api/v1/execute", json={}, headers=auth(hub.user_jwt(["admin"]), str(uuid.uuid4())))
    assert r.status_code == 403 and r.json()["code"] == "forbidden"
    # Een losse action_id is geen ExecutionRequest: zonder handtekening van de Hub gebeurt er niets.
    for body in ({"action_id": "app.restart", "parameters": {}}, [], "tekst", {}):
        r = execute(c, hub, body)
        assert r.status_code == 422, r.text
        assert r.json()["code"] in ("execution_request_ongeldig", "validation_error") and r.json()["trace_id"]


@pytest.mark.parametrize(
    ("action", "code"),
    [
        ("shell.exec", "actie_geweigerd"),
        ("sudo", "actie_geweigerd"),
        ("docker.run", "actie_geweigerd"),
        ("app.delete", "actie_geweigerd"),
        ("pool.dataset.delete", "actie_geweigerd"),
        ("boiler.aan", "actie_geweigerd"),
        ("onbekend", "actie_niet_toegestaan"),
        ("notification.send", "actie_niet_toegestaan"),  # hoort bij de Hub (Gotify), niet bij de executor
        ("sso.sessions.revoke", "actie_niet_toegestaan"),  # hoort bij de eigenaar-connector
    ],
)
def test_buiten_de_allowlist_altijd_geweigerd(tmp_path: Path, action: str, code: str) -> None:
    """Ook met een geldige handtekening van de Hub: wat niet op de allowlist staat wordt geweigerd (EX17, EX27)."""
    hub = Hub(tmp_path / "appdata", allow_writable_policy=True)
    c = hub_client(hub)
    prop = proposal(action, {"host_id": HOST}, {"titel": "t", "tekst": "t"} if action == "notification.send" else {})
    r = execute(c, hub, signed(hub, prop, risk_class="R3"))
    assert r.status_code == 403, r.text
    assert r.json()["code"] == code and r.json()["trace_id"]


def test_zonder_schrijfsleutel_capability_unavailable_nooit_gesimuleerd_succes(tmp_path: Path) -> None:
    hub = Hub(tmp_path / "appdata", allow_writable_policy=True)
    c = hub_client(hub)
    st = c.get("/api/v1/status").json()
    assert st["uitvoeren"] == {"mogelijk": False, "reden": "schrijfsleutel_ontbreekt"}
    prop = proposal("app.restart", {"host_id": HOST, "app_id": "demo-app"}, expected_version="sha256:" + "0" * 64)
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 501, r.text
    assert r.json()["code"] == "capability_unavailable" and r.json()["details"]["reden"] == "schrijfsleutel_ontbreekt"


def test_beschrijfbaar_beleid_voert_niets_uit(tmp_path: Path) -> None:
    """In het image is het beleid alleen-lezen (§8). Is het beschrijfbaar (zoals hier in de repo) en staat de
    ontwikkelschakelaar uit, dan weigert de executor elk verzoek."""
    hub = Hub(tmp_path / "appdata")
    c = hub_client(hub)
    st = c.get("/api/v1/status").json()
    assert st["policy"]["read_only"] is False and st["uitvoeren"]["mogelijk"] is False
    prop = proposal("app.restart", {"host_id": HOST, "app_id": "demo-app"}, expected_version="sha256:" + "0" * 64)
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 503 and r.json()["code"] == "policy_niet_read_only", r.text
    assert "Beschrijfbaar" in c.get("/").text and "policy_niet_read_only" in c.get("/").text


def test_onleesbaar_beleid_voert_niets_uit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    leeg = tmp_path / "geen-beleid"
    leeg.mkdir()
    monkeypatch.setenv("ASM_POLICY_DIR", str(leeg))
    hub = Hub(tmp_path / "appdata", allow_writable_policy=True)
    c = hub_client(hub)
    st = c.get("/api/v1/status").json()
    assert st["policy"]["geladen"] is False and st["allowlist"] == []
    assert st["uitvoeren"] == {"mogelijk": False, "reden": "policy_niet_beschikbaar"}
    prop = proposal("app.restart", {"host_id": HOST, "app_id": "demo-app"}, expected_version="sha256:" + "0" * 64)
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 503 and r.json()["code"] == "policy_niet_beschikbaar", r.text
    page = c.get("/").text
    assert "policy_niet_beschikbaar" in page and "Niet beschikbaar" in page


def test_geen_shell_of_docker_routes(client: TestClient) -> None:
    paths = set(client.get("/api/openapi.json").json()["paths"])
    assert paths == {
        "/healthz",
        "/readyz",
        "/api/v1/status",
        "/api/v1/execute",
        "/api/v1/executions/{request_id}",
        "/connector/v1/hub-link",
        "/connector/v1/hub-link/unlink",
    }
    assert client.post("/api/v1/shell", json={"cmd": "id"}).status_code == 404
    # De formulierroutes van de statuspagina staan niet in de API-beschrijving.
    assert not {"/koppelen", "/schrijfsleutel", "/beheer"} & paths


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


@pytest.mark.parametrize(
    "extra",
    [
        "&".join(f"veld{i}=1" for i in range(10)),  # meer velden dan het formulier heeft (parse_qs max_num_fields)
        "opvulling=" + "x" * 5000,  # body > 4096 bytes
    ],
    ids=["te_veel_velden", "te_grote_body"],
)
def test_te_groot_formulier_geeft_vaste_melding_nooit_een_kale_500(tmp_path: Path, extra: str) -> None:
    """§3.7: elk geweigerd formulier krijgt een vaste Nederlandse melding in het sjabloon (geen 500 zonder uitleg), gaat
    niet naar de Hub en verandert niets aan het koppelbestand."""
    import re

    s = Settings(data_dir=tmp_path)
    ensure_secrets(s.secrets_dir)
    c = TestClient(create_app(s), base_url="http://executor.local", raise_server_exceptions=False)
    csrf = re.search(r'name="csrf" value="([^"]+)"', c.get("/").text)
    assert csrf is not None
    body = (
        f"csrf={csrf.group(1)}&hub_adres=http%3A%2F%2F192.0.2.5%3A30400&koppelcode=ABCD-EFGH-JKMN"
        f"&hub_vingerafdruk=MEGG-8GFG-2E4Y-K2RQ&{extra}"
    )
    r = c.post(
        "/koppelen",
        content=body,
        headers={"Origin": "http://executor.local", "Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 413, r.text[:200]
    assert r.headers["content-type"].startswith("text/html")
    assert "formulier_te_groot" in r.text and "Het formulier is te groot." in r.text
    assert not (s.secrets_dir / "hub-link.json").exists()  # niets geschreven, geen poging naar de Hub
