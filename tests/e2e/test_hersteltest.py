"""Dienst-E2E hersteltest-robot en snapshot-herstel in de zandbak (B12-005, EX14; S-P2-100; Sim-getest).

De echte Hub stelt voor (R1), de echte executor klont in de fake TrueNAS naar ``<pool>/asm-sandbox/<naam>``; de robot
in de Hub toetst kloon, database-export en productie. Geen echte NAS.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from actiehelpers import Stack, app_target, bouw_stack, haal, keur_goed, schrijfaanroepen, stel_voor, voer_uit
from conftest import idem
from executorhelpers import write_nas
from fakes.fake_truenas import FakeTrueNAS
from policyhelpers import DIGEST_B, install_params

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
DS = "testpool/apps/demo-app"
NIEUW = {"image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": f"1.2.4@{DIGEST_B}"}}


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def stack(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Stack]:
    s = bouw_stack(admin=admin, app=app, nas=nas, worker_once=worker_once, tmp_path=tmp_path, monkeypatch=monkeypatch)
    yield s
    s.stop()


def _snapshot(stack: Stack, dataset: str, naam: str) -> dict[str, Any]:
    v = stel_voor(stack.admin, "zfs.snapshot.create", {"host_id": "nas-primary", "dataset": dataset}, {"naam": naam})
    assert v.status_code == 201 and v.json()["blokkades"] == [], v.text
    r = voer_uit(stack.admin, v.json())
    assert r.status_code == 200 and r.json()["resultaat"]["waarschuwingen"] == [], r.text
    return dict(v.json())


def _kloon(stack: Stack, snapshot: str, doel: str) -> Any:
    v = stel_voor(stack.admin, "zfs.snapshot.clone_to_sandbox", {"host_id": "nas-primary", "snapshot": snapshot},
                  {"doel_dataset": doel})  # fmt: skip
    if v.status_code != 201:
        return v
    assert v.json()["risk_class"] == "R1" and v.json()["blokkades"] == [], v.text
    return voer_uit(stack.admin, v.json())


def _herstelpunt(stack: Stack) -> tuple[dict[str, Any], dict[str, Any]]:
    """demo-app met eigen dataset, geïnstalleerd; checkpoint + update-voorstel → herstelpunt (B12-006)."""
    admin, nas = stack.admin, stack.nas
    apps = nas.datasets()["testpool/apps"]
    apps["children"].append({**apps["children"][0], "id": DS, "name": DS, "mountpoint": f"/mnt/{DS}", "children": []})
    nas.add_dataset("testpool/asm-sandbox")  # de ouderdataset van de zandbak maakt de beheerder
    nas.inhoud[DS] = {"config": "oud"}
    v = stel_voor(admin, "app.install", app_target("demo-app"), install_params("demo-app")).json()
    assert keur_goed(admin, v).status_code == 200 and voer_uit(admin, v).status_code == 200
    stack.vernieuw()
    assert stack.toestand.besluiten is not None
    stack.toestand.besluiten["D16"] = ("Getest", {"per_app": [{"app_id": "demo-app", "rpo_uren": 24, "rto_uren": 1}]})
    cp = _snapshot(stack, DS, "voor-update")
    upd = stel_voor(admin, "app.update", app_target("demo-app"), NIEUW).json()
    assert upd["blokkades"] == [], upd
    [hp] = admin.get("/api/v1/backups/herstelpunten", params={"app": "demo-app"}).json()["items"]
    assert hp["checkpoint_id"] == cp["request_id"] and hp["status"] == "geverifieerd"
    return hp, upd


def _robot(stack: Stack, hp: dict[str, Any], klonen: list[str]) -> dict[str, Any]:
    r = stack.admin.post(f"/api/v1/backups/herstelpunten/{hp['id']}/hersteltest", json={"klonen": klonen},
                         headers=idem())  # fmt: skip
    assert r.status_code == 200, r.text
    return dict(r.json())


def _status(stack: Stack) -> tuple[str, str | None]:
    [hp] = stack.admin.get("/api/v1/backups/herstelpunten", params={"app": "demo-app"}).json()["items"]
    return hp["status"], hp["reden"]


def test_ex14_snapshot_herstel_in_de_zandbak_oude_waarde_terug_productie_onaangeroerd(stack: Stack) -> None:
    hp, _ = _herstelpunt(stack)
    nas = stack.nas
    nas.inhoud[DS] = {"config": "nieuw"}  # productie verandert na de snapshot
    r = _kloon(stack, f"{DS}@voor-update", "testpool/asm-sandbox/proef")
    assert r.status_code == 200 and r.json()["resultaat"]["readback"] == {
        "dataset": "testpool/asm-sandbox/proef",
        "aanwezig": True,
    }, r.text
    assert nas.inhoud["testpool/asm-sandbox/proef"] == {"config": "oud"}  # de oude waarde is terug
    assert nas.inhoud[DS] == {"config": "nieuw"}  # productie is niet veranderd
    # Alleen een snapshot en een kloon: nooit een rollback, update of verwijdering op productie.
    assert schrijfaanroepen(nas) == ["app.create", "pool.snapshot.create", "pool.snapshot.clone"]

    uit = _robot(stack, hp, [r.json()["request_id"]])
    assert (uit["resultaat"], uit["reden"], uit["status_herstelpunt"]) == ("geslaagd", None, "geverifieerd"), uit
    assert uit["kloon"]["klonen"] == {f"{DS}@voor-update": "testpool/asm-sandbox/proef"}
    assert uit["productie"]["resultaat"] == "geslaagd" and uit["database"] == {
        "resultaat": "geslaagd",
        "reden": None,
        "database": "geen",
    }
    tests = stack.admin.get("/api/v1/backups/restore-tests").json()["items"]
    assert [(t["app_id"], t["resultaat"], t["referentie"]) for t in tests] == [
        ("demo-app", "geslaagd", f"herstelpunt:{hp['id']}")
    ]
    assert schrijfaanroepen(nas)[-1] == "pool.snapshot.clone"  # de robot zelf schreef niets op de NAS


def test_kloon_buiten_de_zandbak_wordt_geweigerd_en_telt_niet(stack: Stack) -> None:
    hp, _ = _herstelpunt(stack)
    for doel in ("testpool/apps/demo-app-kopie", "testpool/asm-sandbox", "testpool/asm-sandbox/a/b"):
        r = _kloon(stack, f"{DS}@voor-update", doel)
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert schrijfaanroepen(stack.nas) == ["app.create", "pool.snapshot.create"]
    # Een ander verzoek-ID (de snapshot zelf, of een onbekend ID) is geen kloon: onbekend, status ongemoeid.
    for klonen in ([hp["checkpoint_id"]], [str(uuid.uuid4())]):
        uit = _robot(stack, hp, klonen)
        assert (uit["resultaat"], uit["reden"]) == ("onbekend", "kloon_niet_uitgevoerd"), uit
    assert _status(stack) == ("geverifieerd", None)


def test_kloon_van_een_andere_snapshot_hoort_niet_bij_het_herstelpunt(stack: Stack) -> None:
    hp, _ = _herstelpunt(stack)
    _snapshot(stack, "testpool/apps", "ander")
    r = _kloon(stack, "testpool/apps@ander", "testpool/asm-sandbox/ander")
    assert r.status_code == 200, r.text
    uit = _robot(stack, hp, [r.json()["request_id"]])
    assert (uit["resultaat"], uit["reden"]) == ("onbekend", "kloon_hoort_niet_bij_herstelpunt"), uit
    assert _status(stack) == ("geverifieerd", None)


def _met_export(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    """De eigen Hub-export als database-export van demo-app (alleen de Hub-export is nu echt te meten)."""
    from hub.actions import blokkades

    assert stack.admin.post("/api/v1/backups/self", headers=idem()).status_code == 202
    assert stack.worker_once()[-1]["status"] == "geslaagd"
    echt = blokkades._db_export
    monkeypatch.setattr(blokkades, "_db_export", lambda db, app, *a: echt(db, "ai-server-manager", *a))


def test_kapotte_checksum_maakt_het_herstelpunt_ongezond_en_de_pre_update_gate_dicht(
    stack: Stack, monkeypatch: pytest.MonkeyPatch, settings: Any
) -> None:
    _met_export(stack, monkeypatch)
    hp, upd = _herstelpunt(stack)
    assert hp["db_export"]["bron"] == "pg_dump"
    kloon = _kloon(stack, f"{DS}@voor-update", "testpool/asm-sandbox/proef").json()["request_id"]

    uit = _robot(stack, hp, [kloon])  # eerst heel: de export komt met gelijke aantallen terug in de proefdatabase
    assert (uit["resultaat"], uit["status_herstelpunt"]) == ("geslaagd", "geverifieerd"), uit
    assert uit["database"]["tellingen"]["public.app_user"] >= 1

    dump = settings.backups_dir / next(p.name for p in settings.backups_dir.glob("hub-*.dump"))
    with dump.open("r+b") as fh:
        fh.seek(-1, os.SEEK_END)
        last = fh.read(1)
        fh.seek(-1, os.SEEK_END)
        fh.write(bytes([last[0] ^ 0xFF]))
    uit = _robot(stack, hp, [kloon])
    assert (uit["resultaat"], uit["reden"], uit["status_herstelpunt"]) == ("mislukt", "checksum_afwijkend", "ongezond")
    assert _status(stack) == ("ongezond", "checksum_afwijkend")

    # De pre-update-gate is dicht; een nieuwe beoordeling van dezelfde snapshot zet 'ongezond' niet terug.
    r = keur_goed(stack.admin, haal(stack.admin, upd))
    assert r.status_code == 409 and r.json()["code"] == "actie_geblokkeerd", r.text
    [blok] = [b for b in r.json()["details"]["blokkades"] if b["code"] == "backup_checkpoint_ontbreekt"]
    assert blok["details"] == ["herstelpunt_ongezond"]
    assert _status(stack) == ("ongezond", "checksum_afwijkend")
    assert "app.update" not in schrijfaanroepen(stack.nas)


def test_robot_faalt_als_de_productiedatabase_verandert(stack: Stack, monkeypatch: pytest.MonkeyPatch) -> None:
    from hub.backup import hersteltest as ht

    hp, _ = _herstelpunt(stack)
    kloon = _kloon(stack, f"{DS}@voor-update", "testpool/asm-sandbox/proef").json()["request_id"]

    def verkeerd_gericht(db: Any, settings: Any, h: Any) -> Any:
        # Een herstel dat (fout) in productie schrijft: precies wat de robot moet betrappen.
        with stack.app.state.sessionmaker() as prod:
            stack.app.state.vault().put(prod, "vault://test/verkeerd", "x" * 12, actor="test")
            prod.commit()
        return ht.Deel("geslaagd")

    monkeypatch.setattr(ht, "toets_export", verkeerd_gericht)
    uit = _robot(stack, hp, [kloon])
    assert (uit["resultaat"], uit["reden"], uit["status_herstelpunt"]) == ("mislukt", "productie_gewijzigd", "ongezond")


def test_kijker_en_operator_mogen_de_robot_niet_starten(stack: Stack) -> None:
    from conftest import login_as, make_user

    hp, _ = _herstelpunt(stack)
    for rol in ("viewer", "operator"):
        make_user(stack.admin, f"r-{rol}", rol)
        c = login_as(stack.app, f"r-{rol}")
        r = c.post(f"/api/v1/backups/herstelpunten/{hp['id']}/hersteltest", json={"klonen": [hp["checkpoint_id"]]},
                   headers=idem())  # fmt: skip
        assert r.status_code == 403, r.text
        assert c.get("/api/v1/backups/rampenscenario").status_code == 200
    assert stack.admin.get("/api/v1/backups/restore-tests").json()["items"] == []
