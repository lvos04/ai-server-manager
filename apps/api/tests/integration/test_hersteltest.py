"""Hersteltest-robot en rampenscenario-oefening op echte PostgreSQL 16 (B12-005, B12-007, EX13; S-P2-100).

Echte ``pg_dump``-export, echte ``pg_restore`` in een proefdatabase en per tabel aantal en inhoudshash. De externe
back-up (OneDrive) is hier een map die een download nabootst: Sim-getest, geen echt account.
"""

from __future__ import annotations

import os
import select
import shutil
import struct
import subprocess
import sys
import uuid
import zlib
from pathlib import Path
from typing import Any

import psycopg
import pytest
from conftest import ADMIN_URL
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

pytestmark = pytest.mark.integration


def _export(settings: Any, app: Any) -> Any:
    from hub.backup.selfbackup import run_self_backup

    with app.state.sessionmaker() as db:
        row = run_self_backup(db, settings, trigger="manual")
        assert row.status == "geslaagd", row.message
        db.expunge(row)
        return row


def _proefdatabases() -> list[str]:
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        return [r[0] for r in conn.execute("SELECT datname FROM pg_database WHERE datname LIKE 'hersteltest_%'")]


def _flip(pad: Path) -> None:
    with pad.open("r+b") as fh:
        fh.seek(-1, os.SEEK_END)
        last = fh.read(1)
        fh.seek(-1, os.SEEK_END)
        fh.write(bytes([last[0] ^ 0xFF]))


def test_export_in_proefdatabase_gelijke_aantallen_en_altijd_opgeruimd(admin: Any, settings: Any, app: Any) -> None:
    from hub.backup import hersteltest as ht

    row = _export(settings, app)
    voor = set(_proefdatabases())
    pad = settings.backups_dir / row.file_name
    uit = ht.toets_dumpbestand(settings, pad, settings.backups_dir, row.sha256)
    assert (uit.resultaat, uit.reden) == ("geslaagd", None), uit
    tel = uit.bewijs["tellingen"]
    assert tel["public.app_user"] >= 1 and tel["public.audit_event"] >= 1 and uit.bewijs["sha256"] == row.sha256
    assert set(_proefdatabases()) == voor  # V-013: de proefdatabase is weer weg

    # Kapotte checksum: mislukt, zonder dat er een proefdatabase komt.
    _flip(pad)
    uit = ht.toets_dumpbestand(settings, pad, settings.backups_dir, row.sha256)
    assert (uit.resultaat, uit.reden) == ("mislukt", "checksum_afwijkend")
    assert set(_proefdatabases()) == voor


def test_bronpad_via_symbolische_koppeling_geweigerd(settings: Any, app: Any, tmp_path: Path) -> None:
    """V-095: een koppeling in een bovenliggende map of naar buiten de wortel telt niet."""
    from hub.backup import hersteltest as ht

    row = _export(settings, app)
    echt = settings.backups_dir / row.file_name
    wortel = tmp_path / "wortel"
    (wortel / "echt").mkdir(parents=True)
    shutil.copy(echt, wortel / "echt" / "x.dump")
    shutil.copy(echt.with_name(echt.name + ".json"), wortel / "echt" / "x.dump.json")
    (wortel / "via").symlink_to(wortel / "echt")
    (wortel / "naar-buiten.dump").symlink_to(echt)
    for pad in (wortel / "via" / "x.dump", wortel / "naar-buiten.dump", echt):
        uit = ht.toets_dumpbestand(settings, pad, wortel, row.sha256)
        assert (uit.resultaat, uit.reden) == ("mislukt", "bronpad_ongeldig"), pad
    assert ht.toets_dumpbestand(settings, wortel / "echt" / "x.dump", wortel, row.sha256).resultaat == "geslaagd"


def _png(breedte: int, hoogte: int, pixels: bytes) -> bytes:
    """Een geldige PNG (8-bit RGB, filter 0) als synthetische foto."""

    def blok(soort: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + soort + data + struct.pack(">I", zlib.crc32(soort + data))

    regels = b"".join(b"\0" + pixels[y * breedte * 3 : (y + 1) * breedte * 3] for y in range(hoogte))
    kop = struct.pack(">IIBBBBB", breedte, hoogte, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + blok(b"IHDR", kop) + blok(b"IDAT", zlib.compress(regels)) + blok(b"IEND", b"")


def _open_foto(data: bytes) -> tuple[int, int, bytes]:
    """Decodeer een PNG (8-bit RGB): controleert handtekening, elke CRC, de zlib-stroom en de scanlijnen en geeft
    breedte, hoogte en pixels. Een onleesbare foto geeft ``ValueError``."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("geen PNG")
    pos, kop, idat = 8, None, b""
    while pos < len(data):
        if pos + 12 > len(data):
            raise ValueError("afgekapt")
        (lengte,) = struct.unpack(">I", data[pos : pos + 4])
        soort, inhoud = data[pos + 4 : pos + 8], data[pos + 8 : pos + 8 + lengte]
        (crc,) = struct.unpack(">I", data[pos + 8 + lengte : pos + 12 + lengte] or b"\0\0\0\0")
        if len(inhoud) != lengte or zlib.crc32(soort + inhoud) != crc:
            raise ValueError("CRC wijkt af")
        pos += 12 + lengte
        if soort == b"IHDR":
            kop = struct.unpack(">IIBBBBB", inhoud)
        elif soort == b"IDAT":
            idat += inhoud
        elif soort == b"IEND":
            break
    if kop is None or kop[2:] != (8, 2, 0, 0, 0):
        raise ValueError("kop ontbreekt of niet ondersteund")
    breedte, hoogte = kop[0], kop[1]
    try:
        ruw = zlib.decompress(idat)
    except zlib.error as exc:
        raise ValueError("beeldgegevens onleesbaar") from exc
    stap = breedte * 3
    if len(ruw) != hoogte * (stap + 1) or any(ruw[y * (stap + 1)] != 0 for y in range(hoogte)):
        raise ValueError("verkeerde grootte of scanlijnfilter")  # de synthetische foto gebruikt alleen filter 0
    uit = b"".join(ruw[y * (stap + 1) + 1 : (y + 1) * (stap + 1)] for y in range(hoogte))
    return breedte, hoogte, uit


def test_ex13_externe_back_up_exacte_inhoud_en_database_integriteit(settings: Any, app: Any, tmp_path: Path) -> None:
    """EX13 (Sim): een 'download' van de externe back-up (export met .sha256 en .json, en een foto) in een eigen map.
    De foto is een geldige synthetische PNG: de download moet decoderen tot dezelfde pixels; een beschadigde foto is
    onleesbaar. De export telt alleen bij exact gelijke inhoud en een geslaagd herstel met gelijke aantallen en
    inhoudshashes per tabel; een beschadigde download faalt (R-HARDE-EIS-9)."""
    from hub.backup import hersteltest as ht
    from hub.backup.selfbackup import sha256_file

    row = _export(settings, app)
    bron = settings.backups_dir
    breedte, hoogte = 24, 16
    pixels = bytes((x * 10 + y * 3 + k * 70) & 255 for y in range(hoogte) for x in range(breedte) for k in range(3))
    foto = tmp_path / "foto-2019.png"
    foto.write_bytes(_png(breedte, hoogte, pixels))
    assert _open_foto(foto.read_bytes()) == (breedte, hoogte, pixels)  # de bron zelf is een geldige foto
    download = tmp_path / "onedrive-sim"
    download.mkdir()
    for naam in (row.file_name, row.file_name + ".sha256", row.file_name + ".json"):
        shutil.copy(bron / naam, download / naam)
    shutil.copy(foto, download / foto.name)

    assert sha256_file(download / foto.name) == sha256_file(foto)  # exacte inhoud van de foto
    assert _open_foto((download / foto.name).read_bytes()) == (breedte, hoogte, pixels)  # opent, zelfde beeld
    kapot = bytearray((download / foto.name).read_bytes())
    kapot[len(kapot) // 2] ^= 0xFF  # één beschadigd byte in de beeldgegevens
    with pytest.raises(ValueError):
        _open_foto(bytes(kapot))
    with pytest.raises(ValueError):
        _open_foto(bytes(kapot[: len(kapot) // 2]))  # afgebroken download

    verwacht = (download / (row.file_name + ".sha256")).read_text().split()[0]
    assert verwacht == row.sha256
    uit = ht.toets_dumpbestand(settings, download / row.file_name, download, verwacht)
    assert (uit.resultaat, uit.reden) == ("geslaagd", None), uit

    _flip(download / row.file_name)
    uit = ht.toets_dumpbestand(settings, download / row.file_name, download, verwacht)
    assert (uit.resultaat, uit.reden) == ("mislukt", "checksum_afwijkend")


def test_onleesbare_export_is_mislukt(settings: Any, app: Any) -> None:
    """R-HARDE-EIS-2: een export die bestaat maar niet te lezen is, is mislukt (geen fout die de afkeuring
    overslaat)."""
    from hub.backup import hersteltest as ht

    row = _export(settings, app)
    pad = settings.backups_dir / row.file_name
    pad.chmod(0)
    try:
        if os.access(pad, os.R_OK):
            pytest.skip("draait met rechten die elk bestand kunnen lezen")
        uit = ht.toets_dumpbestand(settings, pad, settings.backups_dir, row.sha256)
    finally:
        pad.chmod(0o600)
    assert (uit.resultaat, uit.reden) == ("mislukt", "export_onleesbaar")
    pad.with_name(pad.name + ".json").unlink()  # herstelgegevens weg: ook onleesbaar, nooit geslaagd
    uit = ht.toets_dumpbestand(settings, pad, settings.backups_dir, row.sha256)
    assert (uit.resultaat, uit.reden) == ("mislukt", "export_onleesbaar")


def test_gewijzigde_waarden_bij_gelijk_aantal_rijen_zijn_mislukt(
    settings: Any, app: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-HARDE-EIS-5: aantallen en inhoudshash per tabel liggen vast bij het maken van de export. Een herstelde kopie
    met andere hervatwaarde en voortgang bij hetzelfde aantal rijen is mislukt; een gelijke kopie is geslaagd en de
    kijkgegevens en de voortgang staan er precies in."""
    from hub.backup import hersteltest as ht

    kijk = [(1, "kijker", True, 120, True, 9, 2, 1), (2, "beheerder", False, 345, False, 6, 1, 3)]
    with psycopg.connect(settings.libpq_url) as conn:
        conn.execute(
            "CREATE TABLE proef_kijk (gebruiker int PRIMARY KEY, rol text, gezien bool, hervat int, favoriet bool, "
            "beoordeling int, audiospoor int, ondertitelspoor int)"
        )
        conn.execute("CREATE TABLE proef_taak (taak int PRIMARY KEY, voortgang int, gezien_op timestamptz)")
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO proef_kijk VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", kijk)
        conn.execute("INSERT INTO proef_taak VALUES (1, 17, '2026-11-23 10:00+01'), (2, 41, NULL)")
    try:
        row = _export(settings, app)
        inhoud = row.verification["inhoud"]
        assert inhoud["public.proef_kijk"]["rijen"] == 2 and len(inhoud["public.proef_kijk"]["sha256"]) == 64
        pad = settings.backups_dir / row.file_name

        uit = ht.toets_dumpbestand(settings, pad, settings.backups_dir, row.sha256, inhoud)
        assert (uit.resultaat, uit.reden) == ("geslaagd", None), uit

        echt = ht._tabel_tellingen

        def wijzig_in_de_proef(conn: Any, tabellen: list[str]) -> Any:
            conn.execute("UPDATE proef_kijk SET hervat = 121 WHERE gebruiker = 1")
            conn.execute("UPDATE proef_taak SET voortgang = 18 WHERE taak = 1")
            return echt(conn, tabellen)

        monkeypatch.setattr(ht, "_tabel_tellingen", wijzig_in_de_proef)
        uit = ht.toets_dumpbestand(settings, pad, settings.backups_dir, row.sha256, inhoud)
        assert (uit.resultaat, uit.reden) == ("mislukt", "inhoud_wijkt_af"), uit
        assert uit.bewijs["tabellen"] == ["public.proef_kijk", "public.proef_taak"]
        # Zonder vastgelegde inhoud (oudere export) is er geen positief bewijs.
        uit = ht.toets_dumpbestand(settings, pad, settings.backups_dir, row.sha256, {})
        assert (uit.resultaat, uit.reden) == ("onbekend", "inhoud_onbekend")
        with psycopg.connect(settings.libpq_url) as conn:  # productie onaangeroerd
            assert conn.execute("SELECT * FROM proef_kijk ORDER BY gebruiker").fetchall() == kijk
    finally:
        with psycopg.connect(settings.libpq_url) as conn:
            conn.execute("DROP TABLE proef_kijk, proef_taak")


def _bestaat(naam: str) -> bool:
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        return conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (naam,)).fetchone() is not None


def test_achtergebleven_proefdatabase_na_processtop_wordt_opgeruimd_andere_blijft(settings: Any) -> None:
    """R-HARDE-EIS-6: na SIGTERM blijft een gevulde proefdatabase achter; de volgende proef (zoals na een herstart)
    ruimt alleen die aantoonbaar eigen database op. Een bestaande database met dezelfde naamvorm maar zonder het eigen
    merkteken, en een met het merkteken van een andere Hub, blijven staan."""
    from hub.backup import hersteltest as ht

    kind = (
        "import sys, psycopg\nfrom hub.backup.hersteltest import proefdatabase\n"
        "from psycopg.conninfo import conninfo_to_dict\n"
        "with proefdatabase(sys.argv[1]) as doel:\n"
        " with psycopg.connect(doel) as conn:\n"
        "  conn.execute('CREATE TABLE proefrij (n int)')\n"
        "  conn.execute('INSERT INTO proefrij VALUES (37)')\n"
        " print(conninfo_to_dict(doel)['dbname'], flush=True)\n sys.stdin.read()\n"
    )
    with subprocess.Popen(
        [sys.executable, "-c", kind, settings.libpq_url], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    ) as proces:
        try:
            assert proces.stdout is not None and select.select([proces.stdout], [], [], 30)[0]
            rest = proces.stdout.readline().strip()
        finally:
            proces.terminate()
            proces.wait(timeout=10)
    assert ht.PROEF_RE.fullmatch(rest) and _bestaat(rest)  # SIGTERM: geen opruimen in het proces zelf

    vreemd, ander_merk = f"hersteltest_{uuid.uuid4().hex[:12]}", f"hersteltest_{uuid.uuid4().hex[:12]}"
    with psycopg.connect(settings.libpq_url, autocommit=True) as conn:
        for naam in (vreemd, ander_merk):
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(naam)))
        conn.execute(
            sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(ander_merk), sql.Literal(f"{ht.MERK}: een_andere_hub")
            )
        )
    try:
        with ht.proefdatabase(settings.libpq_url) as doel:  # de volgende proef, zoals na een herstart
            assert not _bestaat(rest)
            assert _bestaat(conninfo_to_dict(doel)["dbname"])
            assert _bestaat(vreemd) and _bestaat(ander_merk)
        assert _bestaat(vreemd) and _bestaat(ander_merk)
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            for naam in (rest, vreemd, ander_merk):
                conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(naam)))


def test_rampenscenario_oefening_hub_database_vault_en_koppelingen(settings: Any, app: Any, tmp_path: Path) -> None:
    """B12-007: oefening zonder de oorspronkelijke NAS. De export van een Hub met een geheim in de vault en een
    TrueNAS-koppeling gaat in een nieuwe database ('andere hardware'); met de bewaarde vault-sleutel opent de nieuwe
    Hub het geheim weer en staan de koppelingen er; alle tabellen hebben dezelfde aantallen."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from hub.backup import hersteltest as ht
    from hub.models import TrueNASConnection
    from hub.vault import Vault

    vault: Vault = app.state.vault()
    ref = "vault://truenas/api-key"
    with app.state.sessionmaker() as db:
        vault.put(db, ref, "oefensleutel-alleen-test-7731", actor="test")  # gitleaks:allow -- testwaarde
        db.merge(TrueNASConnection(id=1, api_key_ref=ref, pinned_fingerprint="ab" * 32, pinned_for_url="wss://nas"))
        db.commit()
    row = _export(settings, app)

    # 'Nieuwe hardware': alleen de export en de apart bewaarde vault-sleutel gaan mee.
    sleutel = tmp_path / "nieuw" / "vault.key"
    sleutel.parent.mkdir()
    shutil.copy(settings.secrets_dir / "vault.key", sleutel)
    with ht.proefdatabase(settings.libpq_url) as doel:
        uit = ht.herstel_in(doel, settings.backups_dir / row.file_name, settings.pg_restore_bin)
        assert (uit.resultaat, uit.reden) == ("geslaagd", None), uit
        engine = create_engine("postgresql+psycopg://", creator=lambda: psycopg.connect(doel))
        try:
            with Session(engine) as nieuw:
                assert Vault.from_file(sleutel).get(nieuw, ref) == "oefensleutel-alleen-test-7731"
                k = nieuw.get(TrueNASConnection, 1)
                assert k is not None and (k.api_key_ref, k.pinned_fingerprint) == (ref, "ab" * 32)
        finally:
            engine.dispose()
    assert not [d for d in _proefdatabases() if f"dbname={d}" in doel]


def test_verhuizing_met_bewaarde_geheimen_behoudt_dienstkoppelingen(settings: Any, app: Any, tmp_path: Path) -> None:
    """R-HARDE-EIS-7: oefening van het scenario 'verhuizing'. Met de export en precies de geheimenbestanden uit het
    scenario aanvaardt een bestaande dienst een nieuw ondertekend bericht van de nieuwe Hub. Met alleen de
    vault-sleutel weigert hij (unknown_key): dan is herkoppelen per dienst nodig, zoals het scenario zegt."""
    from executor.hublink import AuthFailed, verify_hub_jwt

    from hub.backup import hersteltest as ht
    from hub.backup.rampenscenario import SCENARIOS, VERHUIS_GEHEIMEN
    from hub.firststart import ensure_secrets
    from hub.keys import KeyRing
    from hub.models import Service

    stappen = " ".join(next(s for s in SCENARIOS if s["id"] == "verhuizing")["stappen"])
    assert all(naam in stappen for naam in VERHUIS_GEHEIMEN)
    dienst, sid = "verhuisproef", uuid.uuid4()
    with app.state.sessionmaker() as db:
        db.add(Service(id=sid, app_id=dienst, enrolled_via="koppelcode"))
        db.commit()
    row = _export(settings, app)
    pin = app.state.keyring().jwks()["keys"][0]
    koppeling = {"state": "gekoppeld", "service_id": str(sid), "pins": {"jwt": [{"kid": pin["kid"], "jwk": pin}]}}

    def antwoord(ring: Any) -> str:
        token, _ = ring.issue_hub_service_jwt(audience=dienst, service_id=str(sid))
        try:
            verify_hub_jwt(token, koppeling, audience=dienst)
        except AuthFailed as exc:
            return str(exc.reason)
        return "aanvaard"

    def nieuwe_hub(naam: str, bestanden: tuple[str, ...]) -> Any:
        map_ = tmp_path / naam
        map_.mkdir(mode=0o700)
        for b in bestanden:
            shutil.copy(settings.secrets_dir / b, map_ / b)
        ensure_secrets(map_, new_setup_code=False)  # eerste start: wat ontbreekt, wordt nieuw gemaakt
        return KeyRing.load(map_)

    with ht.proefdatabase(settings.libpq_url) as doel:
        assert (
            ht.herstel_in(doel, settings.backups_dir / row.file_name, settings.pg_restore_bin).resultaat == "geslaagd"
        )
        with psycopg.connect(doel) as conn:
            assert conn.execute("SELECT app_id FROM service WHERE id = %s", (sid,)).fetchone() == (dienst,)
    assert antwoord(nieuwe_hub("volgens-scenario", VERHUIS_GEHEIMEN)) == "aanvaard"
    assert antwoord(nieuwe_hub("alleen-vault", ("vault.key",))) == "unknown_key"
