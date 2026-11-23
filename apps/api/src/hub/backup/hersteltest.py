"""Hersteltest-robot (B12-005, EX13, EX14; S-P2-100).

De robot controleert of een herstelpunt (B12-006) echt terug te zetten is, zonder productie aan te raken:

1. **Kloon in de zandbak.** Per dataset van het herstelpunt een uitgevoerde ``zfs.snapshot.clone_to_sandbox`` (R1, via
   voorstel → executor) van precies die snapshot naar ``<pool>/asm-sandbox/<naam>``, teruggelezen als aanwezig. Bij de
   toets leest de Hub de kloon en de snapshot opnieuw (alleen lezen): de snapshot heeft nog de ``createtxg`` van het
   herstelpunt (dezelfde generatie), de kloon heeft die snapshot als ``origin`` en er is niets in geschreven
   (``written`` 0). Een gewijzigde of onleesbare kloon is geen bewijs (R-HARDE-EIS-4). De robot klont zelf niets en zet
   nooit een snapshot terug op productie: dat staat niet op de vaste lijst.
2. **Database-export in een proefdatabase.** De robot zet eerst een eigen kopie van de export vast en leest daarna
   alleen die. De kopie moet dezelfde SHA-256 hebben als vastgelegd; dan herstelt ``pg_restore`` hem in een eigen
   proefdatabase ``hersteltest_<id>`` en vergelijkt de robot per tabel het aantal rijen en de inhoudshash van de
   herstelde kopie met wat bij het maken van de export is vastgelegd (HARDE EIS: kijkgeschiedenis en voortgang tellen
   mee als tabel; R-HARDE-EIS-5). Daarna gaat de proefdatabase altijd weg. Een proefdatabase draagt een eigen
   merkteken; een achtergebleven exemplaar (processtop) ruimt de volgende toets op, nooit een andere database
   (R-HARDE-EIS-6).
3. **Productie onveranderd.** Een vingerafdruk van de productiedatabase vóór en na; een verschil is ``mislukt``.

Positief bewijs: alleen een kloon van elke dataset, een gelijke checksum, gelijke aantallen per tabel en een
onveranderde productie geven ``geslaagd``. Een kapotte checksum of afwijkende inhoud is ``mislukt`` en maakt het
herstelpunt ``ongezond`` (de pre-update-gate gaat dicht). Wat niet te meten is, is ``onbekend``; ``onbekend`` maakt
een herstelpunt nooit beter.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from sqlalchemy.orm import Session

from hub.actions.beleid import get_policy
from hub.actions.blokkades import DATABASE_VERPLICHT, _inventarisrij, herkenningen
from hub.actions.doel import DoelOnbekend, lees_klonen
from hub.backup.selfbackup import EXPECTED_TABLES, database_inhoud, sha256_file
from hub.config import Settings
from hub.models import ActionRequest, Herstelpunt, RestoreTest, SelfBackup
from hub.timeutil import utcnow
from hub.vault import Vault

SANDBOX = "asm-sandbox"
SANDBOX_NAAM_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,62}$")
PROEF_RE = re.compile(r"^hersteltest_[0-9a-f]{12}$")
# Merkteken (COMMENT ON DATABASE) plus de naam van de productiedatabase: alleen zo'n proefdatabase is aantoonbaar eigen.
MERK = "ai-server-manager hersteltest-robot"
# Elke lopende proef houdt dit slot gedeeld vast; opruimen kan alleen met het slot exclusief (er loopt dan geen proef).
PROEF_SLOT = 0x41534D485354
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


LeesKlonen = Callable[[dict[str, str]], dict[str, dict[str, Any]]]


def controleer_klonen(db: Session, hp: Herstelpunt, kloon_ids: list[uuid.UUID], lees: LeesKlonen) -> Deel:
    """Elke dataset van het herstelpunt heeft precies één uitgevoerde, teruggelezen kloon van zijn eigen snapshot in
    ``<pool>/asm-sandbox/<naam>``, gemaakt na die snapshot. Koppeling alleen op ID. Daarna ``lees`` (nu uit TrueNAS):
    dezelfde snapshotgeneratie (``createtxg``) en een onveranderde kloon (``origin`` en ``written`` 0)."""
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
    rb_maak = (maak.resultaat or {}).get("readback") if isinstance(maak.resultaat, dict) else None
    leden = rb_maak.get("leden") if isinstance(rb_maak, dict) else None
    try:
        nu = lees(gezien)
    except DoelOnbekend:
        return Deel("onbekend", "kloon_niet_te_lezen")
    for bron, doel in gezien.items():
        txg = leden.get(bron.split("@", 1)[0]) if isinstance(leden, dict) else None
        st = nu.get(doel) if isinstance(nu, dict) else None
        if not (isinstance(st, dict) and isinstance(txg, str) and txg):
            return Deel("onbekend", "kloon_niet_te_lezen", {"kloon": doel})
        if st.get("createtxg") != txg:
            return Deel("onbekend", "snapshot_andere_generatie", {"kloon": doel})
        if st.get("origin") != bron or type(st.get("written")) is not int:
            return Deel("onbekend", "kloon_niet_te_lezen", {"kloon": doel})
        if st["written"] != 0:
            return Deel("onbekend", "kloon_gewijzigd", {"kloon": doel})
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


def _ruim_eigen_resten_op(conn: psycopg.Connection[Any], merk: str) -> None:
    """Verwijder achtergebleven proefdatabases (bv. na een processtop): alleen met de eigen naamvorm, het eigen
    merkteken en de eigen rol als eigenaar. Een andere database blijft altijd staan."""
    rijen = conn.execute(
        "SELECT datname FROM pg_database WHERE datdba = (SELECT oid FROM pg_roles WHERE rolname = current_user) "
        "AND shobj_description(oid, 'pg_database') = %s",
        (merk,),
    ).fetchall()
    for (naam,) in rijen:
        if PROEF_RE.fullmatch(naam):
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(naam)))


@contextlib.contextmanager
def proefdatabase(libpq_url: str, naam: str | None = None) -> Iterator[str]:
    """Een lege proefdatabase op dezelfde server; de verbindings-URL ervan. Altijd weer weg, ook bij een fout; blijft er
    na een processtop toch een achter, dan ruimt de volgende proef hem op (alleen aantoonbaar eigen, R-HARDE-EIS-6)."""
    naam = naam or f"hersteltest_{uuid.uuid4().hex[:12]}"
    productie = conninfo_to_dict(libpq_url).get("dbname")
    if not PROEF_RE.fullmatch(naam) or naam == productie:
        raise ValueError("ongeldige naam voor een proefdatabase")
    merk = f"{MERK}: {productie}"
    with psycopg.connect(libpq_url, autocommit=True, connect_timeout=10) as conn:
        if conn.execute("SELECT pg_try_advisory_lock(%s)", (PROEF_SLOT,)).fetchone() == (True,):
            try:
                _ruim_eigen_resten_op(conn, merk)
                conn.execute("SELECT pg_advisory_lock_shared(%s)", (PROEF_SLOT,))
            finally:
                conn.execute("SELECT pg_advisory_unlock(%s)", (PROEF_SLOT,))
        else:
            conn.execute("SELECT pg_advisory_lock_shared(%s)", (PROEF_SLOT,))
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(naam)))
        try:
            conn.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(sql.Identifier(naam), sql.Literal(merk)))
            yield make_conninfo(libpq_url, dbname=naam)
        finally:
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(naam)))


def _geldige_inhoud(v: Any) -> bool:
    return (
        isinstance(v, dict)
        and bool(v)
        and all(
            isinstance(t, str)
            and isinstance(w, dict)
            and set(w) == {"rijen", "sha256"}
            and type(w["rijen"]) is int
            and w["rijen"] >= 0
            and isinstance(w["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", w["sha256"]) is not None
            for t, w in v.items()
        )
    )


def _manifest_inhoud(pad: Path, verwacht_sha: Any = None) -> Any:
    """De bij het maken vastgelegde inhoud uit het ``.json``-bestand naast de export (OSError/ValueError bij lezen)."""
    manifest = json.loads(pad.with_name(pad.name + ".json").read_text())
    if not isinstance(manifest, dict) or (verwacht_sha is not None and manifest.get("sha256") != verwacht_sha):
        return None
    ver = manifest.get("verificatie")
    return ver.get("inhoud") if isinstance(ver, dict) else None


def herstel_in(doel_url: str, pad: Path, pg_restore_bin: str, verwacht: Any = None) -> Deel:
    """Zet de export terug in een (lege) doeldatabase en vergelijk per tabel aantal en inhoudshash met ``verwacht`` (bij
    het maken van de export vastgelegd; zonder opgave uit het ``.json``-bestand ernaast)."""
    if verwacht is None:
        try:
            verwacht = _manifest_inhoud(pad)
        except (OSError, ValueError):
            return Deel("mislukt", "export_onleesbaar")
    if not _geldige_inhoud(verwacht):
        return Deel("onbekend", "inhoud_onbekend")
    ontbreekt = [t for t in EXPECTED_TABLES if f"public.{t}" not in verwacht]
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
        aanwezig = {
            f"{s}.{t}"
            for s, t in conn.execute(
                "SELECT schemaname, tablename FROM pg_tables "
                "WHERE schemaname NOT IN ('pg_catalog', 'information_schema')"
            )
        }
        if not set(verwacht) <= aanwezig:
            return Deel("mislukt", "tabellen_ontbreken", {"ontbrekend": sorted(set(verwacht) - aanwezig)})
        na = _tabel_tellingen(conn, sorted(verwacht))
    uit = vergelijk_tellingen({t: w["rijen"] for t, w in verwacht.items()}, na)
    if uit.resultaat != "geslaagd":
        uit.bewijs["tellingen"] = uit.bewijs.get("verschil")
        return uit
    # pg_dump naast pg_restore (zelfde installatie): dezelfde tekstvorm als bij het maken van de export.
    herstelde = database_inhoud(doel_url, str(Path(pg_restore_bin).with_name("pg_dump")))
    if herstelde is None:
        return Deel("mislukt", "herstel_onleesbaar")
    anders = sorted(t for t in set(verwacht) | set(herstelde) if verwacht.get(t) != herstelde.get(t))
    if anders:
        return Deel("mislukt", "inhoud_wijkt_af", {"tabellen": anders})
    uit.bewijs["tellingen"] = na
    return uit


def toets_dumpbestand(
    settings: Settings, pad: Path, wortel: Path, verwacht_sha: Any, verwacht_inhoud: Any = None
) -> Deel:
    """Checksum, herstel in een proefdatabase en vergelijking per tabel voor één exportbestand (eigen export of extern
    gedownload, EX13). Het pad mag niet via een symbolische koppeling buiten ``wortel`` uitkomen. De robot leest alleen
    een eigen, vastgezette kopie; elke leesfout is ``mislukt`` (R-HARDE-EIS-2)."""
    if not _veilig_pad(pad, wortel):
        return Deel("mislukt", "bronpad_ongeldig")
    if not (isinstance(verwacht_sha, str) and re.fullmatch(r"[0-9a-f]{64}", verwacht_sha)):
        return Deel("onbekend", "checksum_onbekend")
    settings.backups_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".hersteltest-", dir=settings.backups_dir) as map_:
        kopie = Path(map_) / pad.name
        try:
            shutil.copyfile(pad, kopie)
            if verwacht_inhoud is None:
                verwacht_inhoud = _manifest_inhoud(pad, verwacht_sha)
            gelijk = sha256_file(kopie) == verwacht_sha
        except (OSError, ValueError):
            return Deel("mislukt", "export_onleesbaar")
        if not gelijk:
            return Deel("mislukt", "checksum_afwijkend")
        try:
            with proefdatabase(settings.libpq_url) as doel:
                uit = herstel_in(doel, kopie, settings.pg_restore_bin, verwacht_inhoud or {})
        except (psycopg.Error, ValueError):
            return Deel("onbekend", "proefdatabase_niet_beschikbaar")
    uit.bewijs["sha256"] = verwacht_sha
    return uit


def toets_export(db: Session, settings: Settings, hp: Herstelpunt) -> Deel:
    """De database-export bij het herstelpunt. HARDE EIS: zonder export bij een media-app is het ``onbekend``; de app
    wordt herkend zoals de pre-update-gate dat doet (naam, catalogusapp en image; R-HARDE-EIS-1)."""
    dbx = hp.db_export if isinstance(hp.db_export, dict) else None
    if dbx is None:
        if hp.app.lower() in DATABASE_VERPLICHT:
            return Deel("onbekend", "database_export_ontbreekt")
        if not _inventarisrij(db, settings, hp.app):
            return Deel("onbekend", "app_onbekend")  # zonder meting is niet te zeggen dat het geen media-app is
        if herkenningen(db, settings, get_policy(), hp.app) & DATABASE_VERPLICHT:
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
    inhoud = (row.verification or {}).get("inhoud") if isinstance(row.verification, dict) else None
    return toets_dumpbestand(
        settings, settings.backups_dir / row.file_name, settings.backups_dir, dbx.get("sha256"), inhoud or {}
    )


def samen(delen: list[Deel]) -> Deel:
    for r in ("mislukt", "onbekend"):
        d = next((d for d in delen if d.resultaat == r), None)
        if d is not None:
            return Deel(r, d.reden)
    return Deel("geslaagd")


def voer_uit(
    db: Session, settings: Settings, vault: Vault, hp: Herstelpunt, kloon_ids: list[uuid.UUID], *, door: str
) -> dict[str, Any]:
    """De hele hersteltest voor één herstelpunt. ``mislukt`` → herstelpunt ``ongezond``; het resultaat komt als
    bewijsrecord in ``restore_test`` (alleen vaste velden, geen vrije tekst); de route legt het auditrecord vast."""
    start = time.monotonic()
    voor = vingerafdruk(settings.libpq_url)
    kloon = controleer_klonen(db, hp, kloon_ids, lambda k: lees_klonen(db, vault, settings, k))
    export = Deel("onbekend", "niet_getoetst")
    if kloon.resultaat == "geslaagd":
        try:
            export = toets_export(db, settings, hp)
        except Exception:  # fail-closed: een fout bij het toetsen van een gekoppelde export is nooit een doorlaat
            export = Deel("mislukt" if hp.db_export else "onbekend", "toets_fout")
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
