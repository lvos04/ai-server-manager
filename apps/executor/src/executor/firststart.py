"""Eigen geheimen van de executor: Ed25519-identiteit en ``vault.key`` (0600, map 0700, nooit overschrijven)."""

from __future__ import annotations

import base64
import os
import secrets
import stat
from collections.abc import Callable
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

IDENTITY = "executor-identity.ed25519"
VAULT_KEY = "vault.key"


class FirstStartError(RuntimeError):
    pass


def _write_exclusive(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def _validate(path: Path) -> None:
    raw = path.read_bytes()
    if not raw.strip():
        raise FirstStartError(f"{path.name} bestaat maar is leeg; bewust niet overschreven.")
    if path.name == VAULT_KEY:
        try:
            ok = len(base64.b64decode(raw.strip(), validate=True)) == 32
        except ValueError:
            ok = False
        if not ok:
            raise FirstStartError(f"{path.name} is geen geldige 32-byte-sleutel; niet overschreven.")
    else:
        try:
            key = serialization.load_pem_private_key(raw, password=None)
        except ValueError as exc:
            raise FirstStartError(f"{path.name} is geen geldige PEM-sleutel; niet overschreven.") from exc
        if not isinstance(key, Ed25519PrivateKey):
            raise FirstStartError(f"{path.name} is geen Ed25519-sleutel; niet overschreven.")


def _identity_pem() -> bytes:
    return Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


def _vault_key() -> bytes:
    return base64.b64encode(secrets.token_bytes(32)) + b"\n"


def ensure_secrets(secrets_dir: Path) -> list[str]:
    secrets_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if stat.S_IMODE(secrets_dir.stat().st_mode) & 0o077:
        os.chmod(secrets_dir, 0o700)
    created: list[str] = []
    gens: dict[str, Callable[[], bytes]] = {IDENTITY: _identity_pem, VAULT_KEY: _vault_key}
    for name, gen in gens.items():
        path = secrets_dir / name
        if path.exists():
            _validate(path)
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                os.chmod(path, 0o600)
        else:
            _write_exclusive(path, gen())
            created.append(name)
    return created


def public_jwk(secrets_dir: Path) -> dict[str, str] | None:
    path = secrets_dir / IDENTITY
    if not path.exists():
        return None
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        return None
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"kty": "OKP", "crv": "Ed25519", "x": base64.urlsafe_b64encode(raw).rstrip(b"=").decode(), "use": "sig"}
