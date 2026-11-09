"""Dienst-E2E: centrale appcatalogus (B01-002) tegen de fake TrueNAS en een fake appstore (Sim-getest, geen NAS).

Acceptatie B01-002: na een NAS-herstart blijft de app-identiteit gelijk; een offline app/NAS krijgt een
verouderde tijdstempel en is nooit gezond. Bestaande apps (MediaGuard, MSO, my_house) verschijnen zonder installatie of
mutatie; de koppeling met de appstore loopt via het dienstenregister (anders ``unknown``).
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from conftest import enroll_body, idem, login_as, make_user
from fakes.fake_appstore import FakeAppstore, entry
from fakes.fake_truenas import FakeTrueNAS, _app
from nashelpers import connect, refresh

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def _apps(admin: Any, **params: Any) -> dict[str, dict[str, Any]]:
    r = admin.get("/api/v1/apps", params={"limit": 200, **params})
    assert r.status_code == 200, r.text
    return {a["runtime_id"]: a for a in r.json()["items"]}


def _digest(ref: str) -> str:
    return "sha256:" + hashlib.sha256(ref.encode()).hexdigest()


def test_catalogus_ontdekt_bestaande_apps_zonder_mutatie(admin: Any, fake_nas: FakeTrueNAS, worker_once: Any) -> None:
    connect(admin, fake_nas)
    done = refresh(admin, worker_once)
    assert done["status"] == "ok" and done["catalogus"]["nieuw"] == 4, done
    apps = _apps(admin)
    assert set(apps) == {"mediaguard", "media-source-optimizer", "my-house", "jellyfin"}

    mg = apps["mediaguard"]
    assert mg["adaptertype"] == "bestaand_mediaguard" and mg["soort"] == "bestaand"
    assert mg["installatiewijze"] == "custom_app"  # ix-app = standaard Custom App-formulier
    assert mg["eigenaar"]["repo"] == "lvos04/media-guard-ultimate"
    assert mg["image"] == {
        "repository": "ghcr.io/lvos04/mediaguard",
        "tag": "1.2.2",
        "digest": _digest("ghcr.io/lvos04/mediaguard:1.2.2"),
    }
    # RUNNING in TrueNAS is geen bewijs van gezond; de binnenkant van MediaGuard volgt in P3.
    assert mg["gezondheid"]["status"] == "unknown" and mg["gezondheid"]["reason_code"] == "binnenkant_niet_gebouwd"
    assert mg["deep_link"] == "http://127.0.0.1:30101/"
    assert apps["my-house"]["app_id"] == "my_house" and apps["my-house"]["adaptertype"] == "bestaand_my_house"
    jf = apps["jellyfin"]
    assert jf["installatiewijze"] == "catalog_app" and jf["soort"] == "derde"
    assert jf["gezondheid"]["status"] == "down" and jf["gezondheid"]["reason_code"] == "app_gestopt"

    r = admin.get(f"/api/v1/apps/{mg['id']}")
    assert r.status_code == 200 and r.headers["ETag"] == f'"{mg["versie_etag"]}"'
    d = r.json()
    assert d["datasets"] == ["testpool/apps/mediaguard"]
    assert d["images"][0]["digest_bron"] == "app.image.query" and d["images"][0]["readback"]["status"] == "ok"
    assert d["resourcegrenzen"]["status"] == "unknown" and d["resourcegrenzen"]["reden"] == "config_niet_gelezen"
    assert d["documentatie"].endswith("A18_MEDIAGUARD.md")
    assert d["catalogus"]["app"] == "ix-app" and d["catalogus"]["trein"] == "stable"
    acties = {a["id"]: a for a in d["acties"]}
    assert acties["openen"]["beschikbaar"] and not acties["herstarten"]["beschikbaar"]
    assert d["appstore"]["status"] == "unknown" and d["appstore"]["reden"] == "appstore_niet_gekoppeld"
    comps = {c["soort"]: c for c in d["gezondheid"]["componenten"]}
    assert comps["truenas"]["status"] == "healthy" and comps["truenas"]["staat"] == "RUNNING"

    # Zoeken en filteren.
    assert set(_apps(admin, q="optimizer")) == {"media-source-optimizer"}
    assert set(_apps(admin, status="down")) == {"jellyfin"}
    assert set(_apps(admin, soort="bestaand")) == {"mediaguard", "media-source-optimizer", "my-house"}
    assert admin.get("/api/v1/apps", params={"adaptertype": "verzonnen"}).status_code == 422

    # Alleen lezen: geen enkele schrijfmethode en nooit de app-configuratie (geheimen) opgehaald.
    assert fake_nas.mutations == []
    assert not [c for c in fake_nas.calls if c[0] == "app.query" and len(c[1]) > 1]


def test_identiteit_stabiel_na_nas_herstart_en_offline_nooit_gezond(
    admin: Any, fake_nas: FakeTrueNAS, worker_once: Any
) -> None:
    connect(admin, fake_nas)
    refresh(admin, worker_once)
    before = _apps(admin)
    ids = {rid: a["id"] for rid, a in before.items()}

    # Idempotent: opnieuw ontdekken verandert niets.
    r = admin.post("/api/v1/apps/discover", headers=idem())
    assert r.status_code == 200, r.text
    assert (r.json()["nieuw"], r.json()["bijgewerkt"], r.json()["ongewijzigd"]) == (0, 0, 4)

    # NAS offline: de inventaris mislukt, de catalogus blijft staan met de laatst-gezien-tijd, alles 'unknown'.
    fake_nas.offline()
    done = refresh(admin, worker_once)
    assert done["status"] == "unknown" and done["catalogus"]["status"] == "unknown"
    offline = _apps(admin)
    assert {rid: a["id"] for rid, a in offline.items()} == ids
    for a in offline.values():
        assert a["gezondheid"]["status"] == "unknown", a
        assert a["gezondheid"]["observed_at"] == before[a["runtime_id"]]["laatst_gezien"]
    assert offline["jellyfin"]["gezondheid"]["reason_code"] == "inventaris_verouderd"

    # "Herstart": NAS weer online, andere volgorde en uptime; zelfde identiteit per app.
    fake_nas.online()
    fake_nas.data["app.query"].reverse()
    fake_nas.data["system.info"]["uptime_seconds"] = 12
    refresh(admin, worker_once)
    after = _apps(admin)
    assert {rid: a["id"] for rid, a in after.items()} == ids

    # Nieuwe image-tag → bijgewerkt + geschiedenis; zelfde identiteit.
    mg = next(a for a in fake_nas.data["app.query"] if a["name"] == "mediaguard")
    mg["active_workloads"]["images"] = ["ghcr.io/lvos04/mediaguard:1.2.3"]
    mg["active_workloads"]["container_details"][0]["image"] = "ghcr.io/lvos04/mediaguard:1.2.3"
    done = refresh(admin, worker_once)
    assert done["catalogus"]["bijgewerkt"] == 1
    d = admin.get(f"/api/v1/apps/{ids['mediaguard']}").json()
    assert [h["tag"] for h in d["image_historie"]] == ["1.2.2", "1.2.3"]
    assert d["image"]["digest"] is None  # niet in app.image.query → onbekend, nooit verzonnen
    assert d["images"][0]["readback"]["status"] == "unknown"

    # App verdwijnt uit TrueNAS: nooit verwijderd, wel 'niet aanwezig' en onbekend.
    removed = next(a for a in fake_nas.data["app.query"] if a["name"] == "my-house")
    fake_nas.data["app.query"].remove(removed)
    done = refresh(admin, worker_once)
    assert done["catalogus"]["verdwenen"] == 1
    assert "my-house" not in _apps(admin)
    gone = _apps(admin, alleen_aanwezig="false")["my-house"]
    assert gone["aanwezig"] is False and gone["verdwenen_sinds"] and gone["id"] == ids["my-house"]
    assert gone["gezondheid"]["reason_code"] == "niet_meer_in_inventaris"
    fake_nas.data["app.query"].append(removed)
    refresh(admin, worker_once)
    back = _apps(admin)["my-house"]
    assert back["aanwezig"] is True and back["id"] == ids["my-house"] and back["verdwenen_sinds"] is None
    assert fake_nas.mutations == []


def test_appstore_koppeling_via_dienstenregister(admin: Any, app: Any, fake_nas: FakeTrueNAS, worker_once: Any) -> None:
    connect(admin, fake_nas)
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "appstore-en-fork"})
    assert r.status_code == 201, r.text
    r = admin.post("/api/v1/services/enroll", json=enroll_body("appstore-en-fork", token=r.json()["enrollment_token"]))
    assert r.status_code == 200, r.text
    service_id = r.json()["service_id"]
    store = FakeAppstore(app.state.keyring().jwt_signing.public_key(), service_id=service_id).start()
    try:
        store.entries = [entry("mediaguard", "MediaGuard"), entry("jellyfin", "Jellyfin", install_method="catalog_app")]
        fake_nas.data["app.query"].append(
            _app(
                "appstore-en-fork",
                "RUNNING",
                "ghcr.io/lvos04/appstore-en-fork:0.1.0",
                store.port,
                30430,
                "/mnt/testpool/apps/appstore",
                "/appdata",
            )
        )
        done = refresh(admin, worker_once)
        assert done["appstore"]["status"] == "ok" and done["appstore"]["gekoppeld"] == 2, done
        assert store.rejected == [] and store.requests
        apps = _apps(admin)
        mg = admin.get(f"/api/v1/apps/{apps['mediaguard']['id']}").json()
        assert mg["appstore"]["status"] == "gekoppeld" and mg["appstore"]["laatste_versie"] == "1.0.0"
        assert apps["my-house"]["appstore_status"] == "niet_in_appstore"
        own = admin.get(f"/api/v1/apps/{apps['appstore-en-fork']['id']}").json()
        assert own["dienst"]["id"] == service_id and own["adaptertype"] == "eigen_dienst"

        # Appstore weg: koppeling onbekend, laatst bekende entry blijft zichtbaar als 'laatst_bekend'.
        store.offline()
        done = refresh(admin, worker_once)
        assert done["appstore"]["reden"] == "appstore_onbereikbaar"
        mg = admin.get(f"/api/v1/apps/{apps['mediaguard']['id']}").json()
        assert mg["appstore"]["status"] == "unknown" and mg["appstore"]["laatst_bekend"]["status"] == "gekoppeld"
    finally:
        store.stop()
    assert fake_nas.mutations == []


def test_kind_ziet_de_catalogus_niet_en_kijker_kan_niet_ontdekken(admin: Any, app: Any) -> None:
    make_user(admin, "kijker", "viewer")
    make_user(admin, "kleintje", "kind")
    viewer, kid = login_as(app, "kijker"), login_as(app, "kleintje")
    assert viewer.get("/api/v1/apps").status_code == 200
    assert kid.get("/api/v1/apps").status_code == 403
    assert viewer.post("/api/v1/apps/discover", headers=idem()).status_code == 403
