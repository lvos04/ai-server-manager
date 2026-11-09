"""Wachtwoorden (argon2id), tokens, rollen en rate-limit (contract §4)."""

from __future__ import annotations

import hashlib
import hmac
import math
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


CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
PAIRING_CODE_LENGTH = 12


def new_pairing_code() -> str:
    """Koppelcode voor handmatig geïnstalleerde apps: 12 tekens Crockford-base32 in groepen van 4 (~60 bit)."""
    raw = "".join(secrets.choice(CROCKFORD_ALPHABET) for _ in range(PAIRING_CODE_LENGTH))
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def normalize_pairing_code(code: str) -> str:
    """Contract 1.2 §3.3: alleen letters/cijfers, hoofdletters, ``O→0``, ``I/L→1``."""
    cleaned = "".join(ch for ch in code.upper() if ch.isascii() and ch.isalnum())
    return cleaned.replace("O", "0").replace("I", "1").replace("L", "1")


def is_valid_pairing_code(normalized: str) -> bool:
    """Precies 12 tekens uit het Crockford-alfabet (na normalisatie); anders 422."""
    return len(normalized) == PAIRING_CODE_LENGTH and all(ch in CROCKFORD_ALPHABET for ch in normalized)


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


def retry_after_seconds(
    db: Session, key: str, window_seconds: int, max_failures: int, now: datetime | None = None
) -> int:
    """Seconden tot er binnen het venster weer minder dan ``max_failures`` mislukte pogingen zijn (0 = nu al)."""
    now = now or utcnow()
    since = now - timedelta(seconds=window_seconds)
    times = list(
        db.scalars(
            select(LoginAttempt.attempted_at)
            .where(LoginAttempt.key == key, LoginAttempt.attempted_at >= since)
            .order_by(LoginAttempt.attempted_at)
        )
    )
    if len(times) < max_failures:
        return 0
    expiry = times[len(times) - max_failures] + timedelta(seconds=window_seconds)
    return max(1, math.ceil((expiry - now).total_seconds()))
