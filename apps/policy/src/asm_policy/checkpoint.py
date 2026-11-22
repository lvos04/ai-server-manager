"""Geverifieerd app-checkpoint vóór ``app.update``/``app.rollback`` (contract 1.3 §8 "Back-upbevestiging"; ADR-0032
besluit 8 en 9 rij F; S-P2-050f).

Een checkpoint is een ZFS-snapshot die de executor zelf maakte met de bestaande actie ``zfs.snapshot.create`` en
daarna in zijn eigen journaal vastlegde (id = ``request_id`` van die snapshotactie). Hub en executor gebruiken
dezelfde regels hieronder: hoe oud het mag zijn en welke dataset een andere dekt. De executor controleert vlak vóór
de schrijfaanroep bovendien zelf of de snapshot nog bestaat met dezelfde ``createtxg`` en of hij alle opslag van de
app dekt. Een id dat een gebruiker, de AI of de Hub noemt, is op zichzelf nooit bewijs.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Iterable, Mapping
from typing import Any

# Een pre-update-checkpoint is vers: hooguit een uur oud (strenger dan elk RPO van een uur of meer).
# shortcut: één vaste grens voor alle apps; een kortere RPO uit het manifest (§9) telt nog niet mee, bij 050g/090.
CHECKPOINT_MAX_SECONDEN = 3600
# Opslag die geen persistente appdata bevat en dus geen dekking nodig heeft.
GEEN_DATA = frozenset({"tmpfs"})
OPSLAGSOORTEN = frozenset({"host_path", "ix_volume", "tmpfs", "anonymous", "cifs", "nfs", "smb", "volume"})


def dekt(checkpoint_dataset: str, recursief: bool, dataset: str) -> bool:
    """Of een snapshot van ``checkpoint_dataset`` de data van ``dataset`` bevat (zelfde dataset, of een ouder met een
    recursieve snapshot)."""
    if dataset == checkpoint_dataset:
        return True
    return recursief and dataset.startswith(checkpoint_dataset + "/")


def dataset_voor_pad(pad: str, mounts: Iterable[tuple[str, str]]) -> str | None:
    """De dataset waarin een hostpad ligt: het langste passende koppelpunt. Een relatief pad of een pad buiten elk
    koppelpunt geeft ``None`` (onbekend)."""
    if not isinstance(pad, str) or not pad.startswith("/"):
        return None
    pad = posixpath.normpath(pad)
    beste: tuple[int, str] | None = None
    for mountpoint, naam in mounts:
        mp = posixpath.normpath(mountpoint)
        if (pad == mp or pad.startswith(mp.rstrip("/") + "/")) and (beste is None or len(mp) > beste[0]):
            beste = (len(mp), naam)
    return beste[1] if beste else None


def mounts_uit_boom(boom: Any) -> list[tuple[str, str]]:
    """``(koppelpunt, dataset)`` uit de boom van ``pool.dataset.query``."""
    uit: list[tuple[str, str]] = []

    def loop(nodes: Any) -> None:
        for n in nodes if isinstance(nodes, list) else []:
            if not isinstance(n, dict):
                continue
            naam, mp = n.get("name") or n.get("id"), n.get("mountpoint")
            if isinstance(naam, str) and isinstance(mp, str) and mp.startswith("/"):
                uit.append((mp, naam))
            loop(n.get("children"))

    loop(boom)
    return uit


def _opslagregels(waarde: Any, diepte: int = 0) -> list[Mapping[str, Any]]:
    if diepte > 16:
        return [{"type": "onbekend"}]
    if isinstance(waarde, Mapping):
        if waarde.get("type") in OPSLAGSOORTEN or "host_path_config" in waarde or "ix_volume_config" in waarde:
            return [waarde]
        return [r for v in waarde.values() for r in _opslagregels(v, diepte + 1)]
    if isinstance(waarde, list):
        return [r for v in waarde for r in _opslagregels(v, diepte + 1)]
    return []


def app_datasets(config: Any, boom: Any, app: str) -> list[str] | None:
    """De datasets met persistente data van deze app volgens zijn eigen ``app.config`` en de datasetboom, of ``None``
    als dat niet volledig vast te stellen is (onbekende opslagsoort, pad buiten elk koppelpunt): dan geen dekking.

    Een hostpad met ``read_only: true`` kan de app niet wijzigen en telt niet mee; ``tmpfs`` bewaart niets. De
    ix-volumes en de map ``ix-apps/app_mounts/<app>`` tellen wel mee."""
    mounts = mounts_uit_boom(boom)
    namen = [n for _mp, n in mounts]
    eigen = re.compile(rf"^[^/]+/\.?ix-apps/app_mounts/{re.escape(app)}(/.*)?$")
    nodig: list[str] = [n for n in namen if eigen.match(n) and n.count("/") == 3]
    for regel in _opslagregels(config):
        soort = regel.get("type")
        if soort in GEEN_DATA:
            continue
        if soort == "host_path" or (soort is None and "host_path_config" in regel):
            if regel.get("read_only") is True:
                continue
            cfg = regel.get("host_path_config")
            ds = dataset_voor_pad(str(cfg.get("path") or ""), mounts) if isinstance(cfg, Mapping) else None
        elif soort == "ix_volume" or (soort is None and "ix_volume_config" in regel):
            cfg = regel.get("ix_volume_config")
            naam = cfg.get("dataset_name") if isinstance(cfg, Mapping) else None
            ds = next((n for n in namen if eigen.match(n) and n.endswith(f"/{naam}")), None) if naam else None
        else:  # anonymous, cifs, nfs, smb, volume of onbekend: daar maakt een ZFS-snapshot geen herstelpunt van
            return None
        if ds is None:
            return None
        if ds not in nodig:
            nodig.append(ds)
    return nodig
