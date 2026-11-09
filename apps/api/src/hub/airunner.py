"""AI-runner (stub, fase P0).

Draait als **aparte gebruiker** zonder toegang tot ``/appdata/secrets`` (signing keys, vault) en zonder toegang tot de
database-socket (contract §8, ADR-0005). In P0 doet hij niets: AI staat standaard uit, er zijn geen modellen en er
worden geen externe of betaalde aanroepen gedaan. Kan de runner de geheimen wél lezen, dan weigert hij te starten.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from pathlib import Path

log = logging.getLogger("hub.ai-runner")

FORBIDDEN = ("vault.key", "jwt-signing.ed25519", "policy-signing.ed25519", "hub-identity.ed25519")


def can_read_secrets(secrets_dir: Path) -> list[str]:
    readable: list[str] = []
    for name in FORBIDDEN:
        path = secrets_dir / name
        try:
            with path.open("rb") as fh:
                fh.read(1)
            readable.append(name)
        except (PermissionError, FileNotFoundError, IsADirectoryError):
            continue
        except OSError:
            continue
    return readable


def main(data_dir: Path, ai_enabled: bool, *, once: bool = False) -> int:
    readable = can_read_secrets(data_dir / "secrets")
    if readable:
        log.error(
            "FOUT: de AI-runner kan geheimen lezen (%s). Hij start niet: hij moet als aparte gebruiker zonder toegang "
            "tot /appdata/secrets draaien (uid %s nu).",
            ", ".join(readable),
            os.getuid(),
        )
        return 78
    if ai_enabled:
        log.warning("AI is ingeschakeld, maar in deze versie is er nog geen model of provider gekoppeld (fase P2+).")
    log.info(
        "AI-runner actief als uid %s: AI staat uit (standaard); geen modellen, geen externe aanroepen.", os.getuid()
    )
    if once:
        return 0
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    while not stop.wait(3600):
        log.info("AI-runner: nog steeds uit (standaard).")
    return 0
