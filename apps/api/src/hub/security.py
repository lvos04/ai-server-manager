"""Wachtwoorden (argon2id), tokens, rollen en rate-limit (contract §4)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from enum import StrEnum

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from hub.models import LoginAttempt
from hub.timeutil import utcnow


class Role(StrEnum):
    admin = "admin"
    operator = "operator"
    viewer = "viewer"
    kind = "kind"  # kinderprofiel: alleen eigen (media)weergave, nooit beheer


ROLE_RANK = {Role.kind: 0, Role.viewer: 1, Role.operator: 2, Role.admin: 3}

# argon2id met expliciete parameters (RFC 9106 "tweede aanbevolen" profiel, geschikt voor een thuis-NAS)
_hasher = PasswordHasher(time_cost=3, memory_cost=64 * 1024, parallelism=2, hash_len=32, salt_len=16)
_DUMMY_HASH = _hasher.hash("dummy-wachtwoord-voor-gelijke-tijd")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    """Constante-tijd-achtig: ook voor onbekende gebruikers wordt een hash geverifieerd."""
    try:
        return _hasher.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def new_token(prefix: str, nbytes: int = 32) -> str:
    return f"{prefix}_{secrets.token_urlsafe(nbytes)}"


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def new_pairing_code() -> str:
    """Koppelcode voor handmatig geïnstalleerde apps: 12 tekens Crockford-base32 in groepen van 4 (~60 bit)."""
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    raw = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def normalize_pairing_code(code: str) -> str:
    cleaned = "".join(ch for ch in code.upper() if ch.isalnum())
    return cleaned.replace("O", "0").replace("I", "1").replace("L", "1")


# ------------------------------------------------------------------ rate-limit (in de database: werkt over herstarts)
def failures_in_window(db: Session, key: str, window_seconds: int, now: datetime | None = None) -> int:
    since = (now or utcnow()) - timedelta(seconds=window_seconds)
    return int(
        db.scalar(
            select(func.count())
            .select_from(LoginAttempt)
            .where(LoginAttempt.key == key, LoginAttempt.attempted_at >= since)
        )
        or 0
    )


def record_failure(db: Session, key: str) -> None:
    db.add(LoginAttempt(key=key, attempted_at=utcnow()))


def clear_failures(db: Session, key: str) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.key == key))


def prune_attempts(db: Session, older_than_seconds: int) -> None:
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < utcnow() - timedelta(seconds=older_than_seconds)))
