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

from asm_policy.etag import _repo

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


def _opslagregels(waarde: Any, diepte: int = 0, *, opslag: bool = False) -> list[Mapping[str, Any]]:
    """Elke opslagregel: een bekende soort, een ``*_config`` van een bekende soort, een regel met ``mount_path`` of
    elk item onder een sleutel ``storage``. Een regel van een onbekende soort komt zo ook mee (en is dan onbekend)."""
    if diepte > 16:
        return [{"type": "onbekend"}]
    if isinstance(waarde, Mapping):
        if (
            opslag
            or waarde.get("type") in OPSLAGSOORTEN
            or "host_path_config" in waarde
            or "ix_volume_config" in waarde
            or "mount_path" in waarde
        ):
            return [waarde]
        return [r for k, v in waarde.items() for r in _opslagregels(v, diepte + 1, opslag=k == "storage")]
    if isinstance(waarde, list):
        return [r for v in waarde for r in _opslagregels(v, diepte + 1, opslag=opslag)]
    if opslag:
        return [{"type": "onbekend"}]
    return []


def onder_pad(pad: str, mounts: Iterable[tuple[str, str]]) -> list[str] | None:
    """De dataset van een hostpad plus elke dataset die daaronder is aangekoppeld (die is in de bind-mount zichtbaar en
    heeft een eigen snapshot nodig), of ``None`` als het pad in geen enkel koppelpunt ligt."""
    mounts = list(mounts)
    ds = dataset_voor_pad(pad, mounts)
    if ds is None:
        return None
    basis = posixpath.normpath(pad).rstrip("/") + "/"
    return [ds, *sorted({n for mp, n in mounts if posixpath.normpath(mp).startswith(basis) and n != ds})]


def _draait(werklast: Any) -> bool:
    """Positief bewijs uit de werklast: de app draait en TrueNAS geeft de volledige lijst koppelingen."""
    if not isinstance(werklast, Mapping) or not isinstance(werklast.get("volumes"), list):
        return False
    containers = werklast.get("containers")
    return isinstance(containers, int) and not isinstance(containers, bool) and containers > 0


def app_datasets(config: Any, boom: Any, app: str, werklast: Any = None, *, ook: Any = None) -> list[str] | None:
    """De datasets met persistente data van deze app, of ``None`` als dat niet volledig vast te stellen is (onbekende
    opslagsoort, pad buiten elk koppelpunt): dan geen dekking.

    Bronnen samen: de opslag in ``app.config``, ``ook`` (de waarden die een terugzetting gaat schrijven), de koppelingen
    van de draaiende werklast (``active_workloads``) en de datasetboom: elke dataset die onder een gekoppeld pad hangt,
    telt mee. Een hostpad of koppeling met alleen-lezen kan de app niet wijzigen; ``tmpfs`` bewaart niets. De ix-volumes
    en de map ``ix-apps/app_mounts/<app>`` tellen wel mee. Een lege uitkomst telt alleen als de werklast positief
    bewijst dat er geen persistente opslag is (de app draait zonder schrijfbare koppeling); anders ``None``."""
    mounts = mounts_uit_boom(boom)
    koppelpunt = {n: mp for mp, n in mounts}
    eigen = re.compile(rf"^[^/]+/\.?ix-apps/app_mounts/{re.escape(app)}(/.*)?$")
    nodig: list[str] = []

    def neem(pad: str) -> bool:
        lijst = onder_pad(pad, mounts)
        nodig.extend(d for d in lijst or [] if d not in nodig)
        return lijst is not None

    for naam, mp in koppelpunt.items():
        if eigen.match(naam) and naam.count("/") == 3:
            neem(mp)
    for regel in [*_opslagregels(config), *_opslagregels(ook)]:
        soort = regel.get("type")
        if soort in GEEN_DATA:
            continue
        if soort == "host_path" or (soort is None and "host_path_config" in regel):
            if regel.get("read_only") is True:
                continue
            cfg = regel.get("host_path_config")
            if not (isinstance(cfg, Mapping) and neem(str(cfg.get("path") or ""))):
                return None
        elif soort == "ix_volume" or (soort is None and "ix_volume_config" in regel):
            cfg = regel.get("ix_volume_config")
            vol = cfg.get("dataset_name") if isinstance(cfg, Mapping) else None
            ds = next((n for n in koppelpunt if eigen.match(n) and n.endswith(f"/{vol}")), None) if vol else None
            if ds is None or not neem(koppelpunt[ds]):
                return None
        else:  # anonymous, cifs, nfs, smb, volume of onbekend: daar maakt een ZFS-snapshot geen herstelpunt van
            return None
    volumes = werklast.get("volumes") if isinstance(werklast, Mapping) else None
    if not isinstance(volumes, list):
        return None  # de volumelijst van de werklast is niet gelezen: onbekend, ook als de configuratie iets aanwijst
    for v in volumes:
        if not isinstance(v, Mapping):
            return None
        if v.get("type") == "tmpfs" or "ro" in str(v.get("mode") or "").split(","):
            continue
        if v.get("type") != "bind" or not neem(str(v.get("source") or "")):
            return None
    if not nodig and not _draait(werklast):
        return None  # leeg zonder positief bewijs is onbekend, nooit "gedekt"
    return nodig


def image_identiteit(ref: str, digest: Any = None) -> set[str]:
    """De ene vorm voor een image: ``repo:versie`` (de tag zonder digest) en ``repo@sha256:…``, ongeacht of de digest in
    de tag of in een apart veld staat (R-HARDE-EIS-5). Zonder tag en digest: leeg (onbekend)."""
    naam, _s, in_ref = str(ref).partition("@")
    repo = _repo(naam)
    tag = naam[len(repo) + 1 :] if naam != repo else ""
    d = in_ref or (str(digest) if digest else "")
    return ({f"{repo}:{tag}"} if tag else set()) | ({f"{repo}@{d}"} if d else set())


def normaliseer(ids: Iterable[Any]) -> set[str]:
    """Vastgelegde identiteiten (ook in een oudere schrijfwijze) in de vorm van :func:`image_identiteit`."""
    uit: set[str] = set()
    for i in ids:
        s = str(i)
        uit |= {s} if s.startswith("versie:") else image_identiteit(s)
    return uit


def identiteiten(staat: Mapping[str, Any]) -> set[str]:
    """Wat er volgens een ``app_state`` draait: images, digests en de catalogusversie (``versie:<v>``). Voor EX15: een
    terugkeer naar een van deze is een terugkeer naar die versie."""
    uit = normaliseer([*(staat.get("images") or []), *(staat.get("digests") or [])])
    if staat.get("versie"):
        uit.add(f"versie:{staat['versie']}")
    return uit


def doel_identiteiten(image: Mapping[str, Any] | None, catalogusversie: Any = None) -> set[str]:
    """Waar een bijwerking of terugzetting naartoe gaat, in dezelfde vorm als :func:`identiteiten` (een digest uit
    ``expected_image``, in de tag of apart, telt altijd mee)."""
    if isinstance(image, Mapping) and image.get("repository"):
        return image_identiteit(f"{image['repository']}:{image.get('tag') or ''}", image.get("digest"))
    return {f"versie:{catalogusversie}"} if catalogusversie else set()


def _soorten(ids: Iterable[str]) -> set[str]:
    return {"versie" if i.startswith("versie:") else "image" for i in ids}


def terug_voor_migratie(historie: Iterable[tuple[bool, set[str]]], doel: set[str]) -> bool | None:
    """EX15 op elke imagewijziging: ``historie`` is per eigen bijwerking of terugzetting, op volgorde, ``(migratie,
    identiteiten ervóór)``. ``True``: het doel draaide vóór de laatste gemelde migratie (databaseherstel vereist).
    ``None``: een wijziging tot en met die migratie heeft geen identiteit van de soort van het doel (onbekend)."""
    rijen = [(m, normaliseer(v)) for m, v in historie]
    laatste = max((i for i, (mig, _v) in enumerate(rijen) if mig), default=None)
    doel = normaliseer(doel)
    if laatste is None or not doel:
        return False
    if doel & set().union(*(v for _m, v in rijen[: laatste + 1])):
        return True
    if any(not (_soorten(v) & _soorten(doel)) for _m, v in rijen[: laatste + 1]):
        return None
    return False
