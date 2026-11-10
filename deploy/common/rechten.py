"""Rechten van de container-processen (contract 1.3 §2.2, C1.3-ASM-01): bounding set legen, wisselen naar 568 en
no_new_privs zetten. Gedeeld door de bewaker (Hub), het entrypoint (executor) en beide healthchecks.

Het standaard Custom App-formulier zet geen no-new-privileges en geen cap_drop (ix-app ``clear_caps()``): elke image
doet het zelf. Volgorde bij een start als root: eigenaarschapsstap → **bounding set leeg** (``PR_CAPBSET_DROP`` voor
elke capability; mislukt dat, dan stoppen met een Nederlandse melding) → ``setgroups([])``, ``setgid``, ``setuid`` →
``PR_SET_NO_NEW_PRIVS``. De effectieve set van het root-proces zelf blijft tot de wissel, zodat ``setuid`` in een
kindproces (``preexec_fn``) nog werkt; na ``execve`` krijgt geen proces meer capabilities.
"""

from __future__ import annotations

import ctypes
import errno
import os
from pathlib import Path

PR_CAPBSET_DROP = 24
PR_SET_NO_NEW_PRIVS = 38
STATUS_FIELDS = ("Uid", "CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb", "NoNewPrivs")
ZERO = "0000000000000000"


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


def last_cap() -> int:
    try:
        return int(Path("/proc/sys/kernel/cap_last_cap").read_text().strip())
    except (OSError, ValueError):
        return 63


def status(pid: str = "self") -> dict[str, str]:
    """Velden uit ``/proc/<pid>/status`` (Uid = de echte uid, eerste kolom)."""
    out: dict[str, str] = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            key, _sep, value = line.partition(":")
            if key in STATUS_FIELDS:
                out[key] = value.split()[0] if value.split() else ""
    except OSError:
        pass
    return out


def drop_bounding_set() -> bool:
    """Leeg de bounding set van dit proces (erft over op kinderen). ``True`` als ``CapBnd`` daarna 0 is."""
    try:
        libc = _libc()
    except OSError:
        return False
    for cap in range(last_cap() + 1):
        if int(libc.prctl(PR_CAPBSET_DROP, cap, 0, 0, 0)) != 0 and ctypes.get_errno() != errno.EINVAL:
            return False  # EINVAL: deze capability bestaat niet in deze kernel
    return status().get("CapBnd") == ZERO


def set_no_new_privs() -> bool:
    try:
        return int(_libc().prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) == 0
    except (OSError, AttributeError):
        return False


def switch_to(uid: int, gid: int) -> None:
    """Volledig naar ``uid:gid`` (geen aanvullende groepen, geen ambient capabilities)."""
    if os.getuid() == 0:
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)


def healthcheck_switch(uid: int = 568, gid: int = 568) -> bool:
    """Eerste handeling van een healthcheck of ``docker exec``-proces (§2.2): bij root eerst de bounding set legen,
    dan naar 568 en no_new_privs. ``False`` = de wissel mislukte (de healthcheck is dan rood)."""
    try:
        if os.getuid() == 0:
            if not drop_bounding_set():
                return False
            switch_to(uid, gid)
        return set_no_new_privs() and os.getuid() != 0
    except OSError:
        return False


def controle_regels() -> list[str]:
    """Controlevlag van de healthcheck: ``Uid``, ``CapEff``, ``CapPrm``, ``CapAmb``, ``CapBnd`` en ``NoNewPrivs``."""
    st = status()
    return [f"{k}\t{st.get(k, '?')}" for k in ("Uid", "CapEff", "CapPrm", "CapAmb", "CapBnd", "NoNewPrivs")]
