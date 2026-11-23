"""Echte, geverifieerde export van de eigen ingebouwde Hub-database (B12-003, eigen deel).

Een back-up krijgt pas status ``geslaagd`` als **alle** controles slagen — nooit op alleen een exitcode:
1. ``pg_dump -Fc`` eindigt met 0 en schreef een niet-leeg bestand met de ``PGDMP``-header;
2. ``pg_restore --list`` kan de inhoudsopgave lezen en die bevat de verwachte tabellen (incl. data);
3. de SHA-256 is na het hernoemen opnieuw berekend en gelijk;
   daarbij leggen we per tabel het aantal rijen en een inhoudshash vast (``inhoud``), waarmee de hersteltest-robot de
   herstelde waarden vergelijkt (R-HARDE-EIS-5);
4. na de retentie zijn dezelfde export, inhoudsopgave, controlesom en herstelgegevens opnieuw gecontroleerd.
Automatische retentie geldt alleen voor gewone exports. Elke pre-upgrade-export behoudt ook zijn eigen
``.hold`` voor eerdere Hub-versies.
Het bestand staat in ``/appdata/backups`` met een ``.sha256``- en ``.json``-bestand ernaast (ook leesbaar als de
database zelf verloren is).
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.models import SelfBackup
from hub.timeutil import iso, utcnow

log = logging.getLogger("hub.backup")

EXPECTED_TABLES = ("alembic_version", "app_user", "decision", "audit_event")
PG_MAGIC = b"PGDMP"
FILE_RE = re.compile(r"^hub-(\d{8}T\d{6}Z)-[0-9a-f]{8}(?:[0-9a-f]{24})?\.dump$")
RETENTION_LOCK = 0x41534D424B50


@dataclass
class Verification:
    ok: bool
    reason_code: str | None
    message: str
    details: dict[str, Any]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _pg_env() -> dict[str, str]:
    """Vaste tijdzone voor pg_dump: de tekstvorm van timestamptz in de export en in de vergelijking is dan gelijk."""
    return {**os.environ, "PGTZ": "UTC"}


_COPY_RE = re.compile(rb"^COPY (\S+) .*FROM stdin;$")


def copy_inhoud(regels: Iterable[bytes]) -> dict[str, dict[str, Any]] | None:
    """Per tabel het aantal rijen en een inhoudshash uit de ``COPY``-blokken van een pg_dump-tekst. De hash is de som
    (mod 2**256) van de SHA-256 per rij: onafhankelijk van de volgorde, gevoelig voor elke gewijzigde waarde."""
    uit: dict[str, dict[str, Any]] = {}
    huidig: str | None = None
    som = 0
    for regel in regels:
        if huidig is None:
            m = _COPY_RE.match(regel.rstrip(b"\n"))
            if m:
                huidig, som = m.group(1).decode().replace('"', ""), 0
                uit[huidig] = {"rijen": 0, "sha256": ""}
        elif regel == b"\\.\n":
            uit[huidig]["sha256"] = f"{som:064x}"
            huidig = None
        else:
            uit[huidig]["rijen"] += 1
            som = (som + int.from_bytes(hashlib.sha256(regel.rstrip(b"\n")).digest())) % 2**256
    return uit if huidig is None and uit else None


def _stroom_inhoud(argv: list[str]) -> dict[str, dict[str, Any]] | None:
    try:
        with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=_pg_env()) as proc:
            assert proc.stdout is not None
            uit = copy_inhoud(proc.stdout)
    except OSError:
        return None
    return uit if proc.returncode == 0 else None


def dump_inhoud(path: Path, pg_restore_bin: str) -> dict[str, dict[str, Any]] | None:
    """Rijen en inhoudshash per tabel zoals ze in de export staan (gestreamd)."""
    return _stroom_inhoud([pg_restore_bin, "--data-only", "--file=-", str(path)])


def database_inhoud(libpq_url: str, pg_dump_bin: str) -> dict[str, dict[str, Any]] | None:
    """Rijen en inhoudshash per tabel van een (herstelde) database, met dezelfde pg_dump-tekstvorm als de export."""
    return _stroom_inhoud([pg_dump_bin, "--data-only", "--format=plain", f"--dbname={libpq_url}"])


def _tool_version(binary: str) -> str | None:
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip()[:128] or None


def verify_dump(path: Path, pg_restore_bin: str, expected_tables: tuple[str, ...] = EXPECTED_TABLES) -> Verification:
    if not path.exists():
        return Verification(False, "dump_missing", "Back-upbestand ontbreekt.", {})
    size = path.stat().st_size
    if size == 0:
        return Verification(False, "empty_dump", "Back-upbestand is leeg.", {"size": 0})
    with path.open("rb") as fh:
        magic = fh.read(5)
    if magic != PG_MAGIC:
        return Verification(False, "bad_magic", "Bestand is geen pg_dump-archief (custom-formaat).", {"size": size})
    try:
        proc = subprocess.run(
            [pg_restore_bin, "--list", str(path)], capture_output=True, text=True, timeout=300, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Verification(
            False, "restore_list_failed", f"pg_restore --list niet uitvoerbaar: {type(exc).__name__}", {}
        )
    if proc.returncode != 0:
        return Verification(
            False, "restore_list_failed", "pg_restore kan de inhoudsopgave niet lezen.", {"stderr": proc.stderr[-500:]}
        )
    entries = [ln for ln in proc.stdout.splitlines() if ln.strip() and not ln.lstrip().startswith(";")]
    missing = [t for t in expected_tables if not re.search(rf"\bTABLE DATA \S+ {re.escape(t)}\b", proc.stdout)]
    if missing:
        return Verification(
            False,
            "missing_tables",
            "Verwachte tabellen ontbreken in de back-up.",
            {"ontbrekend": missing, "entries": len(entries)},
        )
    return Verification(
        True, None, "Inhoudsopgave gelezen; verwachte tabellen aanwezig.", {"entries": len(entries), "size": size}
    )


def _schema_revision(db: Session) -> str | None:
    try:
        return db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        db.rollback()
        return None


def run_self_backup(db: Session, settings: Settings, *, trigger: str) -> SelfBackup:
    """Maak en verifieer een back-up. Commit zelf (ook bij mislukken) zodat het resultaat altijd zichtbaar is."""
    backups = settings.backups_dir
    backups.mkdir(mode=0o700, parents=True, exist_ok=True)
    backups.chmod(0o700)  # V-085: ook een bestaande map; de dumps bevatten de hele database
    started = utcnow()
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    row = SelfBackup(trigger=trigger, status="bezig", started_at=started, verification={})
    db.add(row)
    db.commit()
    name = f"hub-{stamp}-{row.id.hex}.dump"
    final = backups / name
    partial = backups / (name + ".partial")
    row.schema_revision = _schema_revision(db)
    row.tool_version = _tool_version(settings.pg_dump_bin)

    def fail(code: str, msg: str, details: dict[str, Any] | None = None) -> SelfBackup:
        with contextlib.suppress(FileNotFoundError):
            partial.unlink()
        row.status, row.reason_code, row.message = "mislukt", code, msg
        row.verification = details or {}
        row.finished_at = utcnow()
        db.commit()
        log.error("back-up mislukt: %s (%s)", msg, code)
        return row

    try:
        db_size = int(db.execute(text("SELECT pg_database_size(current_database())")).scalar() or 0)
    except Exception:
        db.rollback()
        db_size = 0
    free = shutil.disk_usage(backups).free
    if db_size and free < db_size * 2 + 50 * 1024 * 1024:
        return fail("insufficient_space", "Te weinig vrije ruimte in /appdata/backups.", {"vrij": free, "db": db_size})

    try:
        proc = subprocess.run(
            [
                settings.pg_dump_bin,
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                f"--file={partial}",
                f"--dbname={settings.libpq_url}",
            ],
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
            env=_pg_env(),
            umask=0o077,  # V-085: de dump is 0600 vanaf aanmaak, ongeacht de umask van het proces
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return fail("pg_dump_failed", f"pg_dump niet uitvoerbaar: {type(exc).__name__}")
    if proc.returncode != 0:
        return fail("pg_dump_failed", "pg_dump eindigde met een fout.", {"stderr": proc.stderr[-500:]})

    with partial.open("rb") as fh:
        os.fsync(fh.fileno())
    ver = verify_dump(partial, settings.pg_restore_bin)
    if not ver.ok:
        return fail(ver.reason_code or "verify_failed", ver.message, ver.details)
    inhoud = dump_inhoud(partial, settings.pg_restore_bin)
    if inhoud is None:
        return fail("restore_list_failed", "pg_restore kan de gegevens van de export niet lezen.")
    digest = sha256_file(partial)
    os.replace(partial, final)
    if sha256_file(final) != digest:
        return fail("checksum_unstable", "Checksum veranderde na het wegschrijven.")
    checksum_file = backups / (name + ".sha256")
    checksum_file.write_text(f"{digest}  {name}\n")
    manifest = {
        "bestand": name,
        "sha256": digest,
        "grootte_bytes": final.stat().st_size,
        "schema_revisie": row.schema_revision,
        "pg_dump": row.tool_version,
        "gemaakt_op": iso(utcnow()),
        "aanleiding": trigger,
        "verificatie": {
            "pg_restore_list_entries": ver.details.get("entries"),
            "tabellen": list(EXPECTED_TABLES),
            "inhoud": inhoud,
        },
    }
    manifest_file = backups / (name + ".json")
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
    # Alleen de afronding is serieel. Andere exports kunnen hun dump intussen schrijven.
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": RETENTION_LOCK})
    row.status, row.reason_code, row.message = (
        "geslaagd",
        None,
        "Back-up gemaakt en geverifieerd (pg_restore --list + SHA-256).",
    )
    row.file_name, row.size_bytes, row.sha256 = name, final.stat().st_size, digest
    row.toc_entries = int(ver.details.get("entries") or 0)
    row.verification = {
        "pg_restore_list": "ok",
        "entries": ver.details.get("entries"),
        "sha256_herberekend": True,
        "inhoud": inhoud,
    }
    try:
        apply_retention(db, settings, keep_id=None if trigger == "pre-upgrade" else row.id)
        verification = reverify(db, settings, row)
        if not verification.ok:
            return fail(verification.reason_code or "verify_failed", verification.message, verification.details)
        if checksum_file.read_text().split() != [digest, name] or json.loads(manifest_file.read_text()) != manifest:
            return fail("metadata_mismatch", "De herstelgegevens horen niet bij de zojuist gemaakte export.")
        if trigger == "pre-upgrade":
            (backups / (name + ".hold")).write_text("pre-upgrade\n")
    except (OSError, ValueError):
        return fail("backup_unavailable", "Opruimen of controleren van de export en de herstelgegevens is mislukt.")
    row.finished_at = utcnow()
    db.commit()
    log.info("back-up geslaagd: %s (%s bytes, sha256 %s)", name, row.size_bytes, digest[:12])
    return row


def reverify(db: Session, settings: Settings, row: SelfBackup) -> Verification:
    if row.status != "geslaagd" or not row.file_name or row.deleted_at is not None:
        return Verification(False, "not_available", "Deze back-up is niet (meer) beschikbaar.", {})
    path = settings.backups_dir / row.file_name
    ver = verify_dump(path, settings.pg_restore_bin)
    if not ver.ok:
        return ver
    actual = sha256_file(path)
    if actual != row.sha256:
        return Verification(
            False,
            "checksum_mismatch",
            "Checksum wijkt af van de vastgelegde waarde.",
            {"verwacht": row.sha256, "gevonden": actual},
        )
    return Verification(True, None, "Opnieuw geverifieerd: checksum en inhoudsopgave kloppen.", ver.details)


def apply_retention(db: Session, settings: Settings, *, keep_id: uuid.UUID | None) -> list[str]:
    """Bewaar het ingestelde aantal gewone exports, inclusief de gewone export die nu wordt afgerond."""
    candidates = select(SelfBackup).where(
        SelfBackup.trigger.in_(("manual", "schedule")), SelfBackup.status == "geslaagd", SelfBackup.deleted_at.is_(None)
    )
    places = settings.self_backup_keep
    if keep_id is not None:
        candidates = candidates.where(SelfBackup.id != keep_id)
        places -= 1
    rows = db.scalars(candidates.order_by(SelfBackup.started_at.desc(), SelfBackup.id.desc()).offset(places))
    removed: list[str] = []
    for old in rows:
        if old.file_name:
            for suffix in ("", ".sha256", ".json"):
                with contextlib.suppress(FileNotFoundError):
                    (settings.backups_dir / (old.file_name + suffix)).unlink()
            removed.append(old.file_name)
        old.deleted_at = utcnow()
    return removed


def verify_pre_upgrade(db: Session, settings: Settings, export_id: uuid.UUID) -> Verification:
    """Controleer het herstelpunt dat backup-now in deze upgradebeurt heeft teruggegeven."""
    row = db.get(SelfBackup, export_id)
    if row is None or row.trigger != "pre-upgrade" or not row.file_name or not FILE_RE.fullmatch(row.file_name):
        return Verification(False, "not_available", "Geen pre-upgrade-export met de opgegeven identiteit.", {})
    path = settings.backups_dir / row.file_name
    try:
        result = reverify(db, settings, row)
        if not result.ok:
            return result
        checksum = path.with_suffix(".dump.sha256").read_text().split()
        manifest = json.loads(path.with_suffix(".dump.json").read_text())
        if (
            not path.with_suffix(".dump.hold").is_file()
            or checksum != [row.sha256, row.file_name]
            or not isinstance(manifest, dict)
            or manifest.get("bestand") != row.file_name
            or manifest.get("sha256") != row.sha256
            or manifest.get("aanleiding") != row.trigger
            or manifest.get("schema_revisie") != row.schema_revision
            or manifest.get("grootte_bytes") != row.size_bytes
        ):
            return Verification(False, "metadata_mismatch", "De herstelgegevens horen niet bij deze export.", {})
        return result
    except (OSError, ValueError):
        return Verification(False, "backup_unavailable", "De export of de herstelgegevens zijn onleesbaar.", {})


def latest_verified(db: Session) -> SelfBackup | None:
    return db.scalars(
        select(SelfBackup)
        .where(
            SelfBackup.status == "geslaagd",
            SelfBackup.deleted_at.is_(None),
            # Een afgekeurde herverificatie (bv. dump_missing) maakt de export ongeldig als herstelbewijs (R-VEILIG-2).
            SelfBackup.verification["herverificatie"]["ok"].as_boolean().is_not(False),
        )
        .order_by(SelfBackup.finished_at.desc())
        .limit(1)
    ).first()


def to_dict(row: SelfBackup) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "aanleiding": row.trigger,
        "status": row.status,
        "reason_code": row.reason_code,
        "melding": row.message,
        "bestand": row.file_name,
        "grootte_bytes": row.size_bytes,
        "sha256": row.sha256,
        "inhoudsopgave_items": row.toc_entries,
        "schema_revisie": row.schema_revision,
        "pg_dump": row.tool_version,
        "verificatie": row.verification,
        "gestart_op": iso(row.started_at),
        "beeindigd_op": iso(row.finished_at),
        "verwijderd_op": iso(row.deleted_at),
    }
