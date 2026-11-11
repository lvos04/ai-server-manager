"""TrueNAS-koppeling van de executor: NAS-adres, TLS-vingerafdruk en de schrijfsleutel (contract 1.3 §3.9, ADR-0030).

- Bestand ``/appdata/secrets/naslink.json`` (0600, atomair vervangen). De sleutel staat er alleen versleuteld in
  (AES-256-GCM met ``vault.key``); buiten deze module is alleen ``laatste4`` zichtbaar.
- Adres en vingerafdruk worden **één keer** vastgelegd (eerst als ``pending``, pas na bevestiging en een geslaagde live
  test definitief). Daarna verandert alleen de sleutel; een ander adres of certificaat vraagt een nieuwe datamap.
- Onleesbaar bestand → ``_onleesbaar``: de executor voert niets uit en biedt geen sleutelformulier aan (fail-closed).
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import json
import os
import secrets
import stat
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from executor.firststart import VAULT_KEY

FILE_NAME = "naslink.json"
LOCK_NAME = ".naslink.lock"
PENDING_SECONDS = 15 * 60
AAD = b"executor-naslink-v1"
MAX_KEY_LEN = 512


class NasLinkOnleesbaar(Exception):
    """``naslink.json`` of ``vault.key`` is onleesbaar: niets uitvoeren, niets overschrijven."""


def now_iso(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "host": None,
        "port": None,
        "fingerprint": None,
        "key": None,
        "laatste4": None,
        "ingesteld_op": None,
        "rollen": [],
        "pending": None,
    }


class Vault:
    """AES-256-GCM met de eigen ``vault.key`` (32 bytes, base64). Ook gebruikt door het journaal."""

    def __init__(self, secrets_dir: Path) -> None:
        self.path = secrets_dir / VAULT_KEY

    def _aes(self) -> AESGCM:
        try:
            key = base64.b64decode(self.path.read_bytes().strip(), validate=True)
        except (OSError, ValueError):
            raise NasLinkOnleesbaar("vault.key") from None
        if len(key) != 32:
            raise NasLinkOnleesbaar("vault.key")
        return AESGCM(key)

    def seal(self, plain: bytes, aad: bytes = AAD) -> dict[str, str]:
        nonce = secrets.token_bytes(12)
        return {
            "n": base64.b64encode(nonce).decode(),
            "c": base64.b64encode(self._aes().encrypt(nonce, plain, aad)).decode(),
        }

    def open(self, box: Any, aad: bytes = AAD) -> bytes:
        try:
            nonce, ct = base64.b64decode(box["n"]), base64.b64decode(box["c"])
            return self._aes().decrypt(nonce, ct, aad)
        except (KeyError, TypeError, ValueError, InvalidTag):
            raise NasLinkOnleesbaar("versleutelde waarde") from None


class NasLinkStore:
    def __init__(self, secrets_dir: Path) -> None:
        self.dir = secrets_dir
        self.path = secrets_dir / FILE_NAME
        self.lock_path = secrets_dir / LOCK_NAME
        self.vault = Vault(secrets_dir)

    def _load(self) -> dict[str, Any] | None:
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return empty()
        except OSError:
            return None
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
                return None
            raw = os.read(fd, 64 * 1024 + 1)
        finally:
            os.close(fd)
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        if (
            not isinstance(data, dict)
            or len(raw) > 64 * 1024
            or str(data.get("schema_version", "")).split(".")[0] != "1"
        ):
            return None
        if data.get("key") is not None and not (
            isinstance(data.get("host"), str)
            and isinstance(data.get("port"), int)
            and isinstance(data.get("fingerprint"), str)
        ):
            return None
        return {**empty(), **data}

    def read(self) -> dict[str, Any]:
        data = self._load()
        return {**empty(), "_onleesbaar": True} if data is None else data

    @contextlib.contextmanager
    def update(self) -> Iterator[dict[str, Any]]:
        self.dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            data = self._load()
            if data is None:
                raise NasLinkOnleesbaar(FILE_NAME)
            yield data
            tmp = self.dir / f".{FILE_NAME}.{uuid.uuid4().hex}"
            out = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(out, (json.dumps(data, indent=1, sort_keys=True) + "\n").encode())
                os.fsync(out)
            finally:
                os.close(out)
            os.replace(tmp, self.path)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    # ------------------------------------------------------------------ lezen
    def configured(self) -> bool:
        data = self.read()
        return not data.get("_onleesbaar") and data.get("key") is not None

    def api_key(self) -> str:
        data = self.read()
        if data.get("_onleesbaar") or data.get("key") is None:
            raise NasLinkOnleesbaar("geen sleutel")
        return self.vault.open(data["key"]).decode()

    def pending(self, now: datetime | None = None) -> dict[str, Any] | None:
        """De nog te bevestigen vingerafdruk (stap 1 van het sleutelformulier), of ``None`` als die er niet is of
        verlopen is."""
        p = self.read().get("pending")
        if not isinstance(p, dict):
            return None
        try:
            started = datetime.strptime(str(p.get("started_at")), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except ValueError:
            return None
        if (now or datetime.now(UTC)) - started > timedelta(seconds=PENDING_SECONDS):
            return None
        return p

    def public(self) -> dict[str, Any]:
        """Wat de statuspagina en ``/api/v1/status`` mogen tonen: nooit de sleutel."""
        data = self.read()
        if data.get("_onleesbaar"):
            return {"ingesteld": False, "onleesbaar": True}
        return {
            "ingesteld": data.get("key") is not None,
            "onleesbaar": False,
            "nas_adres": data.get("host"),
            "nas_poort": data.get("port"),
            "tls_vingerafdruk": data.get("fingerprint"),
            "laatste4": data.get("laatste4"),
            "ingesteld_op": data.get("ingesteld_op"),
            "rollen": list(data.get("rollen") or []),
        }

    # ------------------------------------------------------------------ schrijven
    def set_pending(self, host: str, port: int, fingerprint: str) -> None:
        with self.update() as data:
            if data.get("key") is not None:
                raise NasLinkOnleesbaar("al ingesteld")
            data["pending"] = {"host": host, "port": port, "fingerprint": fingerprint, "started_at": now_iso()}

    def clear_pending(self) -> None:
        with self.update() as data:
            data["pending"] = None

    def save_key(self, host: str, port: int, fingerprint: str, api_key: str, roles: list[str]) -> None:
        """Sleutel (opnieuw) vastleggen. Adres en vingerafdruk liggen na de eerste keer vast en veranderen hier niet."""
        box = self.vault.seal(api_key.encode())
        with self.update() as data:
            if data.get("key") is not None and (data["host"], data["port"], data["fingerprint"]) != (
                host,
                port,
                fingerprint,
            ):
                raise NasLinkOnleesbaar("adres of certificaat ligt al vast")
            data.update(
                host=host,
                port=port,
                fingerprint=fingerprint,
                key=box,
                laatste4=api_key[-4:],
                ingesteld_op=now_iso(),
                rollen=sorted(roles),
                pending=None,
            )
