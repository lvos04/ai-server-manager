"""Eigen journaal van de executor in SQLite (``/appdata/executor.sqlite3``; contract 1.3 §8, ADR-0030).

- ``request_nonces``: elke ``nonce`` van een ``ExecutionRequest`` met een geldige handtekening, één keer.
- ``approval_nonces``: elke ``one_time_nonce`` van een goedkeuring, één keer (EX20), ook als de Hub zich vergist.
- ``journal``: per uitvoering de before/after-hash, de methode en de uitkomst.
- ``app_values``: de vorige waarden van een Custom App (uit ``app.config``), **versleuteld** met ``vault.key``, zodat
  ``app.rollback`` ze kan terugzetten. De Hub ziet ze nooit.
- ``state``: de toestand "gestopt" na een afwijking; blijft staan over een herstart. Daarnaast ``vrijgegeven_tot``: de
  hoogste journaalrij op het moment van de laatste vrijgave.

Vastleggen en vergelijken gebeuren in één transactie (``BEGIN IMMEDIATE``). Is de opslag niet bruikbaar, dan
``JournalUnavailable``: de executor voert dan niets uit (fail-closed).

De stop is duurzaam (S-P2-030, R-VEILIG-1 en R-VEILIG-2; ADR-0030 besluit 14):

- de stop en het einde van de journaalrij staan in **één** transactie (de stop eerst);
- lukt dat vastleggen niet, dan houdt dit object de stop **in het geheugen** en legt hem vast zodra het journaal weer
  werkt;
- :meth:`Journal.stopped` telt ook als gestopt: een rij ``gestart`` zonder einde die door geen lopende uitvoering van
  dit proces wordt vastgehouden (het proces viel weg na de schrijfaanroep: uitkomst onbekend), en een rij
  ``afwijking`` van na de laatste vrijgave. Zo'n rij krijgt dan alsnog een stop (en een rij ``gestart`` het einde
  ``afwijking`` met ``uitkomst_onbekend``). Dit gebeurt alleen bij het starten, vóór elke uitvoering en bij het
  vrijgeven, in één schrijftransactie waarin ook de lopende uitvoeringen worden gelezen (ná ``BEGIN IMMEDIATE``; anders
  kan een uitvoering die net begint als weggevallen tellen, R-VEILIG-H1). Een statusopvraag (``vastleggen=False``)
  leest alleen: de vastgelegde stop of die in het geheugen, nooit een schrijftransactie;
- faalt het journaal vóór de schrijfaanroep (er is aantoonbaar niets naar TrueNAS gestuurd), dan wacht het einde
  ``mislukt`` van die rij in het geheugen en wordt het vastgelegd zodra het journaal weer werkt; zo'n rij geeft geen
  stop (R-VEILIG-H2).

Een stop raakt nooit een app: alleen de executor weigert verdere acties tot de vrijgave op de executorpagina.
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from executor.naslink import NasLinkOnleesbaar, Vault

AAD = b"executor-app-values-v1"
SCHEMA = (
    "CREATE TABLE IF NOT EXISTS request_nonces (nonce TEXT PRIMARY KEY, seen_at INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS approval_nonces ("
    " nonce TEXT PRIMARY KEY, approval_id TEXT NOT NULL, seen_at INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS journal ("
    " request_id TEXT NOT NULL, nonce TEXT PRIMARY KEY, action_id TEXT NOT NULL, target TEXT NOT NULL,"
    " methode TEXT, status TEXT NOT NULL, before_hash TEXT, after_hash TEXT, detail TEXT,"
    " started_at INTEGER NOT NULL, finished_at INTEGER)",
    "CREATE TABLE IF NOT EXISTS app_values ("
    " request_id TEXT PRIMARY KEY, app TEXT NOT NULL, box TEXT NOT NULL, created_at INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS kluismarkering ("
    " request_id TEXT PRIMARY KEY, app TEXT NOT NULL, nas_fingerprint TEXT NOT NULL, plekken TEXT NOT NULL,"
    " created_at INTEGER NOT NULL)",
    # S-P2-050f: per bijwerken of terugzetten de eigen herkomst (verzegeld) en per snapshotactie het checkpoint.
    "CREATE TABLE IF NOT EXISTS recept_herkomst ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL UNIQUE, app TEXT NOT NULL, box TEXT NOT NULL,"
    " created_at INTEGER NOT NULL)",
    "CREATE TABLE IF NOT EXISTS checkpoint ("
    " request_id TEXT PRIMARY KEY, dataset TEXT NOT NULL, snapshot TEXT NOT NULL, createtxg TEXT NOT NULL,"
    " recursief INTEGER NOT NULL, grens INTEGER NOT NULL, created_at INTEGER NOT NULL)",
)
AAD_HERKOMST = b"executor-recept-herkomst-v1"
AAD_OUD = b"executor-oud-vastlegging-v1"
# In de geheimenmap: de eenmalige vastlegging van de recepten van vóór S-P2-050f is gedaan. Ontbreekt daarna de
# vastlegging zelf (verlies), dan wordt nooit opnieuw geïnventariseerd (ADR-0032 besluit 8).
OUD_ANKER = "f-ingebruikname"


# In de geheimenmap (het deel dat bij herstel terugkomt) staat per gemarkeerde instantie een leeg ankerbestand (naam:
# de instantie-ID in hex, nooit een waarde). Journaal en ankers moeten dezelfde instanties noemen; een anker zonder rij
# betekent een onvolledig of ouder hersteld journaal: de markering is dan onbekend, niet leeg (R-VEILIG-2).
KLUIS_ANKERS = "kluismarkering"
# Eén anker voor de hele installatie uit de vorige versie (45b75b0); alleen nog gelezen.
KLUIS_ANKER = "kluis-in-gebruik"


class JournalUnavailable(Exception):
    """Het journaal is niet bruikbaar: niets uitvoeren."""


# Uitvoeringen die nu in dit proces lopen, per journaalbestand: (pad, nonce). Een rij ``gestart`` daarvan is geen
# onafgemaakte uitvoering. Een rij ``gestart`` die hier niet in staat, is van een proces dat wegviel (één proces per
# datamap: ``python -m executor api`` start één uvicorn-proces).
_LOPEND: set[tuple[str, str]] = set()
_LOPEND_SLOT = threading.Lock()


def _nu_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Journal:
    def __init__(self, path: Path, secrets_dir: Path) -> None:
        self.path = path
        self.vault = Vault(secrets_dir)
        self.anker = secrets_dir / KLUIS_ANKER
        self.ankers = secrets_dir / KLUIS_ANKERS
        self.oud_anker = secrets_dir / OUD_ANKER
        self._sleutel = os.path.abspath(path)
        # Een stop die niet kon worden vastgelegd: (reden, nonce, after_hash, detail). Zie de kop van dit bestand.
        self._stop_in_geheugen: tuple[dict[str, Any], str | None, str | None, str] | None = None
        # Een einde dat niet kon worden vastgelegd (vóór de schrijfaanroep): nonce -> (status, hash, detail).
        self._einde_in_geheugen: dict[str, tuple[str, str | None, str]] = {}

    @contextlib.contextmanager
    def _connect(self, *, aanmaken: bool = True) -> Iterator[sqlite3.Connection]:
        try:
            if not self.path.exists():
                if not aanmaken:
                    raise FileNotFoundError(self.path)
                os.close(os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600))
            conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        except (OSError, sqlite3.Error) as exc:
            raise JournalUnavailable(type(exc).__name__) from None
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            for stmt in SCHEMA:
                conn.execute(stmt)
            yield conn
        except sqlite3.Error as exc:
            raise JournalUnavailable(type(exc).__name__) from None
        finally:
            conn.close()

    def _claim(self, sql: str, args: tuple[Any, ...]) -> bool:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(sql, args)
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                return False
            conn.execute("COMMIT")
            return True

    # ------------------------------------------------------------------ nonces
    def claim_request_nonce(self, nonce: str) -> bool:
        """``True`` bij het eerste gebruik (nu vastgelegd); ``False`` als deze nonce al eens is gezien."""
        return self._claim("INSERT INTO request_nonces (nonce, seen_at) VALUES (?, ?)", (nonce, int(time.time())))

    def approval_used(self, nonce: str) -> bool:
        with self._connect() as conn:
            return conn.execute("SELECT 1 FROM approval_nonces WHERE nonce = ?", (nonce,)).fetchone() is not None

    def claim_approval_nonce(self, nonce: str, approval_id: str) -> bool:
        return self._claim(
            "INSERT INTO approval_nonces (nonce, approval_id, seen_at) VALUES (?, ?, ?)",
            (nonce, approval_id, int(time.time())),
        )

    # ------------------------------------------------------------------ journaal
    @contextlib.contextmanager
    def lopend(self, nonce: str) -> Iterator[None]:
        """Markeer de uitvoering met deze nonce als lopend in dit proces (vóór :meth:`begin`, tot na het einde)."""
        sleutel = (self._sleutel, nonce)
        with _LOPEND_SLOT:
            _LOPEND.add(sleutel)
        try:
            yield
        finally:
            with _LOPEND_SLOT:
                _LOPEND.discard(sleutel)

    def _lopende_nonces(self) -> set[str]:
        with _LOPEND_SLOT:
            return {n for pad, n in _LOPEND if pad == self._sleutel}

    def bezet(self) -> bool:
        """Of een andere instantie in dit proces nu een uitvoering op dit journaal heeft lopen. Eerst de rijen, dan de
        lopende nonces: een rij die er staat, is vóór zijn invoegen als lopend gemarkeerd."""
        with self._connect() as conn:
            rows = conn.execute("SELECT nonce FROM journal WHERE status = 'gestart'").fetchall()
        lopend = self._lopende_nonces() if rows else set()
        return any(r[0] in lopend for r in rows)

    def begin(
        self, *, request_id: str, nonce: str, action_id: str, target: dict[str, Any], methode: str, before_hash: str
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO journal (request_id, nonce, action_id, target, methode, status, before_hash, started_at)"
                " VALUES (?, ?, ?, ?, ?, 'gestart', ?, ?)",
                (
                    request_id,
                    nonce,
                    action_id,
                    json.dumps(target, sort_keys=True),
                    methode,
                    before_hash,
                    int(time.time()),
                ),
            )

    def finish(self, nonce: str, *, status: str, after_hash: str | None, detail: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE journal SET status = ?, after_hash = ?, detail = ?, finished_at = ? WHERE nonce = ?",
                (status, after_hash, detail[:1000], int(time.time()), nonce),
            )

    def entries(self, request_id: str | None = None) -> list[dict[str, Any]]:
        sql = (
            "SELECT request_id, nonce, action_id, target, methode, status, before_hash, after_hash, detail,"
            " started_at, finished_at FROM journal"
        )
        with self._connect() as conn:
            rows = conn.execute(
                sql + (" WHERE request_id = ?" if request_id else "") + " ORDER BY started_at, rowid",
                (request_id,) if request_id else (),
            ).fetchall()
        keys = (
            "request_id",
            "nonce",
            "action_id",
            "target",
            "methode",
            "status",
            "before_hash",
            "after_hash",
            "detail",
            "started_at",
            "finished_at",
        )
        return [dict(zip(keys, r, strict=True)) for r in rows]

    # ------------------------------------------------------------------ vorige app-waarden (terugzetten)
    def _zegel(self, data: Any, aad: bytes) -> str:
        try:
            return json.dumps(self.vault.seal(json.dumps(data, sort_keys=True).encode(), aad))
        except NasLinkOnleesbaar:
            raise JournalUnavailable("vault.key") from None

    def _open(self, box: str, aad: bytes) -> Any:
        try:
            return json.loads(self.vault.open(json.loads(box), aad))
        except (NasLinkOnleesbaar, ValueError, TypeError):
            raise JournalUnavailable("zegel_ongeldig") from None

    def save_values(
        self, request_id: str, app: str, values: dict[str, Any], herkomst: dict[str, Any] | None = None
    ) -> None:
        """Het recept (vorige waarden) en, sinds S-P2-050f, in dezelfde transactie de eigen herkomst."""
        box = self._zegel(values, AAD + request_id.encode())
        hbox = (
            self._zegel({**herkomst, "app": app}, AAD_HERKOMST + f"{request_id}:{app}".encode()) if herkomst else None
        )
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO app_values (request_id, app, box, created_at) VALUES (?, ?, ?, ?)",
                    (request_id, app, box, int(time.time())),
                )
                if hbox is not None:
                    conn.execute(
                        "INSERT INTO recept_herkomst (request_id, app, box, created_at) VALUES (?, ?, ?, ?)",
                        (request_id, app, hbox, int(time.time())),
                    )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    # ------------------------------------------------------------------ herkomst en checkpoints (S-P2-050f)
    def leg_herkomst_vast(self, request_id: str, app: str, herkomst: dict[str, Any]) -> None:
        """Herkomst van een bijwerking zonder recept (catalogusversie), vóór de schrijfaanroep."""
        hbox = self._zegel({**herkomst, "app": app}, AAD_HERKOMST + f"{request_id}:{app}".encode())
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO recept_herkomst (request_id, app, box, created_at) VALUES (?, ?, ?, ?)",
                (request_id, app, hbox, int(time.time())),
            )

    def herkomsten(self, app: str) -> list[tuple[int, str, dict[str, Any]]]:
        """``(volgnummer, request_id, herkomst)`` van deze app op volgorde. Een ongeldig zegel of een herkomst van een
        andere app: :class:`JournalUnavailable` (onbekend, nooit alsnog ``oud``)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, request_id, box FROM recept_herkomst WHERE app = ? ORDER BY id", (app,)
            ).fetchall()
        uit = []
        for rid, request_id, box in rows:
            h = self._open(box, AAD_HERKOMST + f"{request_id}:{app}".encode())
            if not isinstance(h, dict) or h.get("app") != app:
                raise JournalUnavailable("herkomst_ongeldig")
            uit.append((int(rid), str(request_id), h))
        return uit

    def heeft_herkomst(self, request_id: str) -> bool:
        with self._connect() as conn:
            return (
                conn.execute("SELECT 1 FROM recept_herkomst WHERE request_id = ?", (request_id,)).fetchone() is not None
            )

    def leg_checkpoint_vast(
        self, request_id: str, dataset: str, snapshot: str, createtxg: str, recursief: bool
    ) -> None:
        """Na een geslaagde en teruggelezen snapshot: dit is een checkpoint. ``grens`` is de laatste bijwerking die er
        toen al was; een latere bijwerking van een app maakt het checkpoint voor die app verouderd."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                grens = int(conn.execute("SELECT COALESCE(MAX(id), 0) FROM recept_herkomst").fetchone()[0])
                conn.execute(
                    "INSERT INTO checkpoint (request_id, dataset, snapshot, createtxg, recursief, grens, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (request_id, dataset, snapshot, createtxg, int(recursief), grens, int(time.time())),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def checkpoint(self, request_id: str) -> dict[str, Any] | None:
        keys = ("request_id", "dataset", "snapshot", "createtxg", "recursief", "grens", "created_at")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT request_id, dataset, snapshot, createtxg, recursief, grens, created_at FROM checkpoint"
                " WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        uit = dict(zip(keys, row, strict=True))
        uit["recursief"] = bool(uit["recursief"])
        return uit

    def gewijzigd_na(self, app: str, grens: int) -> bool:
        """Of deze app na volgnummer ``grens`` is bijgewerkt of teruggezet (ook een mislukte poging telt)."""
        with self._connect() as conn:
            return (
                conn.execute("SELECT 1 FROM recept_herkomst WHERE app = ? AND id > ?", (app, grens)).fetchone()
                is not None
            )

    def oud_vastlegging(self) -> set[tuple[str, str, int]]:
        """De recepten van vóór S-P2-050f: ``(request_id, app, created_at)``. De eerste keer eenmalig vastgelegd
        (verzegeld, in één transactie met het tijdanker), daarna alleen gelezen; nooit opnieuw geïnventariseerd.
        Ontbreekt de vastlegging na de eerste keer, of is het zegel ongeldig: :class:`JournalUnavailable`."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                waarde: Any
                row = conn.execute("SELECT value FROM state WHERE key = 'oud_vastlegging'").fetchone()
                if row is None:
                    if self.oud_anker.exists():
                        raise JournalUnavailable("oud_vastlegging_ontbreekt")
                    leden = conn.execute(
                        "SELECT request_id, app, created_at FROM app_values"
                        " WHERE request_id NOT IN (SELECT request_id FROM recept_herkomst) ORDER BY request_id"
                    ).fetchall()
                    data: Any = {"tijdanker": int(time.time()), "leden": [list(r) for r in leden], "aantal": len(leden)}
                    conn.execute(
                        "INSERT INTO state (key, value) VALUES ('oud_vastlegging', ?)", (self._zegel(data, AAD_OUD),)
                    )
                    waarde = data
                else:
                    waarde = self._open(row[0], AAD_OUD)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        try:
            os.close(os.open(self.oud_anker, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600))
        except OSError as exc:
            raise JournalUnavailable(type(exc).__name__) from None
        try:
            lijst = waarde["leden"]
            if len(lijst) != waarde["aantal"]:
                raise ValueError
            return {(str(r[0]), str(r[1]), int(r[2])) for r in lijst}
        except (KeyError, TypeError, ValueError, IndexError):
            raise JournalUnavailable("oud_vastlegging_ongeldig") from None

    def recept_tijd(self, request_id: str) -> tuple[str, int] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT app, created_at FROM app_values WHERE request_id = ?", (request_id,)).fetchone()
        return (str(row[0]), int(row[1])) if row else None

    def load_values(self, request_id: str) -> tuple[str, dict[str, Any]] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT app, box FROM app_values WHERE request_id = ?", (request_id,)).fetchone()
        if row is None:
            return None
        try:
            values = json.loads(self.vault.open(json.loads(row[1]), AAD + request_id.encode()))
        except (NasLinkOnleesbaar, ValueError):
            raise JournalUnavailable("app_values") from None
        return str(row[0]), values if isinstance(values, dict) else {}

    # ------------------------------------------------------------------ kluismarkering (contract 1.3 §8.3)
    def markeer_kluis(self, request_id: str, app: str, nas_fingerprint: str, plekken: list[dict[str, str]]) -> None:
        """Vóór de schrijfaanroep: deze instantie krijgt plekken uit de kluis. Nooit een waarde of hash."""
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO kluismarkering (request_id, app, nas_fingerprint, plekken, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (request_id, app, nas_fingerprint, json.dumps(plekken, sort_keys=True), int(time.time())),
            )
        # Na de rij: een anker zonder rij kan niet ontstaan, een rij zonder anker vult het lezen of starten aan.
        self._zet_anker(app)

    def _zet_anker(self, app: str) -> None:
        try:
            self.ankers.mkdir(mode=0o700, exist_ok=True)
            os.close(os.open(self.ankers / app.encode().hex(), os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600))
        except OSError as exc:
            raise JournalUnavailable(type(exc).__name__) from None

    def _verankerd(self) -> set[str]:
        """De instanties met een anker; een onleesbare ankermap of een vreemde naam: :class:`JournalUnavailable`."""
        try:
            namen = [p.name for p in self.ankers.iterdir()] if self.ankers.exists() else []
            return {bytes.fromhex(n).decode() for n in namen}
        except (OSError, ValueError):
            raise JournalUnavailable("kluisanker_onleesbaar") from None

    def _kluisrijen(self) -> set[str]:
        with self._connect(aanmaken=False) as conn:
            return {str(r[0]) for r in conn.execute("SELECT app FROM kluismarkering").fetchall()}

    def vul_kluisankers_aan(self) -> None:
        """Bij het starten (ook na een upgrade): elke markering in het journaal krijgt haar anker."""
        for app in self._kluisrijen() - self._verankerd():
            self._zet_anker(app)

    def kluis_gemarkeerd(self, app: str) -> bool:
        """Onleesbaar of ontbrekend journaal: :class:`JournalUnavailable` (de aanroeper weigert dan, §8.3). Lezen maakt
        nooit een journaal aan. Een anker zonder markering in het journaal (ouder of leeg hersteld journaal), of het
        anker van de vorige versie bij een journaal zonder markeringen: ook onbekend (R-VEILIG-2)."""
        rijen = self._kluisrijen()
        verankerd = self._verankerd()
        for ontbreekt in rijen - verankerd:
            self._zet_anker(ontbreekt)
        try:
            oud_anker = self.anker.exists()
        except OSError:
            oud_anker = True
        if verankerd - rijen or (oud_anker and not rijen):
            raise JournalUnavailable("kluismarkering_onvolledig")
        return app in rijen

    # ------------------------------------------------------------------ gestopt na een afwijking
    @staticmethod
    def _lees_stop(conn: sqlite3.Connection) -> dict[str, Any] | None:
        row = conn.execute("SELECT value FROM state WHERE key = 'gestopt'").fetchone()
        if row is None:
            return None
        try:
            value = json.loads(row[0])
        except ValueError:
            return {"code": "onbekend"}
        return value if isinstance(value, dict) else {"code": "onbekend"}

    @staticmethod
    def _zet_stop(
        conn: sqlite3.Connection, reason: dict[str, Any], nonce: str | None, after_hash: str | None, detail: str
    ) -> None:
        """Binnen een lopende transactie: eerst de stop, dan het einde van de rij (``afwijking``)."""
        conn.execute(
            "INSERT OR REPLACE INTO state (key, value) VALUES ('gestopt', ?)", (json.dumps(reason, sort_keys=True),)
        )
        if nonce is not None:
            conn.execute(
                "UPDATE journal SET status = 'afwijking', after_hash = ?, detail = ?, finished_at = ? WHERE nonce = ?",
                (after_hash, detail[:1000], int(time.time()), nonce),
            )

    def stopped(self, *, vastleggen: bool = True) -> dict[str, Any] | None:
        """De stop, of ``None``.

        ``vastleggen=False`` (statusopvragen): alleen lezen, de vastgelegde stop of die in het geheugen; geen
        schrijftransactie (R-VEILIG-H1). Standaard (bij het starten, vóór elke uitvoering en bij het vrijgeven): in één
        transactie ook vastleggen wat als gestopt telt maar nog niet vastlag: een einde of stop uit het geheugen, een
        onafgemaakte rij ``gestart`` (uitkomst onbekend) en een ``afwijking`` van na de laatste vrijgave (zie de kop van
        dit bestand)."""
        if not vastleggen:
            geheugen_stop = self._stop_in_geheugen
            with self._connect() as conn:
                vast = self._lees_stop(conn)
            if vast is None and geheugen_stop is not None:
                return dict(geheugen_stop[0])
            return vast
        geheugen = self._stop_in_geheugen
        einden = dict(self._einde_in_geheugen)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Een einde vóór de schrijfaanroep dat nog niet vastlag (R-VEILIG-H2): eerst, dan telt de rij niet.
                for n, (status, after_hash, detail) in einden.items():
                    conn.execute(
                        "UPDATE journal SET status = ?, after_hash = ?, detail = ?, finished_at = ?"
                        " WHERE nonce = ? AND status = 'gestart'",
                        (status, after_hash, detail[:1000], int(time.time()), n),
                    )
                stop = self._lees_stop(conn)
                if geheugen is not None:
                    reden, nonce, after_hash, detail = geheugen
                    if stop is None:
                        self._zet_stop(conn, reden, nonce, after_hash, detail)
                        stop = reden
                    elif nonce is not None:
                        self._zet_stop(conn, stop, nonce, after_hash, detail)
                gestart = conn.execute(
                    "SELECT nonce, request_id, action_id FROM journal WHERE status = 'gestart' ORDER BY rowid"
                ).fetchall()
                # Binnen de transactie (na BEGIN IMMEDIATE en na het lezen van de rijen): een rij die hier staat is
                # vóór zijn invoegen als lopend gemarkeerd, en een nieuwe rij kan niet worden ingevoegd zolang deze
                # transactie loopt. Zo telt een uitvoering die net begint nooit als weggevallen (R-VEILIG-H1).
                lopend = self._lopende_nonces()
                wees = [(str(r[0]), str(r[1]), str(r[2])) for r in gestart if r[0] not in lopend]
                if wees:
                    nonce, request_id, action_id = wees[0]
                    reden = stop or {
                        "code": "uitkomst_onbekend",
                        "request_id": request_id,
                        "action_id": action_id,
                        "at": _nu_iso(),
                    }
                    for n, _r, _a in wees:
                        self._zet_stop(conn, reden, n, None, "uitkomst_onbekend")
                    stop = reden
                if stop is None:
                    grens_rij = conn.execute("SELECT value FROM state WHERE key = 'vrijgegeven_tot'").fetchone()
                    try:
                        grens = int(grens_rij[0]) if grens_rij is not None else 0
                    except ValueError:
                        grens = 0
                    afw = conn.execute(
                        "SELECT request_id, action_id, detail FROM journal WHERE status = 'afwijking' AND rowid > ?"
                        " ORDER BY rowid LIMIT 1",
                        (grens,),
                    ).fetchone()
                    if afw is not None:
                        stop = {
                            "code": str(afw[2] or "afwijking"),
                            "request_id": str(afw[0]),
                            "action_id": str(afw[1]),
                            "at": _nu_iso(),
                        }
                        self._zet_stop(conn, stop, None, None, "")
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        if geheugen is not None and self._stop_in_geheugen is geheugen:
            self._stop_in_geheugen = None
        for n in einden:
            self._einde_in_geheugen.pop(n, None)
        return stop

    def stop(
        self, reason: dict[str, Any], *, nonce: str | None = None, after_hash: str | None = None, detail: str = ""
    ) -> None:
        """Stop vastleggen; met ``nonce`` in dezelfde transactie ook het einde van die rij (``afwijking``)."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                self._zet_stop(conn, reason, nonce, after_hash, detail)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def einde_in_geheugen(self, nonce: str, *, status: str, after_hash: str | None, detail: str = "") -> None:
        """Het einde van een rij kon niet worden vastgelegd terwijl er aantoonbaar niets naar TrueNAS is gestuurd: houd
        het vast tot :meth:`stopped` het kan vastleggen; de rij telt dan niet als onafgemaakt (R-VEILIG-H2)."""
        self._einde_in_geheugen[nonce] = (status, after_hash, detail)

    def stop_in_geheugen(
        self, reason: dict[str, Any], *, nonce: str | None = None, after_hash: str | None = None, detail: str = ""
    ) -> None:
        """De stop kon niet worden vastgelegd: houd hem vast tot :meth:`stopped` hem kan vastleggen (R-VEILIG-1)."""
        self._stop_in_geheugen = (dict(reason), nonce, after_hash, detail)

    def release(self) -> bool:
        """Vrijgeven: de stop weg en de grens ``vrijgegeven_tot`` op de hoogste journaalrij, in één transactie."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                weg = conn.execute("DELETE FROM state WHERE key = 'gestopt'").rowcount > 0
                if weg:
                    grens = conn.execute("SELECT COALESCE(MAX(rowid), 0) FROM journal").fetchone()[0]
                    conn.execute(
                        "INSERT OR REPLACE INTO state (key, value) VALUES ('vrijgegeven_tot', ?)", (str(int(grens)),)
                    )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        if weg:
            self._stop_in_geheugen = None
        return weg
