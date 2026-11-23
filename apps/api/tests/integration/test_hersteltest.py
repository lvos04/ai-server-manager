"""Hersteltest-robot en rampenscenario-oefening op echte PostgreSQL 16 (B12-005, B12-007, EX13; S-P2-100).

Echte ``pg_dump``-export, echte ``pg_restore`` in een proefdatabase en tellingen per tabel. De externe back-up
(OneDrive) is hier een map die een download nabootst: Sim-getest, geen echt account.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import psycopg
import pytest
from conftest import ADMIN_URL

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
    (wortel / "via").symlink_to(wortel / "echt")
    (wortel / "naar-buiten.dump").symlink_to(echt)
    for pad in (wortel / "via" / "x.dump", wortel / "naar-buiten.dump", echt):
        uit = ht.toets_dumpbestand(settings, pad, wortel, row.sha256)
        assert (uit.resultaat, uit.reden) == ("mislukt", "bronpad_ongeldig"), pad
    assert ht.toets_dumpbestand(settings, wortel / "echt" / "x.dump", wortel, row.sha256).resultaat == "geslaagd"


def test_ex13_externe_back_up_exacte_inhoud_en_database_integriteit(settings: Any, app: Any, tmp_path: Path) -> None:
    """EX13 (Sim): een 'download' van de externe back-up (export, .sha256 en een foto) in een eigen map. Alleen bij
    exact gelijke inhoud en een geslaagd herstel met gelijke aantallen telt het; een beschadigde download faalt."""
    from hub.backup import hersteltest as ht
    from hub.backup.selfbackup import sha256_file

    row = _export(settings, app)
    bron = settings.backups_dir
    foto = tmp_path / "foto-2019.jpg"
    foto.write_bytes(b"\xff\xd8\xff\xe0" + os.urandom(2048) + b"\xff\xd9")
    download = tmp_path / "onedrive-sim"
    download.mkdir()
    for naam in (row.file_name, row.file_name + ".sha256"):
        shutil.copy(bron / naam, download / naam)
    shutil.copy(foto, download / foto.name)

    assert sha256_file(download / foto.name) == sha256_file(foto)  # exacte inhoud van de foto
    verwacht = (download / (row.file_name + ".sha256")).read_text().split()[0]
    assert verwacht == row.sha256
    uit = ht.toets_dumpbestand(settings, download / row.file_name, download, verwacht)
    assert (uit.resultaat, uit.reden) == ("geslaagd", None), uit

    _flip(download / row.file_name)
    uit = ht.toets_dumpbestand(settings, download / row.file_name, download, verwacht)
    assert (uit.resultaat, uit.reden) == ("mislukt", "checksum_afwijkend")


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
