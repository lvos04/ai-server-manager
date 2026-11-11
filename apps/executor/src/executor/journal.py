"""Eigen journaal van de executor in SQLite (``/appdata/executor.sqlite3``; contract 1.3 §8, ADR-0030).

- ``request_nonces``: elke ``nonce`` van een ``ExecutionRequest`` met een geldige handtekening, één keer.
- ``approval_nonces``: elke ``one_time_nonce`` van een goedkeuring, één keer (EX20), ook als de Hub zich vergist.
- ``journal``: per uitvoering de before/after-hash, de methode en de uitkomst.
- ``app_values``: de vorige waarden van een Custom App (uit ``app.config``), **versleuteld** met ``vault.key``, zodat
  ``app.rollback`` ze kan terugzetten. De Hub ziet ze nooit.
- ``state``: de toestand "gestopt" na een afwijking; blijft staan over een herstart.

Vastleggen en vergelijken gebeuren in één transactie (``BEGIN IMMEDIATE``). Is de opslag niet bruikbaar, dan
``JournalUnavailable``: de executor voert dan niets uit (fail-closed).
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import time
from collections.abc import Iterator
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
)


class JournalUnavailable(Exception):
    """Het journaal is niet bruikbaar: niets uitvoeren."""


class Journal:
    def __init__(self, path: Path, secrets_dir: Path) -> None:
        self.path = path
        self.vault = Vault(secrets_dir)

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            if not self.path.exists():
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
    def save_values(self, request_id: str, app: str, values: dict[str, Any]) -> None:
        try:
            box = self.vault.seal(json.dumps(values, sort_keys=True).encode(), AAD + request_id.encode())
        except NasLinkOnleesbaar:
            raise JournalUnavailable("vault.key") from None
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_values (request_id, app, box, created_at) VALUES (?, ?, ?, ?)",
                (request_id, app, json.dumps(box), int(time.time())),
            )

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

    # ------------------------------------------------------------------ gestopt na een afwijking
    def stopped(self) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM state WHERE key = 'gestopt'").fetchone()
        if row is None:
            return None
        try:
            value = json.loads(row[0])
        except ValueError:
            return {"code": "onbekend"}
        return value if isinstance(value, dict) else {"code": "onbekend"}

    def stop(self, reason: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES ('gestopt', ?)", (json.dumps(reason, sort_keys=True),)
            )

    def release(self) -> bool:
        with self._connect() as conn:
            return conn.execute("DELETE FROM state WHERE key = 'gestopt'").rowcount > 0
