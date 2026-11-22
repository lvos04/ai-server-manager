"""Pre-update-gate en EX15 bij de executor (S-P2-050f; contract 1.3 §8; ADR-0032 besluit 8 optie 3).

Toestandstabel, één test per rij; bij elke weigering krijgt TrueNAS geen schrijfaanroep:

| rij | toestand                                             | uitkomst                          |
|-----|------------------------------------------------------|-----------------------------------|
| P1  | snapshot via /execute, daarna bijwerken met dat id   | 200, checkpoint gebruikt          |
| N1  | geen checkpoint (id onbekend bij deze executor)      | 409 checkpoint_ontbreekt          |
| N2  | checkpoint ouder dan een uur                         | 409 checkpoint_verlopen           |
| N2b | app na het checkpoint al bijgewerkt                  | 409 checkpoint_verlopen           |
| N3  | snapshot weg of andere createtxg ("hash wijkt af")   | 409 checkpoint_afwijkend          |
| N3b | checkpoint van een andere dataset (dekt de app niet) | 409 checkpoint_dekt_niet          |
| N4  | migratie gemeld, daarna terugzetten op alleen de tag | 409 database_herstel_vereist      |
| N4b | idem bij een catalogusrollback                       | 409 database_herstel_vereist      |
| N5  | herstelpunt zonder eigen herkomst en niet ``oud``    | 409 herkomst_onbekend             |
| N5b | eigen herkomst én ``oud`` (tegenstrijdig)            | 409 herkomst_onbekend             |
| N5c | eigen herkomst onleesbaar                            | 409 herkomst_onbekend             |
| P2  | recept van vóór F (``oud``) en ``buiten_keten``      | 200 met melding ``herkomst``      |
| H1  | schrijfbare koppeling alleen in de werklast          | 409 checkpoint_dekt_niet          |
| H1b | geen opslag zonder positief bewijs (regel zelf)      | onbekend = geen dekking           |
| H1c | database op een aangekoppelde kinddataset            | 409 checkpoint_dekt_niet          |
| H2  | recursief, kindsnapshot ontbreekt bij teruglezen     | 409 checkpoint_dekt_niet          |
| H2b | kindsnapshot na het checkpoint weg                   | 409 checkpoint_afwijkend          |
| H2c | checkpoint zonder voltooide eigen snapshotactie      | 409 checkpoint_ontbreekt          |
| P3  | recursief over ouder en kind, beide teruggelezen     | 200                               |
| H3  | opslag of snapshot verandert vlak vóór de schrijfactie | 409, nul app-schrijfaanroepen   |
| H4  | recept schrijft naar een ongedekte dataset           | 409 checkpoint_dekt_niet          |
| H5  | app.update terug naar de image van vóór een migratie | 409 database_herstel_vereist      |
| H5b | app.update terug naar de catalogusversie ervóór      | 409 database_herstel_vereist      |
| H6  | ouder journaal teruggezet (anker in de geheimenmap)  | 409 herkomst_onbekend (ook catalogusrollback) |

Gemarkeerde instantie zonder recept (kluisplekken_recept_ontbreekt) staat in ``test_kluismarkering.py``; de
kijkersrol bij de Hub in ``tests/e2e/test_acties.py``.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
from asm_policy import checkpoint as cpmod
from asm_policy.etag import ABSENT, app_etag, dataset_etag
from executorhelpers import Hub, approved, checkpoint, execute, nas_hub, set_write_key, signed, write_nas
from executorhelpers import client as hub_client
from fakes.fake_truenas import FakeTrueNAS, _app, default_data
from fastapi.testclient import TestClient
from policyhelpers import DIGEST_B, HOST, install_params, proposal

from executor.journal import Journal, JournalUnavailable

REPO = "ghcr.io/voorbeeld/demo-app"
Stack = tuple[Hub, TestClient, FakeTrueNAS]


@pytest.fixture
def stack(tmp_path: Path) -> Any:
    nas = write_nas().start()
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    yield hub, hub_client(hub), nas
    nas.stop()


def writes(nas: FakeTrueNAS) -> list[str]:
    return [m for m in nas.mutations if m != "app.config"]


def app_prop(nas: FakeTrueNAS, action: str, name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return proposal(
        action,
        {"host_id": HOST, "app_id": name},
        parameters,
        expected_version=app_etag(nas.app(name), nas.data["app.image.query"]),
    )


def bijwerken(nas: FakeTrueNAS, tag: str = f"1.2.4@{DIGEST_B}", **extra: Any) -> dict[str, Any]:
    return app_prop(nas, "app.update", "demo-app", {"image": {"repository": REPO, "tag": tag}, **extra})


def installeer(hub: Hub, c: TestClient) -> None:
    prop = proposal(
        "app.install", {"host_id": HOST, "app_id": "demo-app"}, install_params("demo-app"), expected_version=ABSENT
    )
    assert execute(c, hub, approved(hub, prop)).status_code == 200


def snapshot(
    hub: Hub, c: TestClient, dataset: str = "testpool/apps", naam: str = "voor-update", recursief: bool = True
) -> str:
    prop = proposal(
        "zfs.snapshot.create",
        {"host_id": HOST, "dataset": dataset},
        {"naam": naam, "recursief": recursief},
        expected_version=dataset_etag(dataset),
    )
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 200 and r.json()["waarschuwingen"] == [], r.text
    return str(r.json()["request_id"])


def weigering(r: Any, code: str) -> dict[str, Any]:
    assert r.status_code == 409 and r.json()["code"] == code, r.text
    return dict(r.json())


def journaal(hub: Hub) -> Journal:
    return Journal(hub.settings.replay_db, hub.settings.secrets_dir)


def test_p1_snapshot_via_de_echte_route_en_daarna_bijwerken(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    cp = snapshot(hub, c)
    assert journaal(hub).checkpoint(cp) is not None
    r = execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp))
    assert r.status_code == 200, r.text
    assert writes(nas) == ["app.create", "pool.snapshot.create", "app.update"]


def test_n1_zonder_checkpoint_geen_bijwerken(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    weigering(
        execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=str(uuid.uuid4()))), "checkpoint_ontbreekt"
    )
    assert writes(nas) == ["app.create"] and nas.updated == []


def test_n2_verlopen_checkpoint(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    cp = checkpoint(hub)
    with sqlite3.connect(hub.settings.replay_db) as conn:
        conn.execute("UPDATE checkpoint SET created_at = ? WHERE request_id = ?", (int(time.time()) - 3601, cp))
    d = weigering(execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)), "checkpoint_verlopen")
    assert d["details"]["leeftijd_seconden"] >= 3601
    assert nas.updated == []


def test_n2b_checkpoint_van_voor_de_vorige_bijwerking_is_verouderd(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    cp = checkpoint(hub)
    assert execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)).status_code == 200
    r = execute(c, hub, approved(hub, bijwerken(nas, f"1.2.5@{DIGEST_B}"), backup_checkpoint_id=cp))
    weigering(r, "checkpoint_verlopen")
    assert len(nas.updated) == 1


@pytest.mark.parametrize("soort", ["weg", "andere_createtxg"])
def test_n3_snapshot_weg_of_anders(stack: Stack, soort: str) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    cp = checkpoint(hub, snapshot="testpool/apps@bestaat-niet") if soort == "weg" else checkpoint(hub, createtxg="999")
    weigering(execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)), "checkpoint_afwijkend")
    assert nas.updated == []


def test_n3b_checkpoint_van_een_andere_dataset_dekt_niet(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    cp = snapshot(hub, c, dataset="testpool/photos")
    d = weigering(execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)), "checkpoint_dekt_niet")
    assert d["details"]["datasets"] == ["testpool/apps"]
    assert nas.updated == []


def test_n4_na_een_migratie_geen_terugzetten_op_alleen_de_tag(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    up = approved(hub, bijwerken(nas, upgrade={"migrations": True, "tag_only_rollback_safe": False}))
    assert execute(c, hub, up).status_code == 200
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": up["approval"]["request_id"]})
    d = weigering(execute(c, hub, approved(hub, terug)), "database_herstel_vereist")
    assert d["details"]["checkpoints"] == [up["approval"]["backup_checkpoint_id"]]
    assert len(nas.updated) == 1


def test_n4b_catalogusrollback_na_een_migratie(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app(
            "immich",
            "RUNNING",
            "ghcr.io/immich-app/server:1.0.0",
            2283,
            2283,
            "/mnt/testpool/apps/immich",
            "/d",
            catalog_app="immich",
        )
    )
    van = str(nas.app("immich")["version"])
    up = app_prop(nas, "app.update", "immich", {"catalog_version": "1.0.1", "upgrade": {"migrations": True}})
    assert execute(c, hub, approved(hub, up)).status_code == 200
    terug = app_prop(nas, "app.rollback", "immich", {"catalog_version": van})
    weigering(execute(c, hub, approved(hub, terug)), "database_herstel_vereist")
    assert not any(m == "app.rollback" for m, _p in nas.calls)


def test_n5_herstelpunt_zonder_eigen_herkomst_van_na_f(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    j = journaal(hub)
    j.oud_vastlegging()  # ingebruikname van F: nog geen recepten
    los = str(uuid.uuid4())
    j.save_values(los, "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": los})
    weigering(execute(c, hub, approved(hub, terug)), "herkomst_onbekend")
    assert nas.updated == []


def test_n5b_eigen_herkomst_en_ook_oud_is_tegenstrijdig(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    j = journaal(hub)
    r = str(uuid.uuid4())
    j.save_values(r, "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    assert len(j.oud_vastlegging()) == 1
    j.leg_herkomst_vast(r, "demo-app", {"herkomst": "buiten_keten", "migratie": False})
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": r})
    weigering(execute(c, hub, approved(hub, terug)), "herkomst_onbekend")
    assert nas.updated == []


def test_n5c_onleesbare_eigen_herkomst(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    up = approved(hub, bijwerken(nas))
    assert execute(c, hub, up).status_code == 200
    with sqlite3.connect(hub.settings.replay_db) as conn:
        conn.execute("UPDATE recept_herkomst SET box = '{}'")
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": up["approval"]["request_id"]})
    weigering(execute(c, hub, approved(hub, terug)), "herkomst_onbekend")
    assert len(nas.updated) == 1


def test_p2_oud_en_buiten_keten_gaan_door_met_melding(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    j = journaal(hub)
    oud = str(uuid.uuid4())
    j.save_values(oud, "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    with sqlite3.connect(hub.settings.replay_db) as conn:
        voor = conn.execute("SELECT app, box, created_at FROM app_values WHERE request_id = ?", (oud,)).fetchone()
    # Bijwerken buiten de keten (zonder upgradecontext) maakt een recept met eigen herkomst.
    up = approved(hub, bijwerken(nas, f"1.2.5@{DIGEST_B}"))
    assert execute(c, hub, up).status_code == 200
    # Een herstart legt niets opnieuw vast; het recept van vóór F blijft byte-gelijk.
    assert journaal(hub).oud_vastlegging() == {(oud, "demo-app", voor[2])}
    with sqlite3.connect(hub.settings.replay_db) as conn:
        na = conn.execute("SELECT app, box, created_at FROM app_values WHERE request_id = ?", (oud,)).fetchone()
    assert na == voor
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": up["approval"]["request_id"]})
    r = execute(c, hub, approved(hub, terug))
    assert r.status_code == 200 and r.json()["herkomst"] == "buiten_keten", r.text
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": oud})
    r = execute(c, hub, approved(hub, terug))
    assert r.status_code == 200 and r.json()["herkomst"] == "oud", r.text
    assert nas.updated[-1][1]["values"]["image"]["tag"] == f"1.2.4@{DIGEST_B}"


def test_verlies_van_de_oud_vastlegging_wordt_nooit_opnieuw_geinventariseerd(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    j = journaal(hub)
    oud = str(uuid.uuid4())
    j.save_values(oud, "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    j.oud_vastlegging()
    with sqlite3.connect(hub.settings.replay_db) as conn:
        conn.execute("DELETE FROM state WHERE key = 'oud_vastlegging'")
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": oud})
    weigering(execute(c, hub, approved(hub, terug)), "herkomst_onbekend")
    # Een recept met eigen herkomst blijft wel bruikbaar (bijwerken en terugzetten).
    up = approved(hub, bijwerken(nas, f"1.2.5@{DIGEST_B}"))
    assert execute(c, hub, up).status_code == 200
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": up["approval"]["request_id"]})
    assert execute(c, hub, approved(hub, terug)).status_code == 200


def test_snapshot_zonder_createtxg_telt_niet_als_checkpoint(stack: Stack) -> None:
    hub, c, nas = stack
    ds = "testpool/apps"
    origineel = nas._write

    def zonder_txg(method: str, params: list[Any]) -> Any:
        uit = origineel(method, params)
        for s in nas.data["snapshots"].get(ds, []):
            s.pop("createtxg", None)
        return uit

    nas._write = zonder_txg  # type: ignore[method-assign]
    prop = proposal(
        "zfs.snapshot.create", {"host_id": HOST, "dataset": ds}, {"naam": "x"}, expected_version=dataset_etag(ds)
    )
    r = execute(c, hub, signed(hub, prop, risk_class="R1"))
    assert r.status_code == 200 and r.json()["waarschuwingen"] == ["checkpoint_niet_vastgelegd"], r.text
    assert journaal(hub).checkpoint(str(r.json()["request_id"])) is None


# ------------------------------------------------------------------ R-HARDE-EIS-1 t/m 6 (herstelronde)
DS = "testpool/apps/demo-app"


def eigen_dataset(nas: FakeTrueNAS, *kinderen: str) -> None:
    nas.add_dataset(DS)
    for k in kinderen:
        nas.add_dataset(f"{DS}/{k}")


def test_h1_koppeling_alleen_in_de_werklast(stack: Stack) -> None:
    hub, c, nas = stack
    # my-house: app.config zonder opslag, de draaiende werklast koppelt testpool/apps/my_house.
    nieuw = {"image": {"repository": "ghcr.io/lvos04/my_house", "tag": f"0.2.0@{DIGEST_B}"}}
    prop = app_prop(nas, "app.update", "my-house", nieuw)
    d = weigering(execute(c, hub, approved(hub, prop)), "checkpoint_dekt_niet")
    assert d["details"]["datasets"] == ["testpool/apps/my_house"] and nas.updated == []


def test_h1b_geen_opslag_alleen_met_positief_bewijs() -> None:
    # Op de executor weigert de herkenning een gestopte app al eerder; hier de regel zelf (ook voor de Hub-kant).
    boom = default_data()["pool.dataset.query"]
    draait = {"containers": 1, "volumes": []}
    assert cpmod.app_datasets({"env": {}}, boom, "x", draait) == []
    assert cpmod.app_datasets({"env": {}}, boom, "x", {"containers": 0, "volumes": []}) is None
    assert cpmod.app_datasets({"env": {}}, boom, "x") is None
    ro = {"containers": 1, "volumes": [{"source": "/mnt/testpool/media", "type": "bind", "mode": "ro"}]}
    assert cpmod.app_datasets({}, boom, "x", ro) == []
    vreemd = {"containers": 1, "volumes": [{"source": "/var/lib/docker/x", "type": "volume", "mode": "rw"}]}
    assert cpmod.app_datasets({}, boom, "x", vreemd) is None
    # De te herstellen waarden (ook=) tellen mee: een bestemming buiten elk koppelpunt is onbekend.
    elders = {"storage": [{"type": "host_path", "host_path_config": {"path": "/nergens"}}]}
    assert cpmod.app_datasets({}, boom, "x", draait, ook=elders) is None


def test_h1c_database_op_een_kinddataset(stack: Stack) -> None:
    hub, c, nas = stack
    eigen_dataset(nas, "database")
    installeer(hub, c)
    cp = snapshot(hub, c, DS, "alleen-ouder", recursief=False)
    d = weigering(execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)), "checkpoint_dekt_niet")
    assert d["details"]["datasets"] == [DS, f"{DS}/database"] and nas.updated == []


def test_h2_recursief_zonder_teruggelezen_kindsnapshot(stack: Stack) -> None:
    hub, c, nas = stack
    eigen_dataset(nas, "database")
    installeer(hub, c)
    echt = nas._apply

    def zonder_kind(method: str, params: list[Any]) -> Any:
        uit = echt(method, params)
        if method.endswith(".snapshot.create"):
            nas.data["snapshots"][f"{DS}/database"].pop()  # TrueNAS meldt succes, de kindsnapshot is er niet
        return uit

    nas._apply = zonder_kind  # type: ignore[method-assign]
    cp = snapshot(hub, c, DS)
    nas._apply = echt  # type: ignore[method-assign]
    lid = journaal(hub).checkpoint(cp)
    assert lid is not None and set(lid["leden"]) == {DS} and lid["recursief"] is False
    weigering(execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)), "checkpoint_dekt_niet")
    assert nas.updated == []


def test_h2b_kindsnapshot_na_het_checkpoint_weg(stack: Stack) -> None:
    hub, c, nas = stack
    eigen_dataset(nas, "database")
    installeer(hub, c)
    cp = snapshot(hub, c, DS)
    nas.data["snapshots"][f"{DS}/database"].clear()
    d = weigering(execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)), "checkpoint_afwijkend")
    assert d["details"]["datasets"] == [f"{DS}/database"] and nas.updated == []


def test_h2c_checkpoint_zonder_voltooide_eigen_snapshotactie(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    los = str(uuid.uuid4())
    with pytest.raises(JournalUnavailable):  # registreren kan alleen tijdens de eigen snapshotactie
        journaal(hub).leg_checkpoint_vast(los, "testpool/apps", "testpool/apps@auto-latest", "1000", True)
    cp = checkpoint(hub)
    with sqlite3.connect(hub.settings.replay_db) as conn:
        conn.execute("UPDATE journal SET status = 'mislukt' WHERE request_id = ?", (cp,))
    weigering(execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp)), "checkpoint_ontbreekt")
    assert nas.updated == []


def test_p3_recursief_over_ouder_en_kind(stack: Stack) -> None:
    hub, c, nas = stack
    eigen_dataset(nas, "database")
    installeer(hub, c)
    cp = snapshot(hub, c, DS)
    lid = journaal(hub).checkpoint(cp)
    assert lid is not None and set(lid["leden"]) == {DS, f"{DS}/database"} and lid["recursief"] is True
    r = execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp))
    assert r.status_code == 200 and len(nas.updated) == 1, r.text


@pytest.mark.parametrize("soort", ["opslag", "snapshot"])
def test_h3_dekking_verandert_vlak_voor_de_schrijfactie(stack: Stack, soort: str) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    cp = snapshot(hub, c)
    echt = nas._write
    gelezen = {"n": 0}

    def tussendoor(method: str, params: list[Any]) -> Any:
        if method == "app.config":
            gelezen["n"] += 1
            if gelezen["n"] == 2:  # na de controle, vóór de schrijfaanroep: een ander proces wijzigt de NAS
                app = nas.app("demo-app")
                assert app is not None
                if soort == "opslag":
                    app["config"]["storage"][0]["host_path_config"]["path"] = "/mnt/testpool/photos"
                else:
                    nas.data["snapshots"]["testpool/apps"].pop()
        return echt(method, params)

    nas._write = tussendoor  # type: ignore[method-assign]
    r = execute(c, hub, approved(hub, bijwerken(nas), backup_checkpoint_id=cp))
    assert gelezen["n"] == 2
    weigering(r, "checkpoint_dekt_niet" if soort == "opslag" else "checkpoint_afwijkend")
    assert nas.updated == [] and writes(nas) == ["app.create", "pool.snapshot.create"]
    assert [(e["status"], e["detail"]) for e in journaal(hub).entries() if e["action_id"] == "app.update"] == [
        ("mislukt", r.json()["code"])
    ]
    assert journaal(hub).stopped() is None


def test_h4_recept_met_een_ongedekte_bestemming(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    up = approved(hub, bijwerken(nas))
    assert execute(c, hub, up).status_code == 200
    rid = up["approval"]["request_id"]
    j = journaal(hub)
    recept = j.load_values(rid)
    assert recept is not None
    regel = {**recept[1]["storage"][0], "host_path_config": {"path": "/mnt/testpool/photos"}}
    elders = {**recept[1], "storage": [regel]}
    with sqlite3.connect(hub.settings.replay_db) as conn:  # alsof de app bij die bijwerking op photos schreef
        conn.execute("DELETE FROM app_values WHERE request_id = ?", (rid,))
    j.save_values(rid, "demo-app", elders)
    terug = app_prop(nas, "app.rollback", "demo-app", {"herstel_van": rid})
    d = weigering(execute(c, hub, approved(hub, terug, backup_checkpoint_id=snapshot(hub, c))), "checkpoint_dekt_niet")
    assert d["details"]["datasets"] == ["testpool/apps", "testpool/photos"] and len(nas.updated) == 1


def test_h5_bijwerken_terug_naar_de_image_van_voor_een_migratie(stack: Stack) -> None:
    hub, c, nas = stack
    installeer(hub, c)
    oud = nas.app("demo-app")["config"]["image"]["tag"]  # type: ignore[index]
    up = approved(hub, bijwerken(nas, upgrade={"migrations": True}))
    assert execute(c, hub, up).status_code == 200
    terug = bijwerken(nas, oud)  # dezelfde digest via app.update, niet via app.rollback
    weigering(execute(c, hub, approved(hub, terug)), "database_herstel_vereist")
    assert len(nas.updated) == 1
    verder = approved(hub, bijwerken(nas, f"1.2.5@{DIGEST_B}"))  # vooruit blijft mogelijk
    assert execute(c, hub, verder).status_code == 200


def test_h5b_catalogusversie_terug_via_bijwerken(stack: Stack) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app("immich", "RUNNING", "ghcr.io/immich-app/server:1.0.0", 2283, 2283, "/mnt/testpool/apps/immich", "/d",
             catalog_app="immich")
    )  # fmt: skip
    van = str(nas.app("immich")["version"])  # type: ignore[index]
    up = app_prop(nas, "app.update", "immich", {"catalog_version": "1.0.1", "upgrade": {"migrations": True}})
    assert execute(c, hub, approved(hub, up)).status_code == 200
    terug = app_prop(nas, "app.update", "immich", {"catalog_version": van})
    weigering(execute(c, hub, approved(hub, terug)), "database_herstel_vereist")
    assert [m for m, _p in nas.calls].count("app.upgrade") == 1


def test_h6_ouder_journaal_geeft_herkomst_onbekend(stack: Stack, tmp_path: Path) -> None:
    hub, c, nas = stack
    nas.data["app.query"].append(
        _app("immich", "RUNNING", "ghcr.io/immich-app/server:1.0.0", 2283, 2283, "/mnt/testpool/apps/immich", "/d",
             catalog_app="immich")
    )  # fmt: skip
    installeer(hub, c)
    oud = str(uuid.uuid4())
    j = journaal(hub)
    j.save_values(oud, "demo-app", {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}})
    j.oud_vastlegging()
    assert execute(c, hub, approved(hub, bijwerken(nas, f"1.2.5@{DIGEST_B}"))).status_code == 200
    kopie = tmp_path / "eerder.sqlite"
    with sqlite3.connect(hub.settings.replay_db) as bron, sqlite3.connect(kopie) as doel:
        bron.backup(doel)
    van = str(nas.app("immich")["version"])  # type: ignore[index]
    up = app_prop(nas, "app.update", "immich", {"catalog_version": "1.0.1", "upgrade": {"migrations": True}})
    assert execute(c, hub, approved(hub, up)).status_code == 200
    mig = approved(hub, bijwerken(nas, f"1.2.6@{DIGEST_B}", upgrade={"migrations": True}))
    assert execute(c, hub, mig).status_code == 200
    # Het journaal komt terug uit de kopie van vóór de migraties; de geheimenmap (met de ankers) is de actuele.
    with sqlite3.connect(kopie) as bron, sqlite3.connect(hub.settings.replay_db) as doel:
        bron.backup(doel)
    weigering(execute(c, hub, approved(hub, app_prop(nas, "app.rollback", "immich", {"catalog_version": van}))),
              "herkomst_onbekend")  # fmt: skip
    rid = mig["approval"]["request_id"]
    assert journaal(hub).load_values(rid) is None  # ook het recept van de migratie ontbreekt
    weigering(execute(c, hub, approved(hub, bijwerken(nas, f"1.2.4@{DIGEST_B}"))), "herkomst_onbekend")
    assert len(nas.updated) == 2 and [m for m, _p in nas.calls].count("app.rollback") == 0
    # Ook het oude recept van een app met een onvolledige historie gaat niet alsnog door als "oud".
    weigering(execute(c, hub, approved(hub, app_prop(nas, "app.rollback", "demo-app", {"herstel_van": oud}))),
              "herkomst_onbekend")  # fmt: skip
