"""Persistente ``jti``-replaycache van de executor (contract 1.2 §4.6).

- Sleutel ``(iss, jti)``; bewaard tot ``exp`` + 30 s (daarna is de JWT zelf verlopen: ``token_expired``).
- Een **mutatie** met een al gebruikte ``jti`` → 401 ``token_replayed``, behalve een exacte herhaling (zelfde ``jti``,
  methode, pad en ``Idempotency-Key``): die krijgt het opgeslagen antwoord terug (geen tweede uitvoering).
- Lezen (GET/HEAD) mag binnen de levensduur vaker en komt hier niet langs.
- Opslag in SQLite in ``/appdata`` (0600, WAL), dus gedeeld door alle processen en bestand tegen een herstart; de
  vergelijking en het vastleggen gebeuren in één transactie (``BEGIN IMMEDIATE``).
- Is de cache niet bruikbaar, dan ``ReplayUnavailable`` → 503 ``replay_check_unavailable`` (fail-closed, nooit
  doorlaten).
"""

from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CLOCK_SKEW = 30
FILE_NAME = "executor.sqlite3"


class ReplayUnavailable(Exception):
    """De replaycontrole kan niet worden uitgevoerd (opslag kapot of niet schrijfbaar)."""


@dataclass(frozen=True)
class Claim:
    """Uitkomst van :meth:`ReplayCache.claim`.

    ``kind``: ``new`` (eerste gebruik; nu vastgelegd), ``repeat`` (exacte herhaling; ``status``/``body`` gevuld),
    ``in_progress`` (exacte herhaling terwijl het eerste verzoek nog loopt) of ``replayed`` (andere mutatie).
    """

    kind: str
    status: int | None = None
    body: Any = None


class ReplayCache:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        try:
            if not self.path.exists():
                fd = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
                os.close(fd)
            conn = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        except (OSError, sqlite3.Error) as exc:
            raise ReplayUnavailable(type(exc).__name__) from None
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS jti_replay ("
                " iss TEXT NOT NULL, jti TEXT NOT NULL, keep_until INTEGER NOT NULL,"
                " method TEXT NOT NULL, path TEXT NOT NULL, idempotency_key TEXT NOT NULL,"
                " status INTEGER, body TEXT, PRIMARY KEY (iss, jti))"
            )
            yield conn
        except sqlite3.Error as exc:
            raise ReplayUnavailable(type(exc).__name__) from None
        finally:
            conn.close()

    def claim(
        self, *, iss: str, jti: str, exp: int, method: str, path: str, idempotency_key: str, now: int | None = None
    ) -> Claim:
        t = int(time.time()) if now is None else now
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM jti_replay WHERE keep_until < ?", (t,))
                row = conn.execute(
                    "SELECT method, path, idempotency_key, status, body FROM jti_replay WHERE iss = ? AND jti = ?",
                    (iss, jti),
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO jti_replay (iss, jti, keep_until, method, path, idempotency_key)"
                        " VALUES (?, ?, ?, ?, ?, ?)",
                        (iss, jti, exp + CLOCK_SKEW, method, path, idempotency_key),
                    )
                    result = Claim("new")
                elif (row[0], row[1], row[2]) != (method, path, idempotency_key):
                    result = Claim("replayed")
                elif row[3] is None:
                    result = Claim("in_progress")
                else:
                    result = Claim("repeat", int(row[3]), json.loads(row[4]) if row[4] else None)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return result

    def store_result(self, *, iss: str, jti: str, status: int, body: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE jti_replay SET status = ?, body = ? WHERE iss = ? AND jti = ?",
                (status, json.dumps(body, separators=(",", ":"), ensure_ascii=False), iss, jti),
            )

    def usable(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1 FROM jti_replay LIMIT 1").fetchall()
        except ReplayUnavailable:
            return False
        return True
