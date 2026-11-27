"""AI-runner voor begrensde diagnoseaanvragen.

Draait als **aparte gebruiker** zonder toegang tot ``/appdata/secrets`` (signing keys, vault) en zonder toegang tot de
database-socket (contract §8, ADR-0005). AI staat standaard uit. Het lokale diagnosekanaal opent
alleen na de isolatiecontrole, als uid 569 en bij expliciete inschakeling.
"""

from __future__ import annotations

import logging
import os
import signal
import stat
import threading
from pathlib import Path

from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict

from hub import config
from hub.ai import runner

log = logging.getLogger("hub.ai-runner")

FORBIDDEN = (
    "vault.key",
    "jwt-signing.ed25519",
    "policy-signing.ed25519",
    "hub-identity.ed25519",
)


def can_read_secrets(secrets_dir: Path) -> list[str]:
    readable: list[str] = []
    for name in FORBIDDEN:
        path = secrets_dir / name
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                raise OSError("Onverwacht bestandstype bij de sleutelcontrole")
            # Een geopend bestand bewijst leesrecht. De sleutelinhoud hoeft niet het proces in.
            with path.open("rb"):
                readable.append(name)
        except (PermissionError, FileNotFoundError):
            continue
    return readable


def _directory_accessible(directory: Path) -> bool:
    try:
        with os.scandir(directory):
            return True
    except FileNotFoundError:
        return False
    except PermissionError:
        pass
    # Een map zonder leesrecht kan nog doorgang geven naar een bekend gegevensbestand of een toekomstige socket.
    # De letterlijke '/.' laat de kernel het doorgangsrecht op de map zelf toetsen.
    try:
        os.stat(os.path.join(directory, "."))
    except (PermissionError, FileNotFoundError):
        return False
    return True


def _database_isolated(data_dir: Path) -> bool:
    directories = {data_dir / "postgres", Path(config.DEFAULT_SOCKET_DIR)}
    if pgdata := os.environ.get("PGDATA"):
        directories.add(Path(pgdata))
    # De bewaker gebruikt één lokale socket. Controleer ook eventuele expliciete locaties bij een losse CLI-start.
    # Een netwerkadres of een indirecte service is niet lokaal te toetsen zonder verbinding.
    params = conninfo_to_dict(config.get_settings().libpq_url)
    if params.get("service") or params.get("hostaddr") or os.environ.get("PGSERVICE") or os.environ.get("PGHOSTADDR"):
        return False
    env_host = os.environ.get("PGHOST", "")
    hosts = env_host.split(",") if env_host else []
    hosts.extend(str(params.get("host") or env_host).split(","))
    for host in hosts:
        directory = Path(host)
        if not directory.is_absolute():
            return False
        directories.add(directory)
    return not any(_directory_accessible(directory) for directory in directories)


def main(data_dir: Path, ai_enabled: bool, *, once: bool = False) -> int:
    try:
        isolated = not can_read_secrets(data_dir / "secrets") and _database_isolated(data_dir)
    except (OSError, ProgrammingError, ValueError):
        isolated = False
    if not isolated:
        log.error("De AI-runner weigert te starten omdat de isolatie van sleutels en database niet vaststaat.")
        return 78
    if ai_enabled and (os.getuid(), os.geteuid()) != (runner.RUNNER_UID, runner.RUNNER_UID):
        log.error("Het ingeschakelde diagnosekanaal vereist uid 569.")
        return 78
    if once:
        return 0
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if ai_enabled:
        runner.bedien(config.get_settings(), stop)
    else:
        log.info("AI staat uit. De runner wacht zonder aanbieder te benaderen.")
        stop.wait()
    return 0
