"""First-start-init (contract §3).

Maakt ontbrekende geheimen in ``/appdata/secrets`` (map 0700, bestanden 0600, eigenaar = procesgebruiker 568).
Regels:
- **Nooit overschrijven.** Een bestaand bestand blijft staan; alleen te ruime rechten worden aangescherpt.
  Een leeg of onleesbaar bestaand geheim is een harde fout (overschrijven zou bv. de vault onleesbaar maken).
- Ed25519-sleutels als PKCS#8-PEM: ``hub-identity``, ``jwt-signing``, ``policy-signing``; ``vault.key`` = 32 bytes
  (AES-256-GCM), base64.
- Eenmalige **setupcode** zolang er nog geen beheerder is: alleen de hash staat op schijf, de code zelf alleen in de
  app-log (TrueNAS → Apps → app → Logs). Bij elke containerstart (``hub init``) zonder beheerder wordt een nieuwe code
  gemaakt (de vorige vervalt), zodat de laatste regel in de log altijd de geldige code is (ADR-0004). Andere processen
  (bv. de API in ontwikkeling) maken alleen een code als er nog geen geldige is (``new_setup_code=False``).
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
import secrets
import stat
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ED25519_KEYS = ("hub-identity.ed25519", "jwt-signing.ed25519", "policy-signing.ed25519")
VAULT_KEY = "vault.key"
SETUP_HASH = "setup-code.json"
SETUP_DONE = "setup-completed"
# Crockford-base32 zonder verwarrende tekens (geen I, L, O, U)
SETUP_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


class FirstStartError(RuntimeError):
    """Harde fout bij first-start; de melding is Nederlands en komt in de app-log."""


@dataclass
class FirstStartResult:
    created: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    tightened: list[str] = field(default_factory=list)
    setup_code: str | None = None
    setup_code_expires_at: datetime | None = None
    setup_completed: bool = False


def _write_exclusive(path: Path, data: bytes) -> None:
    """Schrijf alleen als het bestand nog niet bestaat (O_EXCL), met 0600."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def _write_replace(path: Path, data: bytes) -> None:
    """Atomair vervangen (alleen voor de setupcode-hash, die per start mag wisselen)."""
    tmp = path.with_name(path.name + ".tmp")
    with contextlib.suppress(FileNotFoundError):
        tmp.unlink()
    _write_exclusive(tmp, data)
    os.replace(tmp, path)


def _ed25519_pem() -> bytes:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _vault_key() -> bytes:
    return base64.b64encode(secrets.token_bytes(32)) + b"\n"


def _validate_existing(path: Path) -> None:
    raw = path.read_bytes()
    if not raw.strip():
        raise FirstStartError(
            f"geheim {path.name} bestaat maar is leeg. Het wordt bewust niet overschreven; "
            f"zet het uit een back-up terug of verwijder het bewust (dan maakt de app een nieuw)."
        )
    if path.name == VAULT_KEY:
        try:
            key = base64.b64decode(raw.strip(), validate=True)
        except ValueError as exc:
            raise FirstStartError(f"{path.name} is geen geldige base64-sleutel; niet overschreven.") from exc
        if len(key) != 32:
            raise FirstStartError(f"{path.name} heeft {len(key)} bytes in plaats van 32; niet overschreven.")
    elif path.name.endswith(".ed25519"):
        try:
            key_obj = serialization.load_pem_private_key(raw, password=None)
        except ValueError as exc:
            raise FirstStartError(f"{path.name} is geen geldige PEM-sleutel; niet overschreven.") from exc
        if not isinstance(key_obj, Ed25519PrivateKey):
            raise FirstStartError(f"{path.name} is geen Ed25519-sleutel; niet overschreven.")


def _ensure_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        os.chmod(path, 0o700)


def _tighten(path: Path, result: FirstStartResult) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        os.chmod(path, 0o600)
        result.tightened.append(path.name)


def generate_setup_code() -> str:
    raw = "".join(secrets.choice(SETUP_ALPHABET) for _ in range(12))
    return f"{raw[0:4]}-{raw[4:8]}-{raw[8:12]}"


def normalize_setup_code(code: str) -> str:
    cleaned = "".join(ch for ch in code.upper() if ch.isalnum())
    return cleaned.replace("O", "0").replace("I", "1").replace("L", "1")


def hash_setup_code(code: str, salt: bytes) -> str:
    return hashlib.sha256(salt + normalize_setup_code(code).encode()).hexdigest()


def _valid_setup_hash_exists(secrets_dir: Path, now: datetime) -> bool:
    path = secrets_dir / SETUP_HASH
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        expires = datetime.strptime(data["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, KeyError, OSError):
        return False
    return now < expires


def ensure_secrets(
    secrets_dir: Path,
    *,
    setup_code_ttl_seconds: int = 24 * 3600,
    new_setup_code: bool = True,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FirstStartResult:
    """Maak ontbrekende geheimen; nooit overschrijven. Geeft de (nieuwe) setupcode terug zolang setup open is."""
    result = FirstStartResult()
    _ensure_dir(secrets_dir)

    generators: dict[str, Callable[[], bytes]] = dict.fromkeys(ED25519_KEYS, _ed25519_pem)
    generators[VAULT_KEY] = _vault_key
    for name, gen in generators.items():
        path = secrets_dir / name
        if path.exists():
            _validate_existing(path)
            _tighten(path, result)
            result.kept.append(name)
        else:
            _write_exclusive(path, gen())
            result.created.append(name)

    done = secrets_dir / SETUP_DONE
    if done.exists():
        result.setup_completed = True
        with contextlib.suppress(FileNotFoundError):
            (secrets_dir / SETUP_HASH).unlink()
        return result

    if not new_setup_code and _valid_setup_hash_exists(secrets_dir, now()):
        return result  # er is al een geldige code (staat in de log van de eerste start)

    code = generate_setup_code()
    salt = secrets.token_bytes(16)
    expires = now() + timedelta(seconds=setup_code_ttl_seconds)
    payload = {
        "salt": salt.hex(),
        "hash": hash_setup_code(code, salt),
        "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    _write_replace(secrets_dir / SETUP_HASH, json.dumps(payload).encode())
    result.setup_code = code
    result.setup_code_expires_at = expires
    return result


def verify_setup_code(secrets_dir: Path, code: str, *, now: datetime | None = None) -> bool:
    path = secrets_dir / SETUP_HASH
    if (secrets_dir / SETUP_DONE).exists() or not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
        salt = bytes.fromhex(data["salt"])
        expires = datetime.strptime(data["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (ValueError, KeyError, OSError):
        return False
    if (now or datetime.now(UTC)) > expires:
        return False
    return hmac.compare_digest(hash_setup_code(code, salt), str(data["hash"]))


def mark_setup_completed(secrets_dir: Path) -> None:
    done = secrets_dir / SETUP_DONE
    if not done.exists():
        _write_exclusive(done, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ").encode())
    with contextlib.suppress(FileNotFoundError):
        (secrets_dir / SETUP_HASH).unlink()


def setup_pending(secrets_dir: Path) -> bool:
    return not (secrets_dir / SETUP_DONE).exists()


def log_lines(result: FirstStartResult) -> list[str]:
    lines: list[str] = []
    if result.created:
        lines.append("nieuwe geheimen aangemaakt in secrets/: " + ", ".join(sorted(result.created)))
    if result.tightened:
        lines.append("rechten aangescherpt naar 0600: " + ", ".join(sorted(result.tightened)))
    if result.setup_code and result.setup_code_expires_at:
        expires = result.setup_code_expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append("=" * 72)
        lines.append(f"SETUPCODE (eenmalig, voor het eerste beheerdersaccount): {result.setup_code}")
        lines.append(f"Geldig tot {expires}. Open de Hub in je browser en vul deze code in de setup-wizard in.")
        lines.append("Verlopen of kwijt? Herstart de app: er verschijnt dan een nieuwe code (de oude vervalt).")
        lines.append("=" * 72)
    elif result.setup_completed:
        lines.append("setup is afgerond; er wordt geen setupcode meer getoond")
    return lines
