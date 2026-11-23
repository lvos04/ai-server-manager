"""Hersteltest-robot (B12-005, EX13, EX14; S-P2-100).

De robot controleert of een herstelpunt (B12-006) echt terug te zetten is, zonder productie aan te raken:

1. **Kloon in de zandbak.** Per dataset van het herstelpunt een uitgevoerde ``zfs.snapshot.clone_to_sandbox`` (R1, via
   voorstel → executor) van precies die snapshot naar ``<pool>/asm-sandbox/<naam>``, teruggelezen als aanwezig. De
   robot klont zelf niets en zet nooit een snapshot terug op productie: dat staat niet op de vaste lijst.
2. **Database-export in een proefdatabase.** De export (``pg_dump``) moet dezelfde SHA-256 hebben als vastgelegd; dan
   herstelt ``pg_restore`` hem in een eigen proefdatabase ``hersteltest_<id>`` en telt de robot per tabel de rijen in
   de export en in de herstelde kopie (HARDE EIS: kijkgeschiedenis en voortgang tellen mee als tabel). Daarna gaat de
   proefdatabase altijd weg.
3. **Productie onveranderd.** Een vingerafdruk van de productiedatabase vóór en na; een verschil is ``mislukt``.

Positief bewijs: alleen een kloon van elke dataset, een gelijke checksum, gelijke aantallen per tabel en een
onveranderde productie geven ``geslaagd``. Een kapotte checksum of afwijkende inhoud is ``mislukt`` en maakt het
herstelpunt ``ongezond`` (de pre-update-gate gaat dicht). Wat niet te meten is, is ``onbekend``; ``onbekend`` maakt
een herstelpunt nooit beter.
"""

from __future__ import annotations

import contextlib
import hashlib
import math
import re
import subprocess
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from sqlalchemy.orm import Session

from hub.actions.blokkades import DATABASE_VERPLICHT
from hub.backup.selfbackup import EXPECTED_TABLES, sha256_file
from hub.config import Settings
from hub.models import ActionRequest, Herstelpunt, RestoreTest, SelfBackup
from hub.timeutil import utcnow

SANDBOX = "asm-sandbox"
SANDBOX_NAAM_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,62}$")
PROEF_RE = re.compile(r"^hersteltest_[0-9a-f]{12}$")
# shortcut: de vingerafdruk dekt de tabellen die alleen door een gebruiker veranderen; tabellen die de Hub zelf steeds
# bijschrijft (audit, inventaris, metingen) zouden elke test laten mislukken. Een verkeerd gerichte pg_restore raakt
# deze tabellen altijd mee. Versie 2: de proef op een eigen PostgreSQL-instantie, dan telt de hele database.
VINGERAFDRUK_TABELLEN = ("alembic_version", "app_user", "decision", "vault_secret", "truenas_connection", "service")


@dataclass
class Deel:
    resultaat: str  # geslaagd | mislukt | onbekend
    reden: str | None = None
    bewijs: dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------ tellingen (positieve witte lijst)
def _geldige_tellingen(t: Any) -> bool:
    return (
        isinstance(t, dict)
        and bool(t)
        and all(isinstance(k, str) and k and type(v) is int and v >= 0 for k, v in t.items())
    )


def vergelijk_tellingen(voor: Any, na: Any) -> Deel:
    """Gelijke inhoud = dezelfde tabellen met exact dezelfde aantallen. Geen of ongeldige tellingen: ``onbekend``."""
    if not (_geldige_tellingen(voor) and _geldige_tellingen(na)):
        return Deel("onbekend", "tellingen_ongeldig")
    verschil = {
        t: {"voor": voor.get(t), "na": na.get(t)} for t in sorted(set(voor) | set(na)) if voor.get(t) != na.get(t)
    }
    if verschil:
        return Deel("mislukt", "inhoud_wijkt_af", {"verschil": verschil})
    return Deel("geslaagd", None, {"tabellen": len(voor), "rijen": sum(voor.values())})


# ------------------------------------------------------------------ kloon in de zandbak (EX14)
def _uitgevoerd(db: Session, ruw: Any, action_id: str) -> ActionRequest | None:
    try:
        req = db.get(ActionRequest, uuid.UUID(str(ruw)))
    except ValueError:
        return None
    return req if req is not None and req.action_id == action_id and req.status == "uitgevoerd" else None


def controleer_klonen(db: Session, hp: Herstelpunt, kloon_ids: list[uuid.UUID]) -> Deel:
    """Elke dataset van het herstelpunt heeft precies één uitgevoerde, teruggelezen kloon van zijn eigen snapshot in
    ``<pool>/asm-sandbox/<naam>``, gemaakt na die snapshot. Koppeling alleen op ID."""
    snap = hp.snapshot if isinstance(hp.snapshot, dict) else {}
    maak = _uitgevoerd(db, snap.get("actie_id"), "zfs.snapshot.create")
    naam = (maak.parameters or {}).get("naam") if maak is not None else None
    datasets = snap.get("datasets")
    if maak is None or maak.uitgevoerd_op is None or not isinstance(naam, str) or not isinstance(datasets, list):
        return Deel("onbekend", "snapshot_onbekend")
    verwacht = {f"{d}@{naam}" for d in datasets if isinstance(d, str)}
    gezien: dict[str, str] = {}
    for kid in kloon_ids:
        k = _uitgevoerd(db, kid, "zfs.snapshot.clone_to_sandbox")
        if k is None or k.uitgevoerd_op is None or k.uitgevoerd_op <= maak.uitgevoerd_op:
            return Deel("onbekend", "kloon_niet_uitgevoerd", {"kloon": str(kid)})
        bron = str((k.target or {}).get("snapshot") or "")
        doel = (k.parameters or {}).get("doel_dataset")
        rb = (k.resultaat or {}).get("readback") if isinstance(k.resultaat, dict) else None
        delen = doel.split("/") if isinstance(doel, str) else []
        in_zandbak = (
            len(delen) == 3
            and delen[0] == bron.split("/", 1)[0]
            and delen[1] == SANDBOX
            and bool(SANDBOX_NAAM_RE.fullmatch(delen[2]))
        )
        if bron not in verwacht or bron in gezien:
            return Deel("onbekend", "kloon_hoort_niet_bij_herstelpunt", {"kloon": str(kid)})
        if not in_zandbak or rb != {"dataset": doel, "aanwezig": True}:
            return Deel("onbekend", "kloon_niet_in_zandbak", {"kloon": str(kid)})
        gezien[bron] = str(doel)
    if set(gezien) != verwacht:
        return Deel("onbekend", "kloon_ontbreekt", {"ontbreekt": sorted(verwacht - set(gezien))})
    return Deel("geslaagd", None, {"klonen": dict(sorted(gezien.items()))})


# ------------------------------------------------------------------ database-export in een proefdatabase
def _veilig_pad(pad: Path, wortel: Path) -> bool:
    """V-095: geen enkel onderdeel van het pad is een symbolische koppeling en het ligt onder ``wortel``."""
    pad, wortel = pad.absolute(), wortel.absolute()
    if wortel not in pad.parents:
        return False
    deel = pad
    while deel != wortel.parent:
        if deel.is_symlink():
            return False
        deel = deel.parent
    return pad.is_file()


def dump_tellingen(pad: Path, pg_restore_bin: str) -> dict[str, int] | None:
    """Rijen per tabel zoals ze in de export staan (``COPY``-blokken van ``pg_restore --data-only``), gestreamd."""
    tellingen: dict[str, int] = {}
    huidig: str | None = None
    try:
        with subprocess.Popen(
            [pg_restore_bin, "--data-only", "--file=-", str(pad)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ) as proc:
            assert proc.stdout is not None
            for regel in proc.stdout:
                if huidig is None:
                    m = re.match(r"^COPY (\S+) .*FROM stdin;$", regel)
                    if m:
                        huidig = m.group(1).replace('"', "")
                        tellingen[huidig] = 0
                elif regel == "\\.\n":
                    huidig = None
                else:
                    tellingen[huidig] += 1
    except OSError:
        return None
    return tellingen if proc.returncode == 0 and huidig is None and tellingen else None


def _tabel_tellingen(conn: psycopg.Connection[Any], tabellen: list[str]) -> dict[str, int]:
    uit: dict[str, int] = {}
    for naam in tabellen:
        schema, _, tabel = naam.rpartition(".")
        q = sql.SQL("SELECT count(*) FROM {}.{}").format(sql.Identifier(schema or "public"), sql.Identifier(tabel))
        row = conn.execute(q).fetchone()
        uit[naam] = int(row[0]) if row else -1
    return uit


def vingerafdruk(libpq_url: str) -> str | None:
    """SHA-256 over de inhoud van :data:`VINGERAFDRUK_TABELLEN` in de productiedatabase (alleen lezen)."""
    h = hashlib.sha256()
    try:
        with psycopg.connect(libpq_url, connect_timeout=10) as conn:
            conn.read_only = True
            for t in VINGERAFDRUK_TABELLEN:
                q = sql.SQL(
                    "SELECT count(*), coalesce(string_agg(md5(x::text), ',' ORDER BY md5(x::text)), '') FROM {} x"
                )
                row = conn.execute(q.format(sql.Identifier(t))).fetchone()
                h.update(f"{t}:{row}\n".encode() if row else b"")
    except psycopg.Error:
        return None
    return h.hexdigest()


@contextlib.contextmanager
def proefdatabase(libpq_url: str, naam: str | None = None) -> Iterator[str]:
    """Een lege proefdatabase op dezelfde server; de verbindings-URL ervan. Altijd weer weg, ook bij een fout."""
    naam = naam or f"hersteltest_{uuid.uuid4().hex[:12]}"
    productie = conninfo_to_dict(libpq_url).get("dbname")
    if not PROEF_RE.fullmatch(naam) or naam == productie:
        raise ValueError("ongeldige naam voor een proefdatabase")
    with psycopg.connect(libpq_url, autocommit=True, connect_timeout=10) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(naam)))
    try:
        yield make_conninfo(libpq_url, dbname=naam)
    finally:
        with psycopg.connect(libpq_url, autocommit=True, connect_timeout=10) as conn:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(naam)))


def herstel_in(doel_url: str, pad: Path, pg_restore_bin: str) -> Deel:
    """Zet de export terug in een (lege) doeldatabase en vergelijk de aantallen per tabel met de export."""
    voor = dump_tellingen(pad, pg_restore_bin)
    if voor is None:
        return Deel("mislukt", "export_onleesbaar")
    ontbreekt = [t for t in EXPECTED_TABLES if f"public.{t}" not in voor]
    if ontbreekt:
        return Deel("mislukt", "tabellen_ontbreken", {"ontbrekend": ontbreekt})
    try:
        proc = subprocess.run(
            [pg_restore_bin, "--exit-on-error", "--no-owner", "--no-privileges", f"--dbname={doel_url}", str(pad)],
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return Deel("mislukt", "herstel_mislukt")
    if proc.returncode != 0:
        return Deel("mislukt", "herstel_mislukt")  # stderr niet doorgeven: kan inhoud uit de export bevatten
    with psycopg.connect(doel_url, autocommit=True, connect_timeout=10) as conn:
        na = _tabel_tellingen(conn, sorted(voor))
    uit = vergelijk_tellingen(voor, na)
    uit.bewijs["tellingen"] = na if uit.resultaat == "geslaagd" else uit.bewijs.get("verschil")
    return uit


def toets_dumpbestand(settings: Settings, pad: Path, wortel: Path, verwacht_sha: Any) -> Deel:
    """Checksum, herstel in een proefdatabase en tellingen voor één exportbestand (eigen export of extern gedownload,
    EX13). Het pad mag niet via een symbolische koppeling buiten ``wortel`` uitkomen."""
    if not _veilig_pad(pad, wortel):
        return Deel("mislukt", "bronpad_ongeldig")
    if not (isinstance(verwacht_sha, str) and re.fullmatch(r"[0-9a-f]{64}", verwacht_sha)):
        return Deel("onbekend", "checksum_onbekend")
    if sha256_file(pad) != verwacht_sha:
        return Deel("mislukt", "checksum_afwijkend")
    try:
        with proefdatabase(settings.libpq_url) as doel:
            uit = herstel_in(doel, pad, settings.pg_restore_bin)
    except (psycopg.Error, ValueError):
        return Deel("onbekend", "proefdatabase_niet_beschikbaar")
    uit.bewijs["sha256"] = verwacht_sha
    return uit


def toets_export(db: Session, settings: Settings, hp: Herstelpunt) -> Deel:
    """De database-export bij het herstelpunt. HARDE EIS: zonder export bij een media-app is het ``onbekend``."""
    dbx = hp.db_export if isinstance(hp.db_export, dict) else None
    if dbx is None:
        if hp.app.lower() in DATABASE_VERPLICHT:
            return Deel("onbekend", "database_export_ontbreekt")
        return Deel("geslaagd", None, {"database": "geen"})
    if dbx.get("bron") != "pg_dump":
        return Deel("onbekend", "capability_unavailable")  # andere exports komen via de connector (VERSIE 2)
    try:
        row = db.get(SelfBackup, uuid.UUID(str(dbx.get("id"))))
    except ValueError:
        row = None
    if row is None or row.status != "geslaagd" or not row.file_name or row.deleted_at is not None:
        return Deel("onbekend", "export_niet_beschikbaar")
    if row.sha256 != dbx.get("sha256"):
        return Deel("mislukt", "checksum_afwijkend")
    return toets_dumpbestand(settings, settings.backups_dir / row.file_name, settings.backups_dir, dbx.get("sha256"))


def samen(delen: list[Deel]) -> Deel:
    for r in ("mislukt", "onbekend"):
        d = next((d for d in delen if d.resultaat == r), None)
        if d is not None:
            return Deel(r, d.reden)
    return Deel("geslaagd")


def voer_uit(
    db: Session, settings: Settings, hp: Herstelpunt, kloon_ids: list[uuid.UUID], *, door: str
) -> dict[str, Any]:
    """De hele hersteltest voor één herstelpunt. ``mislukt`` → herstelpunt ``ongezond``; het resultaat komt als
    bewijsrecord in ``restore_test`` (alleen vaste velden, geen vrije tekst); de route legt het auditrecord vast."""
    start = time.monotonic()
    voor = vingerafdruk(settings.libpq_url)
    kloon = controleer_klonen(db, hp, kloon_ids)
    export = toets_export(db, settings, hp) if kloon.resultaat == "geslaagd" else Deel("onbekend", "niet_getoetst")
    na = vingerafdruk(settings.libpq_url)
    if voor is None or na is None:
        productie = Deel("onbekend", "productie_niet_te_meten")
    elif voor != na:
        productie = Deel("mislukt", "productie_gewijzigd")
    else:
        productie = Deel("geslaagd", None, {"vingerafdruk": voor})
    uit = samen([productie, kloon, export])
    # Rijslot: een gelijktijdig voorstel (upsert op het herstelpunt) wacht, en zet een ``ongezond`` nooit terug.
    db.refresh(hp, with_for_update=True)
    if uit.resultaat == "mislukt":
        hp.status, hp.reden = "ongezond", uit.reden
    nu = utcnow()
    rij = RestoreTest(
        app_id=hp.app[:64],
        dataset=", ".join(sorted(kloon.bewijs.get("klonen", {}).values()))[:512] or None,
        soort="database" if hp.db_export else "dataset",
        resultaat=uit.resultaat,
        omgeving=f"{SANDBOX} + proefdatabase (hersteltest-robot)",
        omschrijving=f"Hersteltest-robot: kloon {kloon.resultaat}, database {export.resultaat}, productie "
        f"{productie.resultaat}" + (f" ({uit.reden})" if uit.reden else "") + ".",
        referentie=f"herstelpunt:{hp.id}",
        duur_minuten=math.ceil((time.monotonic() - start) / 60),
        uitgevoerd_op=nu,
        vastgelegd_door=door,
        vastgelegd_op=nu,
    )
    db.add(rij)
    db.flush()
    return {
        "herstelpunt": str(hp.id),
        "resultaat": uit.resultaat,
        "reden": uit.reden,
        "status_herstelpunt": hp.status,
        "kloon": {"resultaat": kloon.resultaat, "reden": kloon.reden, **kloon.bewijs},
        "database": {"resultaat": export.resultaat, "reden": export.reden, **export.bewijs},
        "productie": {"resultaat": productie.resultaat, "reden": productie.reden},
        "restore_test": str(rij.id),
    }
