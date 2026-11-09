"""Globaal auditspoor van alle beheerhandelingen: **append-only met hash-ketting** (ADR-0022).

- ``record()`` voegt een rij toe; ``details`` worden altijd geschoond (geheimen → ``***``).
- **Verzegelen bij commit:** vlak vóór de commit van een transactie met nieuwe auditrijen neemt de Hub een
  transactie-advisory-lock, leest de kop van de ketting en geeft elke nieuwe rij een doorlopend, gatloos
  ``ketting_nr``, ``prev_hash`` en ``hash = SHA-256(prev_hash + "\\n" + canonieke JSON van de rij)``. Het lock duurt
  alleen de commit (geen netwerk-aanroepen eronder) en serialiseert de ketting over alle processen (API en worker).
- **Append-only in de database:** een trigger weigert elke ``DELETE`` en elke ``UPDATE`` behalve het eenmalig
  verzegelen van een nog niet verzegelde rij (migratie 0006). Wie de trigger omzeilt (eigenaar van de database),
  breekt de ketting: ``verify()`` vindt een gewijzigde, verwijderde of ingevoegde rij.
- **Anker buiten de database:** de worker schrijft de kop (nr + hash) periodiek naar ``/appdata/audit/anker.jsonl``;
  ``verify()`` vergelijkt die, zodat ook het afknippen van de staart (laatste rijen weg) zichtbaar wordt.

De canonieke vorm (versie 1) is vastgelegd in ``canonical_v1``; migratie 0006 gebruikt een bevroren kopie om bestaande
rijen te verzegelen. Nooit wijzigen zonder nieuwe versie en migratie.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session

from hub.models import AuditEvent
from hub.redact import redact
from hub.timeutil import iso, utcnow

log = logging.getLogger("hub.audit")

AUDIT_LOCK_KEY = 0x4855_4241_5544_4954  # "HUBAUDIT"
GENESIS = "0" * 64
PENDING_KEY = "audit_pending"
ANCHOR_KEEP = 500


def record(
    db: Session,
    *,
    actor_type: str,
    actor_id: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    details: dict[str, Any] | None = None,
    trace_id: str = "",
) -> AuditEvent:
    ev = AuditEvent(
        actor_type=actor_type[:16],
        actor_id=actor_id[:64],
        action=action[:96],
        target_type=target_type[:64],
        target_id=target_id[:128],
        details=redact(details or {}),
        trace_id=trace_id[:36],
        at=utcnow(),
    )
    db.add(ev)
    db.info.setdefault(PENDING_KEY, []).append(ev)
    return ev


# ------------------------------------------------------------------ canonieke vorm en hash (versie 1)
def _ts(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="microseconds")


def canonical_v1(
    *,
    nr: int,
    at: datetime,
    actor_type: str,
    actor_id: str,
    action: str,
    target_type: str,
    target_id: str,
    details: Any,
    trace_id: str,
) -> bytes:
    data = {
        "v": 1,
        "nr": nr,
        "op": _ts(at),
        "actor_type": actor_type,
        "actor_id": actor_id,
        "actie": action,
        "doel_type": target_type,
        "doel_id": target_id,
        "details": details,
        "trace_id": trace_id,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def chain_hash(prev_hash: str, canonical: bytes) -> str:
    return hashlib.sha256(prev_hash.encode("ascii") + b"\n" + canonical).hexdigest()


_SELECT_BY_IDS = (
    "SELECT id, at, actor_type, actor_id, action, target_type, target_id, details, trace_id "
    "FROM audit_event WHERE id = ANY(:ids)"
)
_SELECT_BATCH = (
    "SELECT id, at, actor_type, actor_id, action, target_type, target_id, details, trace_id, "
    "ketting_nr, prev_hash, hash FROM audit_event WHERE ketting_nr > :after ORDER BY ketting_nr LIMIT :n"
)


def _row_canonical(row: Any, nr: int) -> bytes:
    return canonical_v1(
        nr=nr,
        at=row.at,
        actor_type=row.actor_type,
        actor_id=row.actor_id,
        action=row.action,
        target_type=row.target_type,
        target_id=row.target_id,
        details=row.details,
        trace_id=row.trace_id,
    )


def head(db: Session) -> tuple[int, str]:
    row = db.execute(
        text("SELECT ketting_nr, hash FROM audit_event WHERE ketting_nr IS NOT NULL ORDER BY ketting_nr DESC LIMIT 1")
    ).first()
    return (int(row[0]), str(row[1])) if row is not None else (0, GENESIS)


def seal_pending(session: Session) -> int:
    """Verzegel de nieuwe auditrijen van deze transactie (aangeroepen vlak vóór commit)."""
    pending: list[AuditEvent] = [e for e in session.info.get(PENDING_KEY, []) if e.hash is None]
    if not pending:
        session.info.pop(PENDING_KEY, None)
        return 0
    session.flush()  # ids toekennen; de rijen staan nu (onverzegeld) in deze transactie
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": AUDIT_LOCK_KEY})
    nr, prev = head(session)
    ids = sorted(e.id for e in pending)
    # Lees de rijen zoals de database ze bewaart (JSONB-normalisatie), zodat verify() exact dezelfde vorm hasht.
    stored = {r.id: r for r in session.execute(text(_SELECT_BY_IDS), {"ids": ids})}
    by_id = {e.id: e for e in pending}
    for rid in ids:
        nr += 1
        h = chain_hash(prev, _row_canonical(stored[rid], nr))
        ev = by_id[rid]
        ev.ketting_nr, ev.prev_hash, ev.hash = nr, prev, h
        prev = h
    session.info.pop(PENDING_KEY, None)
    return len(ids)


@event.listens_for(Session, "before_commit")
def _before_commit(session: Session) -> None:
    if session.info.get(PENDING_KEY):
        seal_pending(session)


@event.listens_for(Session, "after_rollback")
def _after_rollback(session: Session) -> None:
    session.info.pop(PENDING_KEY, None)


# ------------------------------------------------------------------ verificatie
def _batches(db: Session, size: int) -> Iterator[list[Any]]:
    after = 0
    while True:
        rows = list(db.execute(text(_SELECT_BATCH), {"after": after, "n": size}))
        if not rows:
            return
        yield rows
        after = int(rows[-1].ketting_nr)


def anchor_path(data_dir: Path) -> Path:
    return data_dir / "audit" / "anker.jsonl"


def read_anchors(data_dir: Path) -> list[dict[str, Any]]:
    p = anchor_path(data_dir)
    if not p.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict) and isinstance(item.get("nr"), int) and isinstance(item.get("hash"), str):
            out.append(item)
    return out


def write_anchor(db: Session, data_dir: Path, now: datetime | None = None) -> dict[str, Any]:
    """Schrijf de kop van de ketting naar het ankerbestand als die veranderd is (worker, periodiek)."""
    nr, h = head(db)
    if nr == 0:
        return {"anker": "leeg"}
    anchors = read_anchors(data_dir)
    if anchors and anchors[-1]["nr"] == nr and anchors[-1]["hash"] == h:
        return {"anker": "ongewijzigd", "nr": nr}
    p = anchor_path(data_dir)
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    item = {"nr": nr, "hash": h, "op": iso(now or utcnow())}
    anchors.append(item)
    if len(anchors) > ANCHOR_KEEP * 4:
        anchors = anchors[-ANCHOR_KEEP:]
        tmp = p.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(a, separators=(",", ":")) + "\n" for a in anchors))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    else:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(item, separators=(",", ":")) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    return {"anker": "geschreven", "nr": nr}


def verify(db: Session, data_dir: Path | None = None, *, batch: int = 1000) -> dict[str, Any]:
    """Controleer de hele ketting: doorlopende nummers, koppeling, inhoud en (als aanwezig) het anker.

    Uitkomst ``intact`` | ``verbroken``; bij een fout alleen het nummer, de rij-id en de soort fout (geen inhoud)."""
    started = utcnow()
    unsealed = int(db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.hash.is_(None))) or 0)
    prev, expected, checked = GENESIS, 1, 0
    errors: list[dict[str, Any]] = []
    hashes: dict[int, str] = {}
    for rows in _batches(db, batch):
        for r in rows:
            nr = int(r.ketting_nr)
            if nr != expected:
                errors.append({"soort": "gat_in_nummering", "verwacht_nr": expected, "gevonden_nr": nr, "id": r.id})
                break
            if r.prev_hash != prev:
                errors.append({"soort": "koppeling_verbroken", "nr": nr, "id": r.id})
                break
            if chain_hash(prev, _row_canonical(r, nr)) != r.hash:
                errors.append({"soort": "inhoud_gewijzigd", "nr": nr, "id": r.id})
                break
            prev, expected, checked = r.hash, expected + 1, checked + 1
            hashes[nr] = r.hash
            if len(hashes) > 4096:  # alleen recente kop bewaren voor de ankercontrole
                hashes.pop(next(iter(hashes)))
        if errors:
            break
    if unsealed:
        errors.append({"soort": "onverzegelde_rijen", "aantal": unsealed})
    anchor: dict[str, Any] = {"status": "geen_anker"}
    if data_dir is not None and not errors:
        anchors = read_anchors(data_dir)
        if anchors:
            last = anchors[-1]
            if last["nr"] > checked:
                anchor = {
                    "status": "afgeknipt",
                    "anker_nr": last["nr"],
                    "laatste_nr": checked,
                    "anker_op": last.get("op"),
                }
                errors.append({"soort": "staart_ontbreekt", "anker_nr": last["nr"], "laatste_nr": checked})
            else:
                stored = hashes.get(last["nr"])
                if stored is None:
                    stored_row = db.execute(
                        text("SELECT hash FROM audit_event WHERE ketting_nr = :n"), {"n": last["nr"]}
                    ).first()
                    stored = str(stored_row[0]) if stored_row else None
                if stored != last["hash"]:
                    anchor = {"status": "afwijkend", "anker_nr": last["nr"], "anker_op": last.get("op")}
                    errors.append({"soort": "anker_afwijkend", "anker_nr": last["nr"]})
                else:
                    anchor = {"status": "ok", "anker_nr": last["nr"], "anker_op": last.get("op")}
    return {
        "status": "verbroken" if errors else "intact",
        "gecontroleerd": checked,
        "kop": {"nr": checked, "hash": prev if checked else None},
        "fouten": errors[:10],
        "anker": anchor,
        "gecontroleerd_op": iso(started),
    }


def to_dict(r: AuditEvent) -> dict[str, Any]:
    return {
        "id": r.id,
        "op": iso(r.at),
        "actor_type": r.actor_type,
        "actor_id": r.actor_id,
        "actie": r.action,
        "doel_type": r.target_type,
        "doel_id": r.target_id,
        "details": r.details,
        "trace_id": r.trace_id,
        "ketting_nr": r.ketting_nr,
        "prev_hash": r.prev_hash,
        "hash": r.hash,
    }
