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
from asm_policy.etag import ABSENT, app_etag, dataset_etag
from executorhelpers import Hub, approved, checkpoint, execute, nas_hub, set_write_key, signed, write_nas
from executorhelpers import client as hub_client
from fakes.fake_truenas import FakeTrueNAS, _app
from fastapi.testclient import TestClient
from policyhelpers import DIGEST_B, HOST, install_params, proposal

from executor.journal import Journal

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


def snapshot(hub: Hub, c: TestClient, dataset: str = "testpool/apps", naam: str = "voor-update") -> str:
    prop = proposal(
        "zfs.snapshot.create",
        {"host_id": HOST, "dataset": dataset},
        {"naam": naam, "recursief": True},
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
        _app("immich", "RUNNING", "ghcr.io/immich-app/server:1.0.0", 2283, 2283, "/m", "/d", catalog_app="immich")
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
