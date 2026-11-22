"""Positieve witte lijst voor dekking en herkomst (S-P2-050f, tweede herstelronde op R-HARDE-EIS-1, -2, -4, -5, -6).

Dekking en herkomst gelden alleen als elk onderdeel positief bekend en gelezen is: een ontbrekende volumelijst, een
verdwenen basissnapshot, een opslagregel van onbekend type, een andere schrijfwijze van dezelfde digest, een
migratieregistratie zonder vertrekimage en een ontbrekende tussenregel in de herkomst leiden tot weigering. Alle invoer
is synthetisch; de proeven stoppen bij de lees- en beslisfuncties (Sim-getest, geen NAS).
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from asm_policy import checkpoint as cp
from asm_policy.params import expected_image
from executor.journal import AAD_HERKOMST, Journal, JournalUnavailable
from executor.naslink import NasLinkStore
from executor.uitvoeren import Uitvoerder
from executorhelpers import POLICY, Hub, checkpoint
from policyhelpers import install_params

from hub.actions import blokkades
from hub.routers import backups
from hub.truenas import normalize

pytestmark = [pytest.mark.e2e]

APP = "demo-app"
DS = "proef/config"
ANDER = "proef/geschiedenis"
BOOM = [{"name": ds, "mountpoint": f"/mnt/{ds}"} for ds in (DS, ANDER)]
OPSLAG = {"storage": [{"type": "host_path", "host_path_config": {"path": f"/mnt/{DS}"}}]}
IMAGE = install_params(APP)["app_create"]["values"]["image"]
WERKLAST = {"containers": 1, "images": [f"{IMAGE['repository']}:{IMAGE['tag']}"], "volumes": []}
METHODEN = frozenset({"pool.snapshot.query"})


def uitvoerder(hub: Hub, journaal: Journal | None = None) -> Uitvoerder:
    s = hub.settings
    return Uitvoerder(policy=POLICY, journal=journaal or Journal(s.replay_db, s.secrets_dir),
                      naslink=NasLinkStore(s.secrets_dir))  # fmt: skip


class Lezing:
    """Alleen leesmethoden, zoals de executor ze in de gate aanroept."""

    def __init__(self, config: Any, snapshots: list[dict[str, str]]) -> None:
        self.config, self.snapshots = config, snapshots

    def call(self, methode: str, *_args: Any) -> Any:
        return {"app.config": self.config, "pool.dataset.query": BOOM, "pool.snapshot.query": self.snapshots}[methode]


def code(uitkomst: Any) -> str:
    return uitkomst.body["code"] if uitkomst is not None else "doorgelaten"


# ------------------------------------------------------------------ R-HARDE-EIS-1: volumelijst niet gelezen
def test_niet_gelezen_volumelijst_is_onbekende_dekking_in_hub_en_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    volledig = {**WERKLAST, "volumes": [{"source": f"/mnt/{ANDER}", "type": "bind", "mode": "rw"}]}
    assert cp.app_datasets(OPSLAG, BOOM, APP, volledig) == [DS, ANDER]
    zonder = {k: v for k, v in volledig.items() if k != "volumes"}
    assert cp.app_datasets(OPSLAG, BOOM, APP, zonder) is None  # ook al wijst de configuratie DS aan

    def hub_dekking(werklast: Any) -> list[str] | None:
        app = {"name": APP, "state": "RUNNING", "active_workloads": werklast}
        inv = SimpleNamespace(apps={"status": "ok", "data": normalize.apps([app])},
                              datasets={"status": "ok", "data": normalize.datasets(BOOM)})  # fmt: skip
        monkeypatch.setattr(backups, "coverage_inputs", lambda *_: inv)
        return blokkades._app_datasets(None, None, APP)  # type: ignore[arg-type]

    assert hub_dekking(volledig) == [ANDER]
    assert hub_dekking(zonder) is None
    assert hub_dekking({**volledig, "volumes": ["geen-object"]}) is None
    ro = {**volledig, "volumes": [{"source": "/etc/localtime", "type": "bind", "mode": "ro"}]}
    assert hub_dekking(ro) == []  # alleen-lezen telt niet, net als bij de executor


# ------------------------------------------------------------------ R-HARDE-EIS-2: basissnapshot altijd gecontroleerd
def test_verdwenen_basissnapshot_ook_zonder_appopslag(tmp_path: Path) -> None:
    hub = Hub(tmp_path)
    dienst, naam = uitvoerder(hub), f"{DS}@voor"
    rid = checkpoint(hub, DS, naam, "18")
    assert cp.app_datasets({}, BOOM, APP, WERKLAST) == []
    assert dienst._checkpoint_gate(Lezing({}, [{"name": naam, "createtxg": "18"}]), METHODEN, APP, rid, WERKLAST,
                                   None)[0] is None  # fmt: skip
    for snapshots in ([], [{"name": naam, "createtxg": "19"}]):
        uit = dienst._checkpoint_gate(Lezing({}, snapshots), METHODEN, APP, rid, WERKLAST, None)[0]
        assert code(uit) == "checkpoint_afwijkend" and uit.body["details"]["datasets"] == [DS]


# ------------------------------------------------------------------ R-HARDE-EIS-4: onbekend type opslagregel
@pytest.mark.parametrize("waar", ["recept", "config"])
def test_opslagregel_van_onbekend_type_dekt_niet(tmp_path: Path, waar: str) -> None:
    hub = Hub(tmp_path)
    dienst, naam = uitvoerder(hub), f"{DS}@voor"
    rid = checkpoint(hub, DS, naam, "18")
    vreemd = {"storage": [*OPSLAG["storage"], {"type": "onbekend", "mount_path": "/gegevens"}]}
    config, recept = (OPSLAG, vreemd) if waar == "recept" else (vreemd, None)
    assert cp.app_datasets(config, BOOM, APP, WERKLAST, ook=recept) is None
    uit = dienst._checkpoint_gate(Lezing(config, [{"name": naam, "createtxg": "18"}]), METHODEN, APP, rid, WERKLAST,
                                  recept)[0]  # fmt: skip
    assert code(uit) == "checkpoint_dekt_niet"


def test_recept_met_bekende_gedekte_bestemming_blijft_werken(tmp_path: Path) -> None:
    hub = Hub(tmp_path)
    dienst, naam = uitvoerder(hub), f"{DS}@voor"
    rid = checkpoint(hub, DS, naam, "18")
    recept = {**install_params(APP)["app_create"]["values"], **OPSLAG}
    assert cp.app_datasets(OPSLAG, BOOM, APP, WERKLAST, ook=recept) == [DS]
    lezing = Lezing(OPSLAG, [{"name": naam, "createtxg": "18"}])
    assert dienst._checkpoint_gate(lezing, METHODEN, APP, rid, WERKLAST, recept)[0] is None


# ------------------------------------------------------------------ R-HARDE-EIS-5: één image-identiteit
def test_image_identiteit_is_gelijk_voor_digest_in_tag_en_apart() -> None:
    versie, digest = IMAGE["tag"].split("@")
    repo = IMAGE["repository"]
    in_tag = cp.doel_identiteiten(expected_image({"image": IMAGE}))
    apart = cp.doel_identiteiten(expected_image({"image": {**IMAGE, "tag": versie}, "image_digest": digest}))
    assert in_tag == apart == {f"{repo}:{versie}", f"{repo}@{digest}"}
    # Een oudere vastgelegde schrijfwijze telt in dezelfde vorm.
    assert cp.normaliseer([f"{repo}:{IMAGE['tag']}", f"{repo}@{digest}", "versie:1.0"]) == {*in_tag, "versie:1.0"}


def test_beide_schrijfwijzen_vereisen_databaseherstel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dienst = uitvoerder(Hub(tmp_path))
    versie, digest = IMAGE["tag"].split("@")
    staat = {"images": [f"{IMAGE['repository']}:{IMAGE['tag']}"]}
    dienst.journal.leg_herkomst_vast(str(uuid4()), APP, {"migratie": True, "van": sorted(cp.identiteiten(staat))})
    migratie = {"upgrade": {"migrations": True}}
    eerder = SimpleNamespace(status="uitgevoerd", parameters=migratie, preview={"huidig": staat})
    monkeypatch.setattr(blokkades, "_eigen_wijzigingen", lambda *_: [eerder])
    for params in ({"image": IMAGE}, {"image": {**IMAGE, "tag": versie}, "image_digest": digest}):
        req = SimpleNamespace(action_id="app.update", parameters=params)
        assert [b["code"] for b in blokkades.ex15(None, req)] == ["database_herstel_vereist"]  # type: ignore[arg-type]
        doel = cp.doel_identiteiten(expected_image(params))
        assert code(dienst._herkomst_gate(params, APP, "app.update", doel)[1]) == "database_herstel_vereist"
    # Ook een migratie met een onbekende of mislukte uitkomst telt (ze kan al gedraaid hebben).
    eerder.status = "afwijking"
    req = SimpleNamespace(action_id="app.update", parameters={"image": IMAGE})
    assert [b["code"] for b in blokkades.ex15(None, req)] == ["database_herstel_vereist"]  # type: ignore[arg-type]
    # De Hub weigert ook als niet bekend is wat er vóór de migratie draaide.
    eerder.preview = {"huidig": {}}
    req = SimpleNamespace(action_id="app.update", parameters={"image": IMAGE})
    assert [b["code"] for b in blokkades.ex15(None, req)] == ["herkomst_onbekend"]  # type: ignore[arg-type]


def oude_registratie(j: Journal, app: str, herkomst: dict[str, Any], recept: dict[str, Any] | None = None) -> str:
    """Een herkomst zoals de vorige versie hem schreef: zonder ``van`` en ``vorige``, zonder ketenanker."""
    rid = str(uuid4())
    if recept is not None:
        j.save_values(rid, app, recept)
    box = j._zegel({**herkomst, "app": app}, AAD_HERKOMST + f"{rid}:{app}".encode())
    with closing(sqlite3.connect(j.path)) as conn, conn:
        sql = "INSERT INTO recept_herkomst (request_id, app, box, created_at) VALUES (?, ?, ?, 0)"
        conn.execute(sql, (rid, app, box))
    return rid


def test_oude_migratieregistratie_leidt_de_vertrekimage_af_uit_het_recept(tmp_path: Path) -> None:
    dienst = uitvoerder(Hub(tmp_path))
    mig = {"migratie": True, "van_versie": "1.4.8", "soort": "app.update"}
    oude_registratie(dienst.journal, APP, mig, {"image": IMAGE})
    doel = cp.doel_identiteiten(expected_image({"image": IMAGE}))
    assert code(dienst._herkomst_gate({"image": IMAGE}, APP, "app.update", doel)[1]) == "database_herstel_vereist"
    # Zonder recept en zonder vastgelegde vertrekimage: niet te herleiden, dus weigeren.
    oude_registratie(dienst.journal, "andere-app", mig)
    assert code(dienst._herkomst_gate({"image": IMAGE}, "andere-app", "app.update", doel)[1]) == "herkomst_onbekend"


# ------------------------------------------------------------------ R-HARDE-EIS-6: hash-keten met anker
def drie_wijzigingen(j: Journal) -> list[str]:
    ids = [str(uuid4()) for _ in range(3)]
    for i, (rid, mig) in enumerate(zip(ids, (False, True, False), strict=True)):
        j.leg_herkomst_vast(rid, APP, {"migratie": mig, "van_versie": f"1.0.{i}", "van": [f"versie:1.0.{i}"]})
    return ids


def kopie_zonder(hub: Hub, tmp_path: Path, request_id: str) -> Journal:
    kopie = tmp_path / "hersteld.sqlite"
    with closing(sqlite3.connect(hub.settings.replay_db)) as bron, closing(sqlite3.connect(kopie)) as doel:
        bron.backup(doel)
        with doel:
            doel.execute("DELETE FROM recept_herkomst WHERE request_id = ?", (request_id,))
    return Journal(kopie, hub.settings.secrets_dir)


@pytest.mark.parametrize("weg", [0, 1, 2])
def test_ontbrekende_regel_in_de_keten_is_onvolledig(tmp_path: Path, weg: int) -> None:
    hub = Hub(tmp_path / "dienst")
    ids = drie_wijzigingen(uitvoerder(hub).journal)
    hersteld = kopie_zonder(hub, tmp_path, ids[weg])
    with pytest.raises(JournalUnavailable, match="herkomst_onvolledig"):
        hersteld.herkomsten(APP)
    uit = uitvoerder(hub, hersteld)._herkomst_gate({"catalog_version": "1.0.0"}, APP, "app.rollback", {"versie:1.0.0"})
    assert code(uit[1]) == "herkomst_onbekend"
    with pytest.raises(JournalUnavailable, match="herkomst_onvolledig"):  # ook geen nieuwe regel op een kapotte keten
        hersteld.leg_herkomst_vast(str(uuid4()), APP, {"migratie": False})


def test_intacte_keten_en_verloren_anker(tmp_path: Path) -> None:
    hub = Hub(tmp_path)
    j = uitvoerder(hub).journal
    ids = drie_wijzigingen(j)
    assert [r for _i, r, _h in j.herkomsten(APP)] == ids
    assert j.herkomsten("nog-nooit-gewijzigd") == []
    (j.herkomst_ankers / APP.encode().hex()).unlink()
    with pytest.raises(JournalUnavailable, match="herkomst_onvolledig"):
        j.herkomsten(APP)


def test_oude_recepten_krijgen_eenmalig_een_ketenbegin(tmp_path: Path) -> None:
    hub = Hub(tmp_path)
    j = uitvoerder(hub).journal
    oud = [oude_registratie(j, APP, {"migratie": False, "van_versie": "1.0.0"}, {"image": IMAGE}) for _ in range(2)]
    assert not j.herkomst_start.exists()
    assert [r for _i, r, _h in j.herkomsten(APP)] == oud  # startregistratie: de bestaande regels zijn het begin
    nieuw = str(uuid4())
    j.leg_herkomst_vast(nieuw, APP, {"migratie": False})
    assert [r for _i, r, _h in j.herkomsten(APP)] == [*oud, nieuw]
    with pytest.raises(JournalUnavailable, match="herkomst_onvolledig"):  # na het begin: elke regel telt
        kopie_zonder(hub, tmp_path, oud[0]).herkomsten(APP)
