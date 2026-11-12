"""TrueNAS-schrijfsleutel en beheer op de executorpagina (contract 1.3 §3.9 en §3.7, ADR-0030; Sim-getest).

De sleutel wordt in twee stappen ingesteld (vingerafdruk tonen → bevestigen + live test), versleuteld bewaard en
nooit teruggegeven. Ontkoppelen, vervangen en vrijgeven vragen een sleutel die op dat moment live wordt geverifieerd
tegen het vastgelegde NAS-adres en certificaat. Elke formulier-POST volgt de regels van het koppelformulier.
"""

from __future__ import annotations

import json
import re
import stat
from collections.abc import Iterator
from html import unescape
from pathlib import Path
from typing import Any

import pytest
from executorhelpers import (
    BASE,
    NAS_HOST,
    READ_KEY,
    WRITE_KEY,
    Hub,
    approved,
    execute,
    nas_hub,
    set_write_key,
    signed,
    write_nas,
)
from executorhelpers import client as hub_client
from fakes.fake_truenas import FakeTrueNAS, KeyProfile
from fastapi.testclient import TestClient
from policyhelpers import HOST, proposal

import executor.app as executor_app
from executor.app import create_app
from executor.config import Settings
from executor.firststart import ensure_secrets
from executor.naslink import NasLinkStore
from executor.truenas import display_fingerprint, fetch_fingerprint

NEW_KEY = "tweede-schrijf-key-9876543210wxyz"
SLEUTEL = "/schrijfsleutel"
BEHEER = "/beheer"


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    fake.keys[NEW_KEY] = KeyProfile(roles=["FULL_ADMIN"], write=True)
    yield fake
    fake.stop()


@pytest.fixture
def hub(tmp_path: Path, nas: FakeTrueNAS) -> Hub:
    return nas_hub(tmp_path / "appdata", nas)


def csrf(c: TestClient) -> str:
    m = re.search(r'name="csrf" value="([^"]+)"', c.get("/").text)
    return m.group(1) if m else ""


def post(c: TestClient, path: str, data: dict[str, str], *, origin: str | None = None, **headers: str) -> Any:
    origin = origin if origin is not None else str(c.base_url).rstrip("/")
    return c.post(path, data={"csrf": csrf(c), **data}, headers={"Origin": origin, **headers})


def code_van(r: Any) -> str | None:
    """De foutcode uit de melding van dít verzoek (niet uit het sjablooncommentaar of een controle-regel)."""
    m = re.search(r'<p class="meta">Code <code>([a-z0-9_]+)</code></p>', r.text)
    return m.group(1) if m else None


def status(c: TestClient) -> dict[str, Any]:
    return dict(c.get("/api/v1/status").json())


def naslink_file(hub: Hub) -> Path:
    return hub.settings.secrets_dir / "naslink.json"


def restart_request(hub: Hub, nas: FakeTrueNAS) -> dict[str, Any]:
    from asm_policy.etag import app_etag

    etag = app_etag(nas.app("my-house"), nas.data["app.image.query"])
    prop = proposal("app.restart", {"host_id": HOST, "app_id": "my-house"}, expected_version=etag)
    return signed(hub, prop, risk_class="R1")


# ------------------------------------------------------------------ instellen in twee stappen
def test_sleutel_instellen_in_twee_stappen(hub: Hub, nas: FakeTrueNAS) -> None:
    c = hub_client(hub)
    pagina = c.get("/").text
    assert 'action="/schrijfsleutel"' in pagina and 'action="/beheer"' not in pagina
    assert "Niet ingesteld" in pagina and status(c)["uitvoeren"]["reden"] == "schrijfsleutel_ontbreekt"

    # Stap 1: alleen de TLS-handdruk; de sleutel wordt niet verstuurd en niet bewaard.
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    vinger = fetch_fingerprint(NAS_HOST, nas.port)
    assert r.status_code == 200, r.text
    assert "Controleer de vingerafdruk van TrueNAS" in r.text and display_fingerprint(vinger) in r.text
    assert 'role="status"' in r.text and WRITE_KEY not in r.text
    assert nas.logins == 0 and nas.calls == []
    opgeslagen = json.loads(naslink_file(hub).read_text())
    assert opgeslagen["key"] is None and opgeslagen["pending"]["fingerprint"] == vinger
    assert WRITE_KEY not in naslink_file(hub).read_text()
    assert status(c)["schrijfsleutel"]["ingesteld"] is False and status(c)["truenas"]["adres"] is None
    # De wachtende vingerafdruk blijft zichtbaar bij opnieuw laden (bestaande toestand, geen live-rol).
    opnieuw = c.get("/").text
    assert display_fingerprint(vinger) in opnieuw and "Wacht op je bevestiging" in opnieuw

    # Stap 2: dezelfde sleutel nogmaals = bevestigen → live test tegen precies dat certificaat → opslaan.
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and "De schrijfsleutel is getest en opgeslagen." in r.text, r.text
    assert nas.logins == 1 and [m for m, _ in nas.calls] == ["auth.login_with_api_key", "auth.me", "core.get_methods"]
    assert WRITE_KEY not in r.text and WRITE_KEY not in str(nas.calls)

    st = status(c)
    assert st["schrijfsleutel"]["ingesteld"] is True and st["schrijfsleutel"]["laatste4"] == WRITE_KEY[-4:]
    assert st["truenas"] == {"adres": NAS_HOST, "poort": nas.port, "tls_vingerafdruk": vinger}
    assert st["uitvoeren"] == {"mogelijk": True, "reden": None} and WRITE_KEY not in json.dumps(st)

    # Versleuteld, 0600, en alleen de laatste 4 tekens leesbaar.
    pad = naslink_file(hub)
    assert stat.S_IMODE(pad.stat().st_mode) == 0o600
    ruw = pad.read_text()
    assert WRITE_KEY not in ruw and json.loads(ruw)["laatste4"] == WRITE_KEY[-4:] and json.loads(ruw)["pending"] is None
    assert NasLinkStore(hub.settings.secrets_dir).api_key() == WRITE_KEY

    pagina = c.get("/").text
    assert 'action="/schrijfsleutel"' not in pagina and 'action="/beheer"' in pagina
    assert f"Eindigt op {WRITE_KEY[-4:]}" in pagina and "Vastgelegd" in pagina and display_fingerprint(vinger) in pagina
    assert WRITE_KEY not in pagina

    # En nu voert de executor een ondertekende actie uit.
    assert execute(c, hub, restart_request(hub, nas)).status_code == 200


def test_tweede_keer_instellen_kan_niet(hub: Hub, nas: FakeTrueNAS) -> None:
    set_write_key(hub, nas)
    c = hub_client(hub)
    r = post(c, SLEUTEL, {"truenas_sleutel": NEW_KEY})
    assert r.status_code == 409 and code_van(r) == "sleutel_al_ingesteld"
    assert NasLinkStore(hub.settings.secrets_dir).api_key() == WRITE_KEY and nas.logins == 0


@pytest.mark.parametrize(
    ("sleutel", "code"),
    [(READ_KEY, "schrijfrechten_ontbreken"), ("bestaat-niet-0123456789", "sleutel_geweigerd")],
    ids=["alleen_lezen", "onbekend"],
)
def test_sleutel_zonder_schrijfrechten_of_onbekend_wordt_niet_opgeslagen(
    hub: Hub, nas: FakeTrueNAS, sleutel: str, code: str
) -> None:
    c = hub_client(hub)
    assert post(c, SLEUTEL, {"truenas_sleutel": sleutel}).status_code == 200  # stap 1
    r = post(c, SLEUTEL, {"truenas_sleutel": sleutel})
    assert r.status_code == 400 and code_van(r) == code and 'role="alert"' in r.text, r.text
    assert 'aria-invalid="true"' in r.text and 'id="sleutel-fout"' in r.text and sleutel not in r.text
    assert json.loads(naslink_file(hub).read_text())["key"] is None
    assert status(c)["schrijfsleutel"]["ingesteld"] is False
    # De vingerafdruk is al bevestigd: een goede sleutel wordt daarna direct getest en opgeslagen.
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and "getest en opgeslagen" in r.text, r.text


@pytest.mark.parametrize("sleutel", ["", "met spatie erin", "x" * 513, "niet-ascii-é"])
def test_ongeldige_invoer_gaat_nergens_heen(hub: Hub, nas: FakeTrueNAS, sleutel: str) -> None:
    c = hub_client(hub)
    r = post(c, SLEUTEL, {"truenas_sleutel": sleutel})
    assert r.status_code == 422 and code_van(r) == "sleutel_ongeldig", r.text
    assert not naslink_file(hub).exists() or json.loads(naslink_file(hub).read_text())["pending"] is None
    assert nas.calls == []
    if sleutel:
        assert sleutel not in r.text  # nooit weerspiegelde invoer


def test_certificaat_gewijzigd_na_stap_1_begint_opnieuw(hub: Hub, nas: FakeTrueNAS) -> None:
    c = hub_client(hub)
    assert post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY}).status_code == 200
    pad = naslink_file(hub)
    data = json.loads(pad.read_text())
    data["pending"]["fingerprint"] = "0" * 64  # de beheerder bevestigde een ander certificaat dan er nu staat
    pad.write_text(json.dumps(data))
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 409 and code_van(r) == "certificaat_gewijzigd", r.text
    assert nas.logins == 0 and nas.calls == []  # de sleutel is niet verstuurd
    assert json.loads(pad.read_text())["pending"] is None and json.loads(pad.read_text())["key"] is None
    # Opnieuw: stap 1 toont de vingerafdruk die er nu wél staat.
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and display_fingerprint(fetch_fingerprint(NAS_HOST, nas.port)) in r.text


def test_truenas_onbereikbaar_bij_stap_1(hub: Hub, nas: FakeTrueNAS) -> None:
    c = hub_client(hub)
    nas.offline()
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 502 and code_van(r) == "truenas_onbereikbaar", r.text
    assert not naslink_file(hub).exists() or json.loads(naslink_file(hub).read_text())["pending"] is None


def test_niet_gekoppeld_geen_sleutelformulier(tmp_path: Path, nas: FakeTrueNAS) -> None:
    settings = Settings(data_dir=tmp_path / "leeg", truenas_host=NAS_HOST, truenas_port=nas.port)
    ensure_secrets(settings.secrets_dir)
    c = TestClient(create_app(settings), base_url=BASE)
    pagina = c.get("/").text
    assert 'action="/koppelen"' in pagina and 'action="/schrijfsleutel"' not in pagina
    assert "Wordt gevraagd zodra de executor gekoppeld is." in pagina
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 409 and code_van(r) == "niet_gekoppeld"
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "actie": "ontkoppelen"})
    assert r.status_code == 409 and code_van(r) == "geen_schrijfsleutel"
    assert nas.calls == []


# ------------------------------------------------------------------ §3.7 geldt voor elk formulier
@pytest.mark.parametrize("pad", [SLEUTEL, BEHEER])
def test_herkomst_formuliercode_en_host(hub: Hub, nas: FakeTrueNAS, pad: str) -> None:
    if pad == BEHEER:
        set_write_key(hub, nas)
    c = hub_client(hub)
    velden = {"truenas_sleutel": WRITE_KEY, "actie": "ontkoppelen"}
    token = csrf(c)

    r = c.post(pad, data={"csrf": token, **velden})  # geen Origin
    assert r.status_code == 403 and code_van(r) == "herkomst_onjuist"
    for origin in ("null", "http://kwaad.example", "https://executor.local", "http://executor.local:8080"):
        r = c.post(pad, data={"csrf": token, **velden}, headers={"Origin": origin})
        assert r.status_code == 403 and code_van(r) == "herkomst_onjuist", origin
    r = c.post(pad, data={"csrf": token, **velden}, headers={"Origin": BASE, "Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403 and code_van(r) == "herkomst_onjuist"
    r = c.post(pad, data={"csrf": "x" * 43, **velden}, headers={"Origin": BASE})
    assert r.status_code == 403 and code_van(r) == "formuliercode_onjuist"
    r = c.post(pad, data=velden, headers={"Origin": BASE})
    assert r.status_code == 403 and code_van(r) == "formuliercode_onjuist"
    # DNS-rebinding: een publieke naam als Host wordt geweigerd, ook met passende Origin.
    r = c.post(pad, data={"csrf": token, **velden}, headers={"Origin": "http://kwaad.example", "Host": "kwaad.example"})
    assert r.status_code == 403 and code_van(r) == "host_niet_toegestaan"

    assert nas.calls == [] and nas.logins == 0
    st = status(c)
    assert st["gekoppeld"] is True and st["schrijfsleutel"]["ingesteld"] is (pad == BEHEER)


@pytest.mark.parametrize("pad", [SLEUTEL, BEHEER])
def test_pogingenlimiet_geldt_ook_voor_de_sleutelformulieren(hub: Hub, nas: FakeTrueNAS, pad: str) -> None:
    if pad == BEHEER:
        set_write_key(hub, nas)
    c = hub_client(hub)
    for _ in range(5):
        r = post(c, pad, {"truenas_sleutel": "bestaat-niet-0123456789", "actie": "ontkoppelen"})
        assert r.status_code != 429
    r = post(c, pad, {"truenas_sleutel": WRITE_KEY, "actie": "ontkoppelen"})
    assert r.status_code == 429 and code_van(r) == "rate_limited"
    assert status(c)["gekoppeld"] is True


def test_te_groot_formulier(hub: Hub, nas: FakeTrueNAS) -> None:
    c = hub_client(hub)
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY, "vulling": "x" * 70000})
    assert r.status_code == 413 and code_van(r) == "formulier_te_groot"
    assert nas.calls == []


# ------------------------------------------------------------------ het NAS-adres
def test_nas_adres_uit_het_adres_van_de_pagina(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Zonder ``EXECUTOR_TRUENAS_HOST``: het IP-adres waarop de beheerder de pagina opent is het NAS-adres. Een naam of
    loopback telt niet (geen bewijs van het NAS-adres)."""
    hub = Hub(tmp_path / "appdata")
    gezien: list[tuple[Any, ...]] = []

    def fake_fingerprint(host: str, port: int, *, timeout: float = 5.0) -> str:
        gezien.append(("vingerafdruk", host, port))
        return "ab" * 32

    def fake_verify(host: str, port: int, fingerprint: str, api_key: str, *, timeout: float = 15.0) -> Any:
        gezien.append(("test", host, port, fingerprint))
        return ["FULL_ADMIN"], frozenset({"app.query"})

    monkeypatch.setattr(executor_app, "fetch_fingerprint", fake_fingerprint)
    monkeypatch.setattr(executor_app, "verify_key", fake_verify)

    for base in (BASE, "http://127.0.0.1:30410", "http://nas:30410"):
        c = TestClient(create_app(hub.settings), base_url=base)
        r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
        assert r.status_code == 409 and code_van(r) == "nas_adres_onbekend", base
    assert gezien == []

    c = TestClient(create_app(hub.settings), base_url="http://192.0.2.10:30410")  # documentatie-adres (RFC 5737)
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and display_fingerprint("ab" * 32) in r.text, r.text
    assert gezien == [("vingerafdruk", "192.0.2.10", 443)]
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and "getest en opgeslagen" in r.text, r.text
    assert gezien[-1] == ("test", "192.0.2.10", 443, "ab" * 32)
    assert status(c)["truenas"] == {"adres": "192.0.2.10", "poort": 443, "tls_vingerafdruk": "ab" * 32}


def test_ander_adres_tijdens_de_bevestiging_begint_opnieuw(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """De bevestiging hoort bij één adres: wie stap 2 via een ander adres doet, krijgt stap 1 voor dát adres."""
    hub = Hub(tmp_path / "appdata")
    gezien: list[tuple[str, str]] = []

    def fake_fingerprint(host: str, port: int, *, timeout: float = 5.0) -> str:
        gezien.append(("vingerafdruk", host))
        return ("ab" if host == "192.0.2.10" else "cd") * 32

    def fake_verify(host: str, port: int, fingerprint: str, api_key: str, *, timeout: float = 15.0) -> Any:
        gezien.append(("test", host))
        return ["FULL_ADMIN"], frozenset()

    monkeypatch.setattr(executor_app, "fetch_fingerprint", fake_fingerprint)
    monkeypatch.setattr(executor_app, "verify_key", fake_verify)
    een = TestClient(create_app(hub.settings), base_url="http://192.0.2.10:30410")
    twee = TestClient(create_app(hub.settings), base_url="http://192.0.2.20:30410")
    assert post(een, SLEUTEL, {"truenas_sleutel": WRITE_KEY}).status_code == 200
    r = post(twee, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and display_fingerprint("cd" * 32) in r.text
    assert gezien == [("vingerafdruk", "192.0.2.10"), ("vingerafdruk", "192.0.2.20")]
    assert status(twee)["schrijfsleutel"]["ingesteld"] is False


# ------------------------------------------------------------------ beheer: vervangen, vrijgeven, ontkoppelen
def test_sleutel_vervangen_met_bewijs(hub: Hub, nas: FakeTrueNAS) -> None:
    vinger = set_write_key(hub, nas)
    c = hub_client(hub)
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "vervangen"})
    assert r.status_code == 200 and "De schrijfsleutel is vervangen." in r.text, r.text
    assert WRITE_KEY not in r.text and NEW_KEY not in r.text and nas.logins == 2
    st = status(c)
    assert st["schrijfsleutel"]["laatste4"] == NEW_KEY[-4:]
    assert st["truenas"] == {"adres": NAS_HOST, "poort": nas.port, "tls_vingerafdruk": vinger}
    assert NasLinkStore(hub.settings.secrets_dir).api_key() == NEW_KEY
    ruw = naslink_file(hub).read_text()
    assert WRITE_KEY not in ruw and NEW_KEY not in ruw
    assert execute(c, hub, restart_request(hub, nas)).status_code == 200


@pytest.mark.parametrize(
    ("velden", "status_code", "code"),
    [
        (
            {"truenas_sleutel": "bestaat-niet-0123456789", "nieuwe_sleutel": NEW_KEY, "actie": "vervangen"},
            400,
            "sleutel_geweigerd",
        ),
        (
            {"truenas_sleutel": READ_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "vervangen"},
            400,
            "schrijfrechten_ontbreken",
        ),
        (
            {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": READ_KEY, "actie": "vervangen"},
            400,
            "schrijfrechten_ontbreken",
        ),
        (
            {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": "bestaat-niet-0123456789", "actie": "vervangen"},
            400,
            "sleutel_geweigerd",
        ),
        ({"truenas_sleutel": WRITE_KEY, "actie": "vervangen"}, 422, "nieuwe_sleutel_ontbreekt"),
        ({"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY}, 422, "actie_onbekend"),
        ({"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "wissen"}, 422, "actie_onbekend"),
        ({"truenas_sleutel": "", "actie": "ontkoppelen"}, 422, "sleutel_ongeldig"),
        ({"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": "met spatie", "actie": "vervangen"}, 422, "sleutel_ongeldig"),
        ({"truenas_sleutel": "bestaat-niet-0123456789", "actie": "ontkoppelen"}, 400, "sleutel_geweigerd"),
        ({"truenas_sleutel": READ_KEY, "actie": "ontkoppelen"}, 400, "schrijfrechten_ontbreken"),
    ],
    ids=[
        "bewijs_onbekend",
        "bewijs_alleen_lezen",
        "nieuw_alleen_lezen",
        "nieuw_onbekend",
        "nieuw_ontbreekt",
        "geen_actie",
        "onbekende_actie",
        "bewijs_leeg",
        "nieuw_ongeldig",
        "ontkoppelen_bewijs_onbekend",
        "ontkoppelen_bewijs_alleen_lezen",
    ],
)
def test_beheer_zonder_geldig_bewijs_verandert_niets(
    hub: Hub, nas: FakeTrueNAS, velden: dict[str, str], status_code: int, code: str
) -> None:
    set_write_key(hub, nas)
    voor = naslink_file(hub).read_text()
    c = hub_client(hub)
    r = post(c, BEHEER, velden)
    assert r.status_code == status_code and code_van(r) == code and 'role="alert"' in r.text, r.text
    assert naslink_file(hub).read_text() == voor
    st = status(c)
    assert st["gekoppeld"] is True and st["schrijfsleutel"]["laatste4"] == WRITE_KEY[-4:]
    for geheim in (WRITE_KEY, NEW_KEY, READ_KEY):
        assert geheim not in r.text


def test_beheer_kan_geen_ander_adres_of_certificaat_opgeven(hub: Hub, nas: FakeTrueNAS) -> None:
    """Extra formuliervelden voor adres of vingerafdruk doen niets: het bewijs gaat altijd naar het vastgelegde NAS."""
    vinger = set_write_key(hub, nas)
    ander = write_nas().start()
    try:
        c = hub_client(hub)
        r = post(
            c,
            BEHEER,
            {
                "truenas_sleutel": WRITE_KEY,
                "nieuwe_sleutel": NEW_KEY,
                "actie": "vervangen",
                "nas_adres": NAS_HOST,
                "nas_poort": str(ander.port),
                "truenas_port": str(ander.port),
                "tls_vingerafdruk": fetch_fingerprint(NAS_HOST, ander.port),
            },
        )
        assert r.status_code == 200, r.text
        assert ander.logins == 0 and ander.calls == [] and nas.logins == 2
        assert status(c)["truenas"] == {"adres": NAS_HOST, "poort": nas.port, "tls_vingerafdruk": vinger}
    finally:
        ander.stop()


def test_beheer_bij_gewijzigd_certificaat_verstuurt_de_sleutel_niet(hub: Hub, nas: FakeTrueNAS) -> None:
    NasLinkStore(hub.settings.secrets_dir).save_key(NAS_HOST, nas.port, "0" * 64, WRITE_KEY, ["FULL_ADMIN"])
    c = hub_client(hub)
    for actie in ("ontkoppelen", "vervangen"):
        r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": actie})
        assert r.status_code == 409 and code_van(r) == "certificaat_gewijzigd", r.text
    assert nas.logins == 0 and nas.calls == [] and status(c)["gekoppeld"] is True


def test_vrijgeven_na_een_afwijking(hub: Hub, nas: FakeTrueNAS) -> None:
    set_write_key(hub, nas)
    c = hub_client(hub)
    from asm_policy.etag import app_etag

    nas.silent_noop.add("app.stop")
    prop = proposal(
        "app.stop",
        {"host_id": HOST, "app_id": "my-house"},
        expected_version=app_etag(nas.app("my-house"), nas.data["app.image.query"]),
    )
    # my-house is een Custom App: stoppen is R2 en vraagt een goedkeuring (ADR-0030 besluit 21).
    r = execute(c, hub, approved(hub, prop, risk_class="R2"))
    assert r.status_code == 409 and r.json()["code"] == "afwijking"
    nas.silent_noop.clear()
    pagina = c.get("/").text
    assert "Gestopt" in pagina and "executor_gestopt" in pagina and "Storing" in pagina
    assert execute(c, hub, restart_request(hub, nas)).json()["code"] == "executor_gestopt"

    # Zonder geldig bewijs blijft hij gestopt.
    r = post(c, BEHEER, {"truenas_sleutel": "bestaat-niet-0123456789", "actie": "vervangen"})
    assert r.status_code == 400 and status(c)["gestopt"] is not None
    # Met de huidige sleutel en een leeg veld "Nieuwe sleutel": vrijgegeven, sleutel ongewijzigd.
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "actie": "vervangen"})
    assert r.status_code == 200 and "De executor is vrijgegeven." in r.text, r.text
    st = status(c)
    assert st["gestopt"] is None and st["uitvoeren"] == {"mogelijk": True, "reden": None}
    assert st["schrijfsleutel"]["laatste4"] == WRITE_KEY[-4:]
    assert execute(c, hub, restart_request(hub, nas)).status_code == 200


def test_vervangen_en_vrijgeven_in_een_keer(hub: Hub, nas: FakeTrueNAS) -> None:
    from executor.journal import Journal

    set_write_key(hub, nas)
    Journal(hub.settings.replay_db, hub.settings.secrets_dir).stop({"code": "staat_verschilt", "at": "nu"})
    c = hub_client(hub)
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "vervangen"})
    assert r.status_code == 200 and "vervangen en de executor is vrijgegeven" in r.text, r.text
    assert status(c)["gestopt"] is None and status(c)["schrijfsleutel"]["laatste4"] == NEW_KEY[-4:]


def test_ontkoppelen_met_bewijs_en_opnieuw_koppelen_mogelijk(hub: Hub, nas: FakeTrueNAS) -> None:
    vinger = set_write_key(hub, nas)
    c = hub_client(hub)
    request = restart_request(hub, nas)
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "actie": "ontkoppelen"})
    assert r.status_code == 200 and "Ontkoppeld van de Hub." in r.text, r.text
    st = status(c)
    assert st["gekoppeld"] is False and st["uitvoeren"] == {"mogelijk": False, "reden": "niet_gekoppeld"}
    # NAS-adres, certificaat en sleutel blijven bewaard; de Hub wordt niet meer vertrouwd.
    assert st["schrijfsleutel"]["ingesteld"] is True
    assert st["truenas"] == {"adres": NAS_HOST, "poort": nas.port, "tls_vingerafdruk": vinger}
    assert execute(c, hub, request).status_code == 401
    assert [m for m in nas.mutations if m != "app.config"] == []
    # Het koppelformulier is terug (opnieuw koppelen met een koppelcode), het beheerformulier blijft.
    pagina = c.get("/").text
    assert 'action="/koppelen"' in pagina and 'action="/beheer"' in pagina and 'action="/schrijfsleutel"' not in pagina


def test_onleesbaar_koppelbestand_herstellen_met_de_sleutel(hub: Hub, nas: FakeTrueNAS) -> None:
    set_write_key(hub, nas)
    (hub.settings.secrets_dir / "hub-link.json").write_text("{kapot", encoding="utf-8")
    c = hub_client(hub)
    pagina = c.get("/").text
    assert "De koppelstatus is onleesbaar" in pagina and "<code>koppelstatus_onleesbaar</code>" in pagina
    assert 'action="/beheer"' in pagina and 'action="/koppelen"' not in pagina
    assert "vul onder" in pagina and "daarna kun je opnieuw koppelen met een koppelcode" in pagina
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "actie": "ontkoppelen"})
    assert r.status_code == 200 and "Ontkoppeld van de Hub." in r.text, r.text
    pagina = c.get("/").text
    assert "De koppelstatus is onleesbaar" not in pagina and 'action="/koppelen"' in pagina


def test_onleesbare_sleutelopslag_geen_formulier_en_geen_beheer(hub: Hub, nas: FakeTrueNAS) -> None:
    set_write_key(hub, nas)
    naslink_file(hub).write_text("{kapot", encoding="utf-8")
    c = hub_client(hub)
    pagina = c.get("/").text
    assert "<code>sleutelopslag_onleesbaar</code>" in pagina and "Onleesbaar" in pagina
    assert 'action="/schrijfsleutel"' not in pagina and 'action="/beheer"' not in pagina
    assert naslink_file(hub).read_text() == "{kapot"  # nooit stil overschreven


HERSTEL_HIER = "Herstel gaat met de TrueNAS-schrijfsleutel op deze pagina (Ontkoppelen van de Hub)."
HERSTEL_DOC = "Zie deploy/truenas/CUSTOM_APP.md, kop 'Herstel'."


@pytest.mark.parametrize("sleutel", ["ingesteld", "niet_ingesteld", "opslag_onleesbaar"])
def test_melding_koppelstatus_onleesbaar_noemt_de_herstelweg_die_er_is(
    hub: Hub, nas: FakeTrueNAS, sleutel: str
) -> None:
    """R-ONTWERP-4 (S-P2-005): het formulierantwoord en ``last_error`` in /api/v1/status bij koppelstatus_onleesbaar
    noemen 'Ontkoppelen van de Hub' op deze pagina alleen als dat blok er staat (een bruikbare schrijfsleutel); anders
    verwijzen ze naar de kop 'Herstel' in het installatiedocument."""
    if sleutel != "niet_ingesteld":
        set_write_key(hub, nas)
    c = hub_client(hub)
    formuliercode = csrf(c)  # van een tabblad van vóór het onleesbaar worden (sleutel- of beheerformulier)
    assert formuliercode
    (hub.settings.secrets_dir / "hub-link.json").write_text("{kapot", encoding="utf-8")
    if sleutel == "opslag_onleesbaar":
        naslink_file(hub).write_text("{kapot", encoding="utf-8")
    bruikbaar = sleutel == "ingesteld"
    for pad in ("/koppelen", SLEUTEL):
        r = c.post(pad, data={"csrf": formuliercode}, headers={"Origin": str(c.base_url).rstrip("/")})
        assert r.status_code == 409 and code_van(r) == "koppelstatus_onleesbaar", r.text
        # Met het beheerblok krijgt het antwoord een nieuwe formuliercode (en cookie); zonder blijft de oude geldig.
        formuliercode = m.group(1) if (m := re.search(r'name="csrf" value="([^"]+)"', r.text)) else formuliercode
        tekst = unescape(r.text)
        assert ('action="/beheer"' in r.text) is bruikbaar
        assert (HERSTEL_HIER in tekst) is bruikbaar, f"{pad}: herstel op deze pagina terwijl het blok er niet is"
        assert (HERSTEL_DOC in tekst) is not bruikbaar, f"{pad}: verwijzing naar de kop 'Herstel' klopt niet"
    melding = status(c)["koppeling"]["last_error"]["melding"]
    assert (HERSTEL_HIER in melding) is bruikbaar and (HERSTEL_DOC in melding) is not bruikbaar, melding
