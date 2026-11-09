"""Entrypoint van de executor-image: als root alleen /appdata aan 568:568 geven, daarna alles als 568."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

UID, GID = 568, 568
PR_SET_NO_NEW_PRIVS = 38
DATA = Path(os.environ.get("EXECUTOR_DATA_DIR", "/appdata"))


def fail(msg: str) -> None:
    print(f"[executor] FOUT: {msg}", flush=True)
    time.sleep(30)
    sys.exit(78)


def main() -> None:
    if not DATA.exists():
        fail(f"{DATA} bestaat niet. Koppel een eigen dataset (Host Path) aan {DATA}.")
    if os.getuid() == 0:
        for p in (DATA, DATA / "secrets"):
            p.mkdir(exist_ok=True)
            st = p.stat()
            if (st.st_uid, st.st_gid) != (UID, GID):
                print(f"[executor] eigenaar van {p} wordt {UID}:{GID}", flush=True)
                os.chown(p, UID, GID)
                if p.name == "secrets":
                    for f in p.iterdir():
                        os.lchown(f, UID, GID)
        os.setgroups([])
        os.setgid(GID)
        os.setuid(UID)
    # Contract §10 'no-new-privileges' (kan niet in het standaardformulier): blijft gelden na execv.
    try:
        if int(ctypes.CDLL(None, use_errno=True).prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) != 0:
            print("[executor] WAARSCHUWING: no-new-privileges kon niet worden gezet", flush=True)
    except (OSError, AttributeError):
        print("[executor] WAARSCHUWING: no-new-privileges niet beschikbaar", flush=True)
    if not os.access(DATA, os.W_OK):
        fail(f"gebruiker {os.getuid()} kan niet schrijven in {DATA}; laat 'Custom User' uit of pas de rechten aan.")
    rc = subprocess.run([sys.executable, "-m", "executor", "init"], check=False).returncode
    if rc != 0:
        fail("eigen geheimen aanmaken mislukt (zie hierboven); bestaande geheimen worden nooit overschreven")
    os.execv(sys.executable, [sys.executable, "-m", "executor", "api"])  # noqa: S606 — vaste argumenten


if __name__ == "__main__":
    main()
