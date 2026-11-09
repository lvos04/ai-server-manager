"""Vault: AES-256-GCM-versleutelde opslag van credentials (contract §3).

Tabellen bevatten alleen een referentie ``vault://<scope>/<naam>``; de UI toont nooit de waarde terug, alleen de
laatste 4 tekens en de datum. De sleutel staat in ``/appdata/secrets/vault.key`` (0600) en is niet leesbaar voor de
AI-runner (aparte gebruiker).
"""

from __future__ import annotations

import base64
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.models import VaultSecret

REF_RE = re.compile(r"^vault://(?P<scope>[a-z0-9][a-z0-9_-]{0,62})/(?P<name>[a-z0-9][a-z0-9_.-]{0,126})$")


class VaultError(RuntimeError):
    pass


def make_ref(scope: str, name: str) -> str:
    ref = f"vault://{scope}/{name}"
    if not REF_RE.match(ref):
        raise VaultError(f"ongeldige vault-referentie: {ref}")
    return ref


def last4(value: str) -> str:
    return value[-4:] if len(value) >= 8 else "****"


class Vault:
    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise VaultError("vault-sleutel moet 32 bytes zijn")
        self._aes = AESGCM(key)

    @classmethod
    def from_file(cls, path: Path) -> Vault:
        return cls(base64.b64decode(path.read_bytes().strip(), validate=True))

    def encrypt(self, ref: str, plaintext: str) -> tuple[bytes, bytes]:
        nonce = secrets.token_bytes(12)
        return nonce, self._aes.encrypt(nonce, plaintext.encode(), ref.encode())

    def decrypt(self, ref: str, nonce: bytes, ciphertext: bytes) -> str:
        return self._aes.decrypt(nonce, ciphertext, ref.encode()).decode()

    def put(self, db: Session, ref: str, plaintext: str, *, actor: str) -> VaultSecret:
        if not REF_RE.match(ref):
            raise VaultError(f"ongeldige vault-referentie: {ref}")
        nonce, ct = self.encrypt(ref, plaintext)
        row = db.scalar(select(VaultSecret).where(VaultSecret.ref == ref))
        now = datetime.now(UTC)
        if row is None:
            row = VaultSecret(
                ref=ref,
                nonce=nonce,
                ciphertext=ct,
                last4=last4(plaintext),
                created_at=now,
                updated_at=now,
                updated_by=actor,
            )
            db.add(row)
        else:
            row.nonce, row.ciphertext, row.last4, row.updated_at, row.updated_by = (
                nonce,
                ct,
                last4(plaintext),
                now,
                actor,
            )
        return row

    def get(self, db: Session, ref: str) -> str | None:
        row = db.scalar(select(VaultSecret).where(VaultSecret.ref == ref))
        if row is None:
            return None
        return self.decrypt(ref, row.nonce, row.ciphertext)
