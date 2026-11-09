"""Log-index (B09-004): een **alleen-lezen** logsink met geschoonde, gestructureerde en begrensde regels.

- Bronnen: de eigen processen van de Hub (``hub-api``, ``hub-worker``; vanaf ``WARNING``) via ``DbLogHandler``, en
  eigen diensten via ``POST /api/v1/logs`` (service-token). TrueNAS-containerlogs leest de Hub (nog) niet: die bron
  is ``capability_unavailable`` (NIET GEVALIDEERD welke methode de alleen-lezen-sleutel daarvoor mag gebruiken).
- **Schonen vóór opslag** met ``redact_log_text``: geheimen, tokens, JWT's, PEM, lange hex/base64, e-mail en
  IP-adressen (alleen de soort blijft), plus de exacte waarde van elk geheim uit de vault en elk door de Hub
  uitgegeven token (alleen SHA-256-vingerafdrukken in het geheugen). Wat niet geschoond is, komt nooit in de index.
- **Grenzen:** bericht ≤ 2000 tekens, velden ≤ 4 KiB, per bron hooguit ``log_ingest_max_per_minute`` regels per
  minuut, retentie ``log_retention_seconds`` en hooguit ``log_max_rows`` regels.
- De sink voert nooit iets uit op grond van loginhoud: logregels zijn gegevens (EX17).
"""

from __future__ import annotations

import contextvars
import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from hub.models import EnrollmentGrant, LogEntry, ServiceToken, VaultSecret, WebSession
from hub.redact import SecretMatcher, redact_log_text, redact_log_value
from hub.timeutil import utcnow
from hub.vault import Vault

log = logging.getLogger("hub.logsink")
current_trace: contextvars.ContextVar[str | None] = contextvars.ContextVar("hub_trace_id", default=None)

NIVEAUS = ("debug", "info", "warning", "error", "critical")
MAX_BERICHT = 2000
MAX_VELDEN_BYTES = 4096
_CACHE_TTL = 60.0


@dataclass
class Regel:
    op: datetime
    bron: str
    niveau: str
    bericht: str
    logger: str = ""
    trace_id: str | None = None
    velden: dict[str, Any] | None = None


# ------------------------------------------------------------------ bekende geheimen (alleen vingerafdrukken)
class _MatcherCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._matcher = SecretMatcher()
        self._key: tuple[Any, ...] | None = None
        self._at = 0.0

    def get(self, db: Session, vault: Vault | None) -> SecretMatcher:
        key = (
            db.scalar(select(func.max(VaultSecret.updated_at))),
            db.scalar(select(func.count()).select_from(VaultSecret)),
            db.scalar(select(func.max(ServiceToken.created_at))),
        )
        with self._lock:
            if key == self._key and time.monotonic() - self._at < _CACHE_TTL:
                return self._matcher
        fps: set[str] = set()
        if vault is not None:
            for row in db.scalars(select(VaultSecret)):
                try:
                    value = vault.decrypt(row.ref, row.nonce, row.ciphertext)
                except Exception:  # noqa: S112 - een onleesbaar geheim kan niet lekken via deze weg
                    continue
                if len(value) >= 8:
                    fps.add(SecretMatcher.fingerprint(value))
                del value
        # Door de Hub uitgegeven tokens staan al als SHA-256 in de database.
        fps.update(db.scalars(select(ServiceToken.token_hash).where(ServiceToken.revoked_at.is_(None))))
        fps.update(db.scalars(select(WebSession.token_hash).where(WebSession.revoked_at.is_(None))))
        fps.update(db.scalars(select(EnrollmentGrant.secret_hash).where(EnrollmentGrant.used_at.is_(None))))
        matcher = SecretMatcher(fps)
        with self._lock:
            self._matcher, self._key, self._at = matcher, key, time.monotonic()
        return matcher

    def clear(self) -> None:
        with self._lock:
            self._key = None


MATCHERS = _MatcherCache()


def clean(regel: Regel, matcher: SecretMatcher | None) -> LogEntry:
    velden = redact_log_value(regel.velden or {}, matcher)
    raw = json.dumps(velden, ensure_ascii=False, default=str)
    if len(raw.encode()) > MAX_VELDEN_BYTES:
        velden = {"_ingekort": True, "sleutels": sorted(str(k) for k in (velden or {}))[:20]}
    niveau = regel.niveau.lower() if regel.niveau.lower() in NIVEAUS else "info"
    return LogEntry(
        op=regel.op,
        ontvangen_op=utcnow(),
        bron=regel.bron[:64],
        niveau=niveau,
        logger=redact_log_text(regel.logger, matcher, max_len=96),
        bericht=redact_log_text(regel.bericht, matcher, max_len=MAX_BERICHT),
        trace_id=regel.trace_id[:36] if regel.trace_id else None,
        velden=velden if isinstance(velden, dict) else {"waarde": velden},
    )


def store(db: Session, regels: list[Regel], vault: Vault | None) -> int:
    if not regels:
        return 0
    matcher = MATCHERS.get(db, vault)
    for r in regels:
        db.add(clean(r, matcher))
    db.flush()
    return len(regels)


def recent_count(db: Session, bron: str, now: datetime, seconds: int = 60) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(LogEntry)
            .where(LogEntry.bron == bron, LogEntry.ontvangen_op >= now - timedelta(seconds=seconds))
        )
        or 0
    )


def prune(db: Session, retention_seconds: int, max_rows: int, now: datetime | None = None) -> dict[str, int]:
    now = now or utcnow()
    old = db.execute(delete(LogEntry).where(LogEntry.op < now - timedelta(seconds=retention_seconds)))
    removed_old = int(getattr(old, "rowcount", 0) or 0)
    total = int(db.scalar(select(func.count()).select_from(LogEntry)) or 0)
    removed_extra = 0
    if total > max_rows:
        cutoff = db.scalar(select(LogEntry.id).order_by(LogEntry.id.desc()).offset(max_rows).limit(1))
        if cutoff is not None:
            res = db.execute(delete(LogEntry).where(LogEntry.id <= cutoff))
            removed_extra = int(getattr(res, "rowcount", 0) or 0)
    return {"verouderd": removed_old, "boven_maximum": removed_extra}


# ------------------------------------------------------------------ eigen processen → log-index
class DbLogHandler(logging.Handler):
    """Zet logrecords (standaard vanaf WARNING) in een begrensde wachtrij; een achtergronddraad schrijft ze geschoond
    weg. Nooit blokkerend: is de wachtrij vol, dan telt de handler het verlies. Fouten bij wegschrijven worden
    ingeslikt (de normale log naar stdout blijft het primaire spoor)."""

    def __init__(
        self,
        factory: sessionmaker[Session],
        bron: str,
        vault_loader: Any = None,
        level: int = logging.WARNING,
        max_queue: int = 1000,
        flush_seconds: float = 2.0,
    ) -> None:
        super().__init__(level)
        self.factory, self.bron, self.vault_loader = factory, bron, vault_loader
        self.q: queue.Queue[Regel] = queue.Queue(maxsize=max_queue)
        self.dropped = 0
        self.flush_seconds = flush_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name=f"logsink-{bron}", daemon=True)
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith(("hub.logsink", "sqlalchemy", "alembic")):
            return
        try:
            msg = record.getMessage()
            if record.exc_info and record.exc_info[0] is not None:
                msg += f" [{record.exc_info[0].__name__}]"
            self.q.put_nowait(
                Regel(
                    op=datetime.fromtimestamp(record.created, tz=UTC),
                    bron=self.bron,
                    niveau=record.levelname.lower(),
                    bericht=msg,
                    logger=record.name,
                    trace_id=current_trace.get(),
                )
            )
        except queue.Full:
            self.dropped += 1
        except Exception:  # noqa: S110 - een log-handler mag de app nooit laten falen
            pass

    def _drain(self) -> list[Regel]:
        out: list[Regel] = []
        while len(out) < 500:
            try:
                out.append(self.q.get_nowait())
            except queue.Empty:
                break
        return out

    def flush_now(self) -> int:
        regels = self._drain()
        if not regels:
            return 0
        try:
            vault = self.vault_loader() if self.vault_loader else None
            with self.factory() as db:
                n = store(db, regels, vault)
                db.commit()
                return n
        except Exception:
            self.dropped += len(regels)
            return 0

    def _loop(self) -> None:
        while not self._stop.wait(self.flush_seconds):
            self.flush_now()
        self.flush_now()

    def close(self) -> None:
        self._stop.set()
        if self._thread.is_alive() and threading.current_thread() is not self._thread:
            self._thread.join(timeout=5)
        super().close()


def install(
    factory: sessionmaker[Session], bron: str, vault_loader: Any = None, level: str = "warning"
) -> DbLogHandler:
    handler = DbLogHandler(factory, bron, vault_loader, level=getattr(logging, level.upper(), logging.WARNING))
    logging.getLogger("hub").addHandler(handler)
    return handler


def uninstall(handler: DbLogHandler) -> None:
    logging.getLogger("hub").removeHandler(handler)
    handler.close()


def to_dict(r: LogEntry) -> dict[str, Any]:
    from hub.timeutil import iso

    return {
        "id": r.id,
        "op": iso(r.op),
        "bron": r.bron,
        "niveau": r.niveau,
        "logger": r.logger,
        "bericht": r.bericht,
        "trace_id": r.trace_id,
        "velden": r.velden,
    }
