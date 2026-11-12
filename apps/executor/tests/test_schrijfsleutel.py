"""TrueNAS-schrijfsleutel en beheer op de executorpagina (contract 1.3 §3.9 en §3.7, ADR-0030; Sim-getest).

De sleutel wordt in twee stappen ingesteld (vingerafdruk tonen → bevestigen + live test), versleuteld bewaard en
nooit teruggegeven. Ontkoppelen, vervangen en vrijgeven vragen een sleutel die op dat moment live wordt geverifieerd
tegen het vastgelegde NAS-adres en certificaat. Elke formulier-POST volgt de regels van het koppelformulier.
"""

from __future__ import annotations

import json
import logging
import os
import re
import stat
import subprocess
import sys
import typing
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

NEW_KEY = "tweede-test-key-xxxxyyyyzzzz"
# Schrijfsleutels die niet de hele allowlist dekken (R-TECH-1), en een sleutel met APPS_WRITE + SNAPSHOT_WRITE.
SNAP_KEY = "snapshot-test-key-ssssnnnnaaaa"
APPS_KEY = "apps-test-key-aaaappppssss"
APPS_SNAP_KEY = "apps-snap-test-key-aassaass"
SLEUTEL = "/schrijfsleutel"
BEHEER = "/beheer"
# Het groene totaal bovenaan de pagina (Peil-sjabloon: pil "Gezond" in de regel "totaal").
TOTAAL_GEZOND = '<p class="totaal"><span class="pil pil-gezond">'


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    fake.keys[NEW_KEY] = KeyProfile(roles=["FULL_ADMIN"], write=True)
    fake.keys[SNAP_KEY] = KeyProfile(roles=["SNAPSHOT_WRITE"], write=True)
    fake.keys[APPS_KEY] = KeyProfile(roles=["APPS_WRITE"], write=True)
    fake.keys[APPS_SNAP_KEY] = KeyProfile(roles=["APPS_WRITE", "SNAPSHOT_WRITE"], write=True)
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
    [
        (READ_KEY, "schrijfrechten_ontbreken"),
        ("bestaat-niet-0123456789", "sleutel_geweigerd"),
        (SNAP_KEY, "schrijfrechten_onvolledig"),
        (APPS_KEY, "schrijfrechten_onvolledig"),
    ],
    ids=["alleen_lezen", "onbekend", "alleen_snapshot_write", "alleen_apps_write"],
)
def test_sleutel_zonder_schrijfrechten_of_onbekend_wordt_niet_opgeslagen(
    hub: Hub, nas: FakeTrueNAS, sleutel: str, code: str
) -> None:
    """Een sleutel telt alleen als schrijfsleutel als zijn rollen de app- én snapshotacties van de allowlist dekken
    (R-TECH-1): alleen SNAPSHOT_WRITE of alleen APPS_WRITE wordt geweigerd, met een vaste melding en nooit "Gezond"."""
    c = hub_client(hub)
    assert post(c, SLEUTEL, {"truenas_sleutel": sleutel}).status_code == 200  # stap 1
    r = post(c, SLEUTEL, {"truenas_sleutel": sleutel})
    assert r.status_code == 400 and code_van(r) == code and 'role="alert"' in r.text, r.text
    assert 'aria-invalid="true"' in r.text and 'id="sleutel-fout"' in r.text and sleutel not in r.text
    assert json.loads(naslink_file(hub).read_text())["key"] is None
    st = status(c)
    assert st["schrijfsleutel"]["ingesteld"] is False
    assert st["uitvoeren"] == {"mogelijk": False, "reden": "schrijfsleutel_ontbreekt"}
    assert TOTAAL_GEZOND not in c.get("/").text
    # De vingerafdruk is al bevestigd: een goede sleutel wordt daarna direct getest en opgeslagen.
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and "getest en opgeslagen" in r.text, r.text
    assert TOTAAL_GEZOND in c.get("/").text  # tegenproef: de controle op "Gezond" hierboven kan falen


def test_apps_write_en_snapshot_write_samen_tellen_als_schrijfsleutel(hub: Hub, nas: FakeTrueNAS) -> None:
    """R-TECH-1: APPS_WRITE samen met SNAPSHOT_WRITE dekt de allowlist (net als FULL_ADMIN)."""
    c = hub_client(hub)
    assert post(c, SLEUTEL, {"truenas_sleutel": APPS_SNAP_KEY}).status_code == 200  # stap 1
    r = post(c, SLEUTEL, {"truenas_sleutel": APPS_SNAP_KEY})
    assert r.status_code == 200 and "getest en opgeslagen" in r.text, r.text
    st = status(c)
    assert st["uitvoeren"] == {"mogelijk": True, "reden": None}
    assert json.loads(naslink_file(hub).read_text())["rollen"] == ["APPS_WRITE", "SNAPSHOT_WRITE"]
    assert execute(c, hub, restart_request(hub, nas)).status_code == 200


@pytest.mark.parametrize(
    ("sleutel", "mag_app", "mag_snapshot"),
    [(WRITE_KEY, True, True), (APPS_SNAP_KEY, True, True), (SNAP_KEY, False, True), (APPS_KEY, True, False)],
    ids=["full_admin", "apps_en_snapshot", "alleen_snapshot", "alleen_apps"],
)
def test_nep_truenas_dwingt_rechten_per_methode_af(
    nas: FakeTrueNAS, sleutel: str, mag_app: bool, mag_snapshot: bool
) -> None:
    """R-TECH-1: de nep-TrueNAS geeft per methode EACCES als de rollen de app- of snapshotmethode niet dekken (aanname
    uit de rolnamen; NIET GEVALIDEERD (echte NAS)). Zo kan een test een te smalle sleutel echt zien falen."""
    from executor.truenas import NasClient, NasFout

    vinger = fetch_fingerprint(NAS_HOST, nas.port)
    schrijf = frozenset({"app.redeploy", "pool.snapshot.create"})
    dataset = sorted(nas.datasets())[0]
    for methode, params, mag in (
        ("app.redeploy", ["my-house"], mag_app),
        ("pool.snapshot.create", [{"dataset": dataset, "name": "asm-proef"}], mag_snapshot),
    ):
        with NasClient(NAS_HOST, nas.port, vinger, allowed=schrijf, timeout=5) as client:
            client.login(sleutel)
            if mag:
                client.call(methode, *params)
            else:
                with pytest.raises(NasFout) as fout:
                    client.call(methode, *params)
                assert fout.value.code == "truenas_geen_toegang", methode


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
            "sleutel_niet_huidig",
        ),
        (
            {"truenas_sleutel": READ_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "vervangen"},
            400,
            "sleutel_niet_huidig",
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
        (
            {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": SNAP_KEY, "actie": "vervangen"},
            400,
            "schrijfrechten_onvolledig",
        ),
        ({"truenas_sleutel": WRITE_KEY, "actie": "vervangen"}, 422, "nieuwe_sleutel_ontbreekt"),
        ({"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY}, 422, "actie_onbekend"),
        ({"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "wissen"}, 422, "actie_onbekend"),
        ({"truenas_sleutel": "", "actie": "ontkoppelen"}, 422, "sleutel_ongeldig"),
        ({"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": "met spatie", "actie": "vervangen"}, 422, "sleutel_ongeldig"),
        ({"truenas_sleutel": "bestaat-niet-0123456789", "actie": "ontkoppelen"}, 400, "sleutel_niet_huidig"),
        ({"truenas_sleutel": READ_KEY, "actie": "ontkoppelen"}, 400, "sleutel_niet_huidig"),
    ],
    ids=[
        "bewijs_onbekend",
        "bewijs_alleen_lezen",
        "nieuw_alleen_lezen",
        "nieuw_onbekend",
        "nieuw_alleen_snapshot_write",
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
    for geheim in (WRITE_KEY, NEW_KEY, READ_KEY, SNAP_KEY):
        assert geheim not in r.text
    if code == "sleutel_niet_huidig":
        assert nas.logins == 0 and nas.calls == []  # een ander bewijs dan de huidige sleutel gaat nergens heen


# ------------------------------------------------------------------ BN-2 (a): alleen de huidige sleutel is bewijs
def _gestopt(hub: Hub) -> None:
    from executor.journal import Journal

    Journal(hub.settings.replay_db, hub.settings.secrets_dir).stop({"code": "staat_verschilt", "at": "nu"})


@pytest.mark.parametrize("bewijs", [NEW_KEY, SNAP_KEY], ids=["andere_schrijfsleutel", "alleen_snapshot_write"])
@pytest.mark.parametrize(
    ("actie", "extra", "stop"),
    [("ontkoppelen", {}, False), ("vervangen", {"nieuwe_sleutel": NEW_KEY}, False), ("vervangen", {}, True)],
    ids=["ontkoppelen", "vervangen", "vrijgeven"],
)
def test_beheer_neemt_alleen_de_huidige_sleutel_als_bewijs(
    hub: Hub, nas: FakeTrueNAS, bewijs: str, actie: str, extra: dict[str, str], stop: bool
) -> None:
    """R-VEILIG-2, BN-2 (a): een andere geldige schrijfsleutel of een sleutel met alleen SNAPSHOT_WRITE is geen bewijs,
    ook al zou TrueNAS hem accepteren. Vaste melding, niets naar TrueNAS, niets veranderd (naslink.json byte-gelijk,
    gekoppeld, gestopt blijft gestopt)."""
    set_write_key(hub, nas)
    if stop:
        _gestopt(hub)
    voor = naslink_file(hub).read_bytes()
    c = hub_client(hub)
    r = post(c, BEHEER, {"truenas_sleutel": bewijs, "actie": actie, **extra})
    assert r.status_code == 400 and code_van(r) == "sleutel_niet_huidig" and 'role="alert"' in r.text, r.text
    assert naslink_file(hub).read_bytes() == voor and nas.logins == 0 and nas.calls == []
    st = status(c)
    assert st["gekoppeld"] is True and st["schrijfsleutel"]["laatste4"] == WRITE_KEY[-4:]
    assert (st["gestopt"] is not None) is stop
    assert NasLinkStore(hub.settings.secrets_dir).api_key() == WRITE_KEY
    assert bewijs not in r.text and WRITE_KEY not in r.text
    # Tegenproef: met de huidige sleutel lukt dezelfde actie wel.
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "actie": actie, **extra})
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("vault", ["weg", "nieuw"])
def test_beheer_met_onleesbare_vault_key_verandert_niets(hub: Hub, nas: FakeTrueNAS, vault: str) -> None:
    """BN-2 (a): zonder bruikbare vault.key is de huidige sleutel niet te openen, dus is er geen bewijs: vaste melding,
    niets naar TrueNAS, naslink.json byte-gelijk. Het formulier komt uit een tabblad van vóór het verlies."""
    set_write_key(hub, nas)
    c = hub_client(hub)
    formuliercode = csrf(c)
    assert formuliercode
    (hub.settings.secrets_dir / "vault.key").unlink()
    if vault == "nieuw":
        assert ensure_secrets(hub.settings.secrets_dir) == ["vault.key"]
    voor = naslink_file(hub).read_bytes()
    for actie in ("ontkoppelen", "vervangen"):
        r = c.post(
            BEHEER,
            data={"csrf": formuliercode, "truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": actie},
            headers={"Origin": BASE},
        )
        assert r.status_code == 409 and code_van(r) == "sleutelopslag_onleesbaar", r.text
    assert naslink_file(hub).read_bytes() == voor and nas.logins == 0 and nas.calls == []
    assert status(c)["gekoppeld"] is True


def test_huidige_sleutel_ingetrokken_in_truenas_verandert_niets(hub: Hub, nas: FakeTrueNAS) -> None:
    """BN-2 (a): het bewijs is de huidige sleutel én een geslaagde live test. Is die sleutel in TrueNAS ingetrokken, dan
    weigert TrueNAS hem en verandert er niets; vervangen kan dan niet meer (herinstallatie met een nieuwe datamap)."""
    set_write_key(hub, nas)
    del nas.keys[WRITE_KEY]
    voor = naslink_file(hub).read_bytes()
    c = hub_client(hub)
    for actie in ("vervangen", "ontkoppelen"):
        r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": actie})
        assert r.status_code == 400 and code_van(r) == "sleutel_geweigerd", r.text
    assert naslink_file(hub).read_bytes() == voor and nas.logins == 2
    assert status(c)["gekoppeld"] is True


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


def _niet_bruikbaar(hub: Hub, nas: FakeTrueNAS, c: TestClient) -> None:
    """Gemeenschappelijke verwachting bij een sleutelopslag die niet te gebruiken is: status en pagina zeggen
    sleutelopslag_onleesbaar, geen sleutel- of beheerformulier, nooit "Gezond", uitvoeren 503 en niets naar TrueNAS."""
    st = status(c)
    assert st["schrijfsleutel"]["onleesbaar"] is True and st["schrijfsleutel"]["ingesteld"] is False, st
    assert st["uitvoeren"] == {"mogelijk": False, "reden": "sleutelopslag_onleesbaar"}
    pagina = c.get("/").text
    assert "<code>sleutelopslag_onleesbaar</code>" in pagina and TOTAAL_GEZOND not in pagina
    assert 'action="/schrijfsleutel"' not in pagina and 'action="/beheer"' not in pagina
    r = execute(c, hub, restart_request(hub, nas))
    assert r.status_code == 503 and r.json()["code"] == "schrijfsleutel_onleesbaar", r.text
    assert nas.logins == 0 and nas.mutations == []


def test_vault_key_kwijt_na_herstart_is_onleesbaar_en_niet_gezond(hub: Hub, nas: FakeTrueNAS) -> None:
    """R-TECH-2: na het verlies van vault.key maakt de start (ensure_secrets) een nieuwe; de opgeslagen sleutel is
    daarmee niet te openen. Status en pagina zeggen dat (nooit "Gezond" of "uitvoeren mogelijk") en het bestand blijft
    ongewijzigd."""
    set_write_key(hub, nas)
    c = hub_client(hub)
    assert TOTAAL_GEZOND in c.get("/").text and status(c)["uitvoeren"]["mogelijk"] is True  # tegenproef
    voor = naslink_file(hub).read_bytes()
    (hub.settings.secrets_dir / "vault.key").unlink()
    assert ensure_secrets(hub.settings.secrets_dir) == ["vault.key"]
    _niet_bruikbaar(hub, nas, hub_client(hub))
    assert naslink_file(hub).read_bytes() == voor


class _AndereEigenaar:
    """``os`` voor executor.naslink, waarin de eigen gebruiker een andere is: het bestand is dan van een ander."""

    def __getattr__(self, naam: str) -> Any:
        return getattr(os, naam)

    @staticmethod
    def geteuid() -> int:
        return os.geteuid() + 1


@pytest.mark.parametrize(
    "soort", ["0644", "symlink", "andere_eigenaar", "schema_2", "sleutel_zonder_adres", "sleutel_zonder_vingerafdruk"]
)
def test_sleutelopslag_met_verkeerde_rechten_eigenaar_of_inhoud_is_onleesbaar(
    hub: Hub, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch, soort: str
) -> None:
    """R-TECH-3, V-045: naslink.json met rechten voor groep of anderen, als symlink (ook naar een geldig bestand), van
    een andere eigenaar, met een andere hoofdversie, of met een sleutel zonder adres of vingerafdruk is onleesbaar.
    Geen formulier, uitvoeren 503, en het bestand (en een doel van de symlink) blijft byte-gelijk."""
    import executor.naslink as naslink_mod

    set_write_key(hub, nas)
    pad = naslink_file(hub)
    if soort == "0644":
        pad.chmod(0o644)
    elif soort == "symlink":
        doel = hub.settings.secrets_dir / "elders.json"
        doel.write_bytes(pad.read_bytes())
        doel.chmod(0o600)
        pad.unlink()
        pad.symlink_to(doel)
    elif soort == "andere_eigenaar":
        monkeypatch.setattr(naslink_mod, "os", _AndereEigenaar())
    else:
        data = json.loads(pad.read_text())
        if soort == "schema_2":
            data["schema_version"] = "2.0"
        else:
            data["host" if soort == "sleutel_zonder_adres" else "fingerprint"] = None
        pad.write_text(json.dumps(data))
        pad.chmod(0o600)
    voor = pad.read_bytes()
    doel_voor = os.readlink(pad) if pad.is_symlink() else None
    _niet_bruikbaar(hub, nas, hub_client(hub))
    assert pad.read_bytes() == voor and (os.readlink(pad) if pad.is_symlink() else None) == doel_voor


@pytest.mark.parametrize("moment", ["stap1", "stap2", "vervangen", "ontkoppelen"])
def test_opslag_niet_schrijfbaar_geeft_een_vaste_melding(hub: Hub, nas: FakeTrueNAS, moment: str) -> None:
    """R-TECH-4, V-041: een schijf- of rechtenfout in /appdata/secrets geeft een vaste code met Nederlandse melding
    (rol alert), nooit een kale 500; de opgeslagen gegevens blijven zoals ze waren."""
    c = hub_client(hub)
    if moment == "stap2":
        assert post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY}).status_code == 200  # stap 1
    elif moment in ("vervangen", "ontkoppelen"):
        set_write_key(hub, nas)
    velden = (
        {"truenas_sleutel": WRITE_KEY}
        if moment.startswith("stap")
        else {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": moment}
    )
    pad = SLEUTEL if moment.startswith("stap") else BEHEER
    geheimen = hub.settings.secrets_dir
    voor = {p.name: p.read_bytes() for p in geheimen.iterdir() if p.is_file()}
    formuliercode = csrf(c)
    geheimen.chmod(0o500)
    try:
        r = c.post(pad, data={"csrf": formuliercode, **velden}, headers={"Origin": BASE})
    finally:
        geheimen.chmod(0o700)
    assert r.status_code == 503 and code_van(r) == "sleutelopslag_niet_schrijfbaar", r.text
    assert 'role="alert"' in r.text and "Internal Server Error" not in r.text
    assert {p.name: p.read_bytes() for p in geheimen.iterdir() if p.is_file()} == voor


def test_wedloop_met_een_ander_tabblad_geeft_sleutel_al_ingesteld(
    hub: Hub, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-TECH-9: is de sleutel net in een ander tabblad ingesteld (tijdens stap 1 of tijdens de live test van stap 2),
    dan krijgt dit tabblad 409 sleutel_al_ingesteld, niet de melding over een onleesbare opslag. Niets overschreven."""
    from executor.naslink import NasLinkConflict

    echte_vingerafdruk, echte_test = executor_app.fetch_fingerprint, executor_app.verify_key

    def stap1_terwijl_elders_ingesteld(host: str, port: int, *, timeout: float = 5.0) -> str:
        set_write_key(hub, nas)
        return echte_vingerafdruk(host, port, timeout=timeout)

    monkeypatch.setattr(executor_app, "fetch_fingerprint", stap1_terwijl_elders_ingesteld)
    c = hub_client(hub)
    r = post(c, SLEUTEL, {"truenas_sleutel": NEW_KEY})
    assert r.status_code == 409 and code_van(r) == "sleutel_al_ingesteld", r.text
    assert NasLinkStore(hub.settings.secrets_dir).api_key() == WRITE_KEY

    # Stap 2: tijdens de live test stelt een ander tabblad de sleutel in.
    naslink_file(hub).unlink()
    monkeypatch.setattr(executor_app, "fetch_fingerprint", echte_vingerafdruk)

    def stap2_terwijl_elders_ingesteld(*args: Any, **kwargs: Any) -> Any:
        uitkomst = echte_test(*args, **kwargs)
        set_write_key(hub, nas)
        return uitkomst

    monkeypatch.setattr(executor_app, "verify_key", stap2_terwijl_elders_ingesteld)
    c = hub_client(hub)
    assert post(c, SLEUTEL, {"truenas_sleutel": NEW_KEY}).status_code == 200  # stap 1
    r = post(c, SLEUTEL, {"truenas_sleutel": NEW_KEY})
    assert r.status_code == 409 and code_van(r) == "sleutel_al_ingesteld", r.text
    assert NasLinkStore(hub.settings.secrets_dir).api_key() == WRITE_KEY  # de sleutel van het andere tabblad blijft

    # Op het niveau van de opslag: een logische weigering, geen "onleesbaar".
    store = NasLinkStore(hub.settings.secrets_dir)
    with pytest.raises(NasLinkConflict):
        store.set_pending(NAS_HOST, nas.port, "ab" * 32)
    with pytest.raises(NasLinkConflict):
        store.save_key(NAS_HOST, nas.port, "ab" * 32, NEW_KEY, ["FULL_ADMIN"])


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


# ------------------------------------------------------------------ V-094: de sleutel staat in geen enkele logregel
ONBEKEND = "bestaat-niet-0123456789"


def test_sleutel_staat_in_geen_enkele_logregel(
    hub: Hub, nas: FakeTrueNAS, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    """V-094: de hele levensloop van de sleutel (geweigerd, instellen, uitvoeren, vervangen, ontkoppelen), met elke
    logger op INFO (ook httpx, websockets en de fake TrueNAS), de eigen loggers van de executor op DEBUG en de uitvoer
    op stdout/stderr van het proces. Geen van de gebruikte sleutels staat in een logregel, in de argumenten van een
    logrecord of in de procesuitvoer.

    Bewust niet op DEBUG voor bibliotheken: websockets logt op DEBUG elk frame, dus ook de aanmelding met de sleutel.
    De dienst zet die logger nooit op DEBUG (uvicorn configureert alleen zijn eigen loggers, ook bij
    ``EXECUTOR_LOG_LEVEL=debug``); dat bewaakt de test hierna."""
    caplog.set_level(logging.INFO)
    caplog.set_level(logging.DEBUG, logger="executor")
    c = hub_client(hub)
    assert post(c, SLEUTEL, {"truenas_sleutel": READ_KEY}).status_code == 200  # stap 1
    assert code_van(post(c, SLEUTEL, {"truenas_sleutel": READ_KEY})) == "schrijfrechten_ontbreken"
    assert code_van(post(c, SLEUTEL, {"truenas_sleutel": ONBEKEND})) == "sleutel_geweigerd"
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and "getest en opgeslagen" in r.text, r.text
    assert execute(c, hub, restart_request(hub, nas)).status_code == 200  # de executor meldt zich aan met de sleutel
    c = hub_client(hub)  # nieuwe app-instantie: de pogingenlimiet (5 per kwartier) telt per instantie
    assert code_van(post(c, BEHEER, {"truenas_sleutel": ONBEKEND, "actie": "ontkoppelen"})) == "sleutel_niet_huidig"
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "vervangen"})
    assert r.status_code == 200 and "De schrijfsleutel is vervangen." in r.text, r.text
    r = post(c, BEHEER, {"truenas_sleutel": NEW_KEY, "actie": "ontkoppelen"})
    assert r.status_code == 200 and "Ontkoppeld van de Hub." in r.text, r.text
    assert nas.logins >= 5

    # Ondergrens (V-003): de pogingen zijn echt gelogd, anders bewijst "staat er niet in" niets.
    regels = [rec.getMessage() for rec in caplog.records]
    codes = ("schrijfrechten_ontbreken", "sleutel_geweigerd", "sleutel_niet_huidig", "sleutel_ingesteld", "vervangen")
    for code in (*codes, "ontkoppeld"):
        assert any(f"code={code} trace_id=" in regel for regel in regels), code
    uit, fout = capfd.readouterr()
    teksten = [caplog.text, uit, fout, *regels, *(repr(rec.args) for rec in caplog.records)]
    for geheim in (WRITE_KEY, NEW_KEY, READ_KEY, ONBEKEND):
        for tekst in teksten:
            assert geheim not in tekst, tekst


def test_dienst_zet_websockets_nooit_op_debug(tmp_path: Path) -> None:
    """Hoort bij de test hierboven: ``python -m executor api`` (``__main__.main``, met elk toegestaan
    ``EXECUTOR_LOG_LEVEL``) configureert uvicorn en laadt de app zonder dat websockets DEBUG-records maakt (daarin zou
    het aanmeldframe met de sleutel staan). ``uvicorn.run`` wordt vervangen door alleen configureren en laden; in een
    apart proces, zodat de logconfiguratie van deze testsessie niet verandert."""
    niveaus = typing.get_args(Settings.model_fields["log_level"].annotation)
    assert "debug" in niveaus
    code = (
        "import logging, sys, uvicorn\n"
        "from uvicorn.config import Config\n"
        "def alleen_laden(app, **kw):\n"
        "    c = Config(app, **kw)\n"
        "    c.load()\n"
        "    print('geladen', any(logging.getLogger(n).isEnabledFor(logging.DEBUG)"
        " for n in ('websockets', 'websockets.client')))\n"
        "uvicorn.run = alleen_laden\n"
        "from executor.__main__ import main\n"
        "sys.exit(main(['api']))\n"
    )
    for niveau in niveaus:
        env = {**os.environ, "EXECUTOR_DATA_DIR": str(tmp_path / niveau), "EXECUTOR_LOG_LEVEL": niveau}
        uit = subprocess.run(  # noqa: S603 - vaste argumentlijst (deze Python en de code hierboven), geen shell
            [sys.executable, "-c", code], capture_output=True, text=True, check=False, timeout=60, env=env
        )
        assert uit.returncode == 0 and uit.stdout.strip() == "geladen False", (niveau, uit.stdout, uit.stderr)


def _delen(sleutel: str, lengte: int = 8) -> set[str]:
    """Elk stuk van ``lengte`` tekens uit de sleutel (websockets kort een frame in het midden in en laat de staart
    staan)."""
    return {sleutel[i : i + lengte] for i in range(len(sleutel) - lengte + 1)}


def test_sleutel_ook_met_root_op_debug_in_geen_enkele_logregel(
    hub: Hub, nas: FakeTrueNAS, caplog: pytest.LogCaptureFixture, capfd: pytest.CaptureFixture[str]
) -> None:
    """R-VEILIG-4: met de root-logger (en dus elke logger die zijn niveau erft, ook ``websockets``) op DEBUG doorloopt
    de sleutel zijn hele levensloop (geweigerd, instellen, uitvoeren, vervangen, ontkoppelen). Geen stuk van 8 tekens
    of meer van een gebruikte sleutel staat in een logregel, in de argumenten van een logrecord of op stdout/stderr. De
    verbinding van de executor (en die van de nep-TrueNAS) logt via een eigen logger vast op INFO."""
    caplog.set_level(logging.DEBUG)
    for naam in ("websockets", "websockets.client", "websockets.server", "executor"):
        caplog.set_level(logging.DEBUG, logger=naam)
    c = hub_client(hub)
    assert post(c, SLEUTEL, {"truenas_sleutel": READ_KEY}).status_code == 200  # stap 1
    assert code_van(post(c, SLEUTEL, {"truenas_sleutel": READ_KEY})) == "schrijfrechten_ontbreken"
    assert code_van(post(c, SLEUTEL, {"truenas_sleutel": ONBEKEND})) == "sleutel_geweigerd"
    r = post(c, SLEUTEL, {"truenas_sleutel": WRITE_KEY})
    assert r.status_code == 200 and "getest en opgeslagen" in r.text, r.text
    assert execute(c, hub, restart_request(hub, nas)).status_code == 200
    c = hub_client(hub)  # nieuwe app-instantie: de pogingenlimiet telt per instantie
    r = post(c, BEHEER, {"truenas_sleutel": WRITE_KEY, "nieuwe_sleutel": NEW_KEY, "actie": "vervangen"})
    assert r.status_code == 200 and "De schrijfsleutel is vervangen." in r.text, r.text
    r = post(c, BEHEER, {"truenas_sleutel": NEW_KEY, "actie": "ontkoppelen"})
    assert r.status_code == 200 and "Ontkoppeld van de Hub." in r.text, r.text
    assert nas.logins >= 5

    # Ondergrens (V-003): er is echt op DEBUG gelogd en de pogingen staan erin.
    assert any(rec.levelno == logging.DEBUG for rec in caplog.records)
    assert any("code=sleutel_ingesteld trace_id=" in rec.getMessage() for rec in caplog.records)
    uit, fout = capfd.readouterr()
    teksten = [caplog.text, uit, fout, *(rec.getMessage() for rec in caplog.records)]
    teksten += [repr(rec.args) for rec in caplog.records]
    for geheim in (WRITE_KEY, NEW_KEY, READ_KEY, ONBEKEND):
        for deel in _delen(geheim):
            for tekst in teksten:
                assert deel not in tekst, (deel, tekst[:300])


def test_dienst_logt_elke_poging_in_de_app_log(tmp_path: Path) -> None:
    """R-VEILIG-3, contract §3.7/§3.9 (Log): de dienst zoals ``python -m executor api`` hem start (uvicorn met de
    logconfiguratie van ``__main__``) schrijft bij elke afgehandelde poging één regel met code en trace-ID naar de
    app-log (stdout), zonder geheimen. In een apart proces: ``uvicorn.run`` laadt de app zoals uvicorn dat doet en doet
    twee pogingen met een testclient."""
    code = (
        "import re, sys, uvicorn\n"
        "from uvicorn.config import Config\n"
        "def proef(app, **kw):\n"
        "    c = Config(app, **kw)\n"
        "    c.load()\n"
        "    from fastapi.testclient import TestClient\n"
        "    t = TestClient(c.loaded_app, base_url='http://executor.local')\n"
        "    r1 = t.post('/koppelen', data={'x': '1'})\n"
        '    m = re.search(r\'name="csrf" value="([^"]+)"\', t.get(\'/\').text)\n'
        "    r2 = t.post('/schrijfsleutel', data={'csrf': m.group(1), 'truenas_sleutel': sys.argv[1]},\n"
        "                headers={'Origin': 'http://executor.local'})\n"
        "    print('pogingen', r1.status_code, r2.status_code, flush=True)\n"
        "uvicorn.run = proef\n"
        "from executor.__main__ import main\n"
        "sys.exit(main(['api']))\n"
    )
    for niveau in ("info", "warning"):
        env = {**os.environ, "EXECUTOR_DATA_DIR": str(tmp_path / niveau), "EXECUTOR_LOG_LEVEL": niveau}
        uit = subprocess.run(  # noqa: S603 - vaste argumentlijst (deze Python en de code hierboven), geen shell
            [sys.executable, "-c", code, WRITE_KEY], capture_output=True, text=True, check=False, timeout=60, env=env
        )
        assert uit.returncode == 0 and "pogingen 403 409" in uit.stdout, (niveau, uit.stdout, uit.stderr)
        alles = uit.stdout + uit.stderr
        assert re.search(r"code=herkomst_onjuist trace_id=[0-9a-f-]{36}", uit.stdout), (niveau, alles)
        assert re.search(r"code=niet_gekoppeld trace_id=[0-9a-f-]{36}", uit.stdout), (niveau, alles)
        for deel in _delen(WRITE_KEY):
            assert deel not in alles, (niveau, deel)


# ------------------------------------------------------------------ V-093: geen melding uit de URL
GEKOZEN = {
    "code": "koppelstatus_onleesbaar",
    "fout": "zelfgekozen-fout",
    "melding": "<b>zelfgekozen-melding</b>",
    "titel": "zelfgekozen-titel",
    "tekst": "zelfgekozen-tekst",
    "trace_id": "zelfgekozen-trace",
    "rol": "alert",
    "toon": "fout",
    "pad": "/zelfgekozen-pad",
}


def _zonder_formuliercode(tekst: str) -> str:
    return re.sub(r'name="csrf" value="[^"]+"', 'name="csrf" value=""', tekst)


@pytest.mark.parametrize("sleutel", ["niet_ingesteld", "ingesteld", "gestopt"])
def test_geen_melding_uit_een_zelfgekozen_queryparameter(hub: Hub, nas: FakeTrueNAS, sleutel: str) -> None:
    """V-093: GET / met zelfgekozen queryparameters toont geen melding en weerspiegelt niets; de pagina is (op de
    nieuwe formuliercode na) gelijk aan die zonder queryparameters."""
    if sleutel != "niet_ingesteld":
        set_write_key(hub, nas)
    if sleutel == "gestopt":
        from executor.journal import Journal

        Journal(hub.settings.replay_db, hub.settings.secrets_dir).stop({"code": "staat_verschilt", "at": "nu"})
    c = hub_client(hub)
    schoon = c.get("/")
    assert schoon.status_code == 200 and code_van(schoon) is None and 'role="alert"' not in schoon.text
    r = c.get("/", params=GEKOZEN)
    assert r.status_code == 200 and str(r.request.url.query)  # de parameters zijn echt meegestuurd
    assert code_van(r) is None and 'role="alert"' not in r.text and 'role="status"' not in r.text
    assert "zelfgekozen" not in r.text and "zelfgekozen" not in unescape(r.text)
    assert _zonder_formuliercode(r.text) == _zonder_formuliercode(schoon.text)
    assert nas.calls == []
