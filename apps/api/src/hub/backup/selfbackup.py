"""Echte, geverifieerde export van de eigen ingebouwde Hub-database (B12-003, eigen deel).

Een back-up krijgt pas status ``geslaagd`` als **alle** controles slagen — nooit op alleen een exitcode:
1. ``pg_dump -Fc`` eindigt met 0 en schreef een niet-leeg bestand met de ``PGDMP``-header;
2. ``pg_restore --list`` kan de inhoudsopgave lezen en die bevat de verwachte tabellen (incl. data);
3. de SHA-256 is na het hernoemen opnieuw berekend en gelijk.
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
FILE_RE = re.compile(r"^hub-(\d{8}T\d{6}Z)-[0-9a-f]{8}\.dump$")


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
    backups.mkdir(parents=True, exist_ok=True)
    started = utcnow()
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    row = SelfBackup(trigger=trigger, status="bezig", started_at=started, verification={})
    db.add(row)
    db.commit()
    name = f"hub-{stamp}-{row.id.hex[:8]}.dump"
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
    digest = sha256_file(partial)
    os.replace(partial, final)
    if sha256_file(final) != digest:
        return fail("checksum_unstable", "Checksum veranderde na het wegschrijven.")
    (backups / (name + ".sha256")).write_text(f"{digest}  {name}\n")
    manifest = {
        "bestand": name,
        "sha256": digest,
        "grootte_bytes": final.stat().st_size,
        "schema_revisie": row.schema_revision,
        "pg_dump": row.tool_version,
        "gemaakt_op": iso(utcnow()),
        "aanleiding": trigger,
        "verificatie": {"pg_restore_list_entries": ver.details.get("entries"), "tabellen": list(EXPECTED_TABLES)},
    }
    (backups / (name + ".json")).write_text(json.dumps(manifest, indent=2) + "\n")
    row.status, row.reason_code, row.message = (
        "geslaagd",
        None,
        "Back-up gemaakt en geverifieerd (pg_restore --list + SHA-256).",
    )
    row.file_name, row.size_bytes, row.sha256 = name, final.stat().st_size, digest
    row.toc_entries = int(ver.details.get("entries") or 0)
    row.verification = {"pg_restore_list": "ok", "entries": ver.details.get("entries"), "sha256_herberekend": True}
    row.finished_at = utcnow()
    db.commit()
    apply_retention(db, settings)
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


def apply_retention(db: Session, settings: Settings) -> list[str]:
    rows = list(
        db.scalars(
            select(SelfBackup)
            .where(SelfBackup.status == "geslaagd", SelfBackup.deleted_at.is_(None))
            .order_by(SelfBackup.started_at.desc())
        )
    )
    removed: list[str] = []
    for old in rows[settings.self_backup_keep :]:
        if old.file_name:
            for suffix in ("", ".sha256", ".json"):
                with contextlib.suppress(FileNotFoundError):
                    (settings.backups_dir / (old.file_name + suffix)).unlink()
            removed.append(old.file_name)
        old.deleted_at = utcnow()
    db.commit()
    return removed


def latest_verified(db: Session) -> SelfBackup | None:
    return db.scalars(
        select(SelfBackup)
        .where(SelfBackup.status == "geslaagd", SelfBackup.deleted_at.is_(None))
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
