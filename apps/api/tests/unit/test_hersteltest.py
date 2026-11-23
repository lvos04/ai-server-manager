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


def test_inhoudshash_per_tabel_volgorde_maakt_niet_uit_elke_waarde_wel() -> None:
    """R-HARDE-EIS-5: aantal en hash per tabel uit de COPY-blokken; een andere waarde bij gelijk aantal is anders."""
    from hub.backup.selfbackup import copy_inhoud

    def blok(*rijen: bytes) -> list[bytes]:
        return [b"SET x = 1;\n", b"COPY public.kijk (a, b) FROM stdin;\n", *(r + b"\n" for r in rijen), b"\\.\n"]

    a = copy_inhoud(blok(b"1\t120", b"2\t345"))
    assert a is not None and a["public.kijk"]["rijen"] == 2
    assert copy_inhoud(blok(b"2\t345", b"1\t120")) == a
    assert copy_inhoud(blok(b"1\t121", b"2\t345")) != a
    assert (
        copy_inhoud(blok(b"1\t120", b"1\t120"))["public.kijk"] != copy_inhoud(blok(b"2\t345", b"2\t345"))["public.kijk"]
    )  # type: ignore[index]
    assert copy_inhoud(blok(b"1\t120")[:-1]) is None  # afgebroken blok
    assert copy_inhoud([]) is None


@pytest.mark.parametrize(
    "verwacht",
    [None, {}, {"t": {"rijen": 1}}, {"t": {"rijen": True, "sha256": "a" * 64}}, {"t": {"rijen": 1, "sha256": "x"}}],
)
def test_zonder_geldige_vastgelegde_inhoud_geen_herstel(verwacht: object, tmp_path: Path) -> None:
    pad = tmp_path / "x.dump"
    uit = ht.herstel_in("postgresql://niet-gebruikt@/x", pad, "pg_restore", verwacht if verwacht is not None else {})
    assert (uit.resultaat, uit.reden) == ("onbekend", "inhoud_onbekend")


def test_poolverlies_bewaart_de_schijven_en_stopt_zonder_doel_en_back_up() -> None:
    """R-HARDE-EIS-10: de oorspronkelijke schijven blijven terugval; eerst een apart doel en een bruikbare back-up met
    de appgegevens, en stoppen als dat ontbreekt. Pas daarna een nieuwe pool, nooit op de oorspronkelijke schijven."""
    stappen = next(s for s in rampenscenario.SCENARIOS if s["id"] == "poolverlies")["stappen"]

    def eerste(*woorden: str) -> int:
        return next(i for i, t in enumerate(stappen) if all(w in t for w in woorden))

    bewaar = eerste("oorspronkelijke schijven", "onaangeroerd")
    doel, backup = eerste("apart doel"), eerste("back-up met de appgegevens")
    stop, nieuw = eerste("STOP", "ontbreekt"), eerste("nieuwe pool aan")
    assert bewaar < doel < backup < stop < nieuw
    assert "aparte doel" in stappen[nieuw]
    assert not any("pool opnieuw aan" in t for t in stappen)


def test_verhuizing_noemt_de_ondertekensleutels_en_herkoppeling() -> None:
    """R-HARDE-EIS-7: de verhuizing bewaart naast de vault-sleutel ook de ondertekensleutels van de Hub, of koppelt
    elke dienst gecontroleerd opnieuw; de natest eist dat bestaande diensten nieuwe berichten aanvaarden."""
    s = next(s for s in rampenscenario.SCENARIOS if s["id"] == "verhuizing")
    tekst = " ".join(s["stappen"])
    assert all(n in tekst for n in rampenscenario.VERHUIS_GEHEIMEN) and "opnieuw met een nieuwe koppelcode" in tekst
    assert any("aanvaardt een nieuw ondertekend bericht" in t for t in s["natest"])
