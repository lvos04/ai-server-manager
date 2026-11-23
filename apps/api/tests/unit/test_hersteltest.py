"""Hersteltest-robot en rampenscenario zonder database (B12-005, B12-007; S-P2-100)."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

from hub.backup import hersteltest as ht
from hub.backup import rampenscenario
from hub.models import Herstelpunt

# Tabelnamen zoals in de databases van de mediaserver (kijkgeschiedenis) en MediaGuard (voortgang).
MEDIA = {"UserDatas": 1840, "job": 312, "vervang_transactie": 97}


def test_gelijke_aantallen_per_tabel_is_geslaagd() -> None:
    uit = ht.vergelijk_tellingen(MEDIA, dict(MEDIA))
    assert (uit.resultaat, uit.reden, uit.bewijs) == ("geslaagd", None, {"tabellen": 3, "rijen": 2249})


@pytest.mark.parametrize(
    ("na", "verschil"),
    [
        ({**MEDIA, "UserDatas": 1839}, {"UserDatas": {"voor": 1840, "na": 1839}}),  # één kijkregel kwijt
        ({k: v for k, v in MEDIA.items() if k != "job"}, {"job": {"voor": 312, "na": None}}),  # voortgang weg
        ({**MEDIA, "extra": 0}, {"extra": {"voor": None, "na": 0}}),
    ],
)
def test_harde_eis_elk_verschil_in_kijkgeschiedenis_of_voortgang_is_mislukt(na: dict, verschil: dict) -> None:
    uit = ht.vergelijk_tellingen(MEDIA, na)
    assert (uit.resultaat, uit.reden, uit.bewijs) == ("mislukt", "inhoud_wijkt_af", {"verschil": verschil})


@pytest.mark.parametrize(
    "ongeldig", [None, {}, [], {"UserDatas": True}, {"UserDatas": "1840"}, {"UserDatas": -1}, {"": 1}, {"t": 1.0}]
)
def test_ongeldige_tellingen_zijn_onbekend_nooit_geslaagd(ongeldig: object) -> None:
    assert ht.vergelijk_tellingen(MEDIA, ongeldig).resultaat == "onbekend"
    assert ht.vergelijk_tellingen(ongeldig, MEDIA).resultaat == "onbekend"


def test_samen_mislukt_gaat_voor_onbekend_en_alleen_alles_geslaagd_telt() -> None:
    g, o, m = ht.Deel("geslaagd"), ht.Deel("onbekend", "x"), ht.Deel("mislukt", "y")
    assert ht.samen([g, o, m]).resultaat == "mislukt" and ht.samen([g, o]).reden == "x"
    assert ht.samen([g, g]).resultaat == "geslaagd"


@pytest.mark.parametrize("app", ["emby", "jellyfin", "mediaguard", "MediaGuard"])
def test_harde_eis_media_herstelpunt_zonder_database_is_onbekend(app: str) -> None:
    hp = Herstelpunt(id=uuid.uuid4(), app=app, checkpoint_id="x", snapshot={}, db_export=None, status="x")
    uit = ht.toets_export(None, None, hp)  # type: ignore[arg-type]  # zonder export raakt de robot niets aan
    assert (uit.resultaat, uit.reden) == ("onbekend", "database_export_ontbreekt")


def test_andere_export_dan_pg_dump_is_capability_unavailable() -> None:
    hp = Herstelpunt(app="mediaguard", db_export={"bron": "connector", "sha256": "a" * 64})
    assert ht.toets_export(None, None, hp).reden == "capability_unavailable"  # type: ignore[arg-type]


def test_proefdatabase_nooit_onder_de_productienaam(tmp_path: Path) -> None:
    for naam in ("hub", "hersteltest_", "hersteltest_ABCDEF012345", "hersteltest_0123456789ab; DROP"):
        with pytest.raises(ValueError), ht.proefdatabase("postgresql://hub@/hub", naam):
            pass


def test_veilig_pad_weigert_koppeling_in_bovenliggende_map(tmp_path: Path) -> None:
    (tmp_path / "echt").mkdir()
    (tmp_path / "echt" / "x.dump").write_bytes(b"PGDMP")
    (tmp_path / "via").symlink_to(tmp_path / "echt")
    assert ht._veilig_pad(tmp_path / "echt" / "x.dump", tmp_path)
    assert not ht._veilig_pad(tmp_path / "via" / "x.dump", tmp_path)
    assert not ht._veilig_pad(tmp_path / "echt" / "x.dump", tmp_path / "via")
    assert not ht._veilig_pad(tmp_path / "echt" / "bestaat-niet.dump", tmp_path)


# Een terminalstap op de NAS (V-096) mag in geen enkele stap staan.
TERMINAL = re.compile(
    r"\b(ssh|sudo|shell|terminal|console|midclt|zfs (rollback|send|recv|destroy)|zpool|docker|psql|pg_restore|"
    r"rm -|chmod|chown)\b|\$ |`",
    re.IGNORECASE,
)


def test_rampenscenario_dekt_b12_007_zonder_terminalstap() -> None:
    ids = [s["id"] for s in rampenscenario.SCENARIOS]
    assert ids == ["poolverlies", "credential_lek", "foutieve_appmigratie", "mediaguard_terugzetten", "verhuizing"]
    for s in rampenscenario.SCENARIOS:
        assert s["titel"] and s["wanneer"] and s["stappen"] and s["natest"], s["id"]
        for tekst in [s["wanneer"], *s["stappen"], *s["natest"]]:
            assert not TERMINAL.search(tekst), (s["id"], tekst)
    assert not TERMINAL.search(rampenscenario.REGEL.replace("terminal", ""))
    mg = next(s for s in rampenscenario.SCENARIOS if s["id"] == "mediaguard_terugzetten")
    assert any("database" in t and "HARDE EIS" in t for t in mg["stappen"])
