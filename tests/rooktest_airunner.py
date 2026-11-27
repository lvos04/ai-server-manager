"""Proef als UID 569 in de Hub-image, met aparte tijdelijke fixtures voor een leesbare sleutel en databasemap."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from hub.airunner import FORBIDDEN


def controleer_start(data: Path, verwacht: int) -> None:
    start = subprocess.run(
        [sys.executable, "-m", "hub", "ai-runner", "--once"],
        env={**os.environ, "HUB_DATA_DIR": str(data)},
        check=False,
        timeout=15,
    )
    if start.returncode != verwacht:
        raise SystemExit(f"FOUT: toegangscontrole AI-runner gaf {start.returncode}, verwacht {verwacht}")


def main() -> None:
    if os.getuid() != 569 or os.geteuid() != 569:
        raise SystemExit("FOUT: kluisproef draait niet als UID 569")
    for proces in Path("/proc").glob("[0-9]*"):
        try:
            argv = (proces / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
            if argv[1:] != [b"-m", b"hub", b"ai-runner"]:
                continue
            status = (proces / "status").read_text().splitlines()
        except FileNotFoundError:
            continue
        uids = next(regel.split()[1:3] for regel in status if regel.startswith("Uid:"))
        if uids != ["569", "569"]:
            raise SystemExit("FOUT: de draaiende AI-runner heeft een verkeerde UID")
        break
    else:
        raise SystemExit("FOUT: geen draaiende AI-runner gevonden")

    data = Path("/appdata")
    for naam in FORBIDDEN:
        try:
            with (data / "secrets" / naam).open("rb"):
                raise SystemExit("FOUT: UID 569 kan een afgeschermde sleutel openen")
        except PermissionError:
            pass
    controleer_start(data, 0)
    with TemporaryDirectory() as mapnaam:
        proef = Path(mapnaam)
        kluis = proef / "secrets" / "vault.key"
        kluis.parent.mkdir()
        kluis.write_bytes(b"210")
        controleer_start(proef, 78)
        kluis.unlink()
        database = proef / "postgres"
        database.mkdir()
        (database / "PG_VERSION").write_text("16\n", encoding="ascii")
        controleer_start(proef, 78)
    print(
        "ok: AI-runner draait als 569, kluis en ondertekensleutel ontoegankelijk, "
        "leesbare proefsleutel en databasemap elk geweigerd (78)"
    )


if __name__ == "__main__":
    main()
