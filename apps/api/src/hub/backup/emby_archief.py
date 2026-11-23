"""Controle van een reeds afgeleverd Emby-exportarchief en zijn afzonderlijke back-upkopie (contract §2.3.8)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Annotated, Any, Literal

from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, Field

from hub.backup.appdekking import Meting, tijd

BESTAND = "emby-export.json"
SCHEMA = "jelly-leon/emby-kijkgegevens-export/1"
MAX_BYTES = 32 * 1024 * 1024


@cache
def _archiefschema() -> Draft202012Validator:
    bestand = resources.files("hub.backup").joinpath("emby-kijkgegevens-export.schema.json")
    return Draft202012Validator(json.loads(bestand.read_text(encoding="utf-8")))


def _lees(mapje: Path, naam: str, grens: int) -> tuple[bytes, tuple[int, int]]:
    map_fd = os.open(mapje, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(naam, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=map_fd)
        with os.fdopen(fd, "rb") as bestand:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= grens:
                raise ValueError("Ongeldig archiefbestand.")
            data = bestand.read(grens + 1)
            if len(data) != info.st_size:
                raise ValueError("Archiefbestand gewijzigd.")
            return data, (info.st_dev, info.st_ino)
    finally:
        os.close(map_fd)


def _controlesom(mapje: Path, data: bytes) -> str:
    digest = hashlib.sha256(data).hexdigest()
    sidecar, _ = _lees(mapje, BESTAND + ".sha256", 128)
    if sidecar != f"{digest}  {BESTAND}\n".encode():
        raise ValueError("De bestandscontrole wijkt af.")
    return digest


class _Archiefdeel(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore", allow_inf_nan=False)


class _Kijkgegevens(_Archiefdeel):
    gezien: bool
    aantal: Annotated[int, Field(ge=0)]
    laatst: str | None
    positie: Annotated[int, Field(ge=0)]
    favoriet: bool
    beoordeling: float | None
    vind_ik_leuk: bool | None


class _Gebruiker(_Archiefdeel):
    id: Annotated[str, Field(min_length=1)]
    naam: Annotated[str, Field(min_length=1)]
    beleid: dict[str, Any]
    configuratie: dict[str, Any]
    heeft_wachtwoord: bool
    zichtbaar: list[str]
    kijkgegevens: dict[str, _Kijkgegevens]
    spoorkeuzes: dict[str, dict[str, Any]]
    spoorkeuzes_niet_gelezen: list[str]
    benoemde_favorieten: list[str]


class _Bron(_Archiefdeel):
    product: Literal["Emby Server"]
    server_id: Annotated[str, Field(min_length=1)]


class _Inhoud(_Archiefdeel):
    bron: _Bron
    bibliotheken: list[dict[str, Any]]
    classificaties: list[dict[str, Any]]
    plugins: list[dict[str, Any]]
    items: dict[str, dict[str, Any]]
    gebruikers: Annotated[list[_Gebruiker], Field(min_length=1)]


def _exporttijd(data: bytes) -> datetime:
    opname = json.loads(data)
    if not isinstance(opname, dict) or opname.get("schema") != SCHEMA or not _archiefschema().is_valid(opname):
        raise ValueError("Onbekend archiefschema.")
    gemaakt = tijd(opname.pop("gemaakt", None))
    inhoud = opname.pop("inhoud_sha256", None)
    canoniek = json.dumps(opname, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(canoniek.encode("utf-8")).hexdigest() != inhoud:
        raise ValueError("De inhoudscontrole wijkt af.")
    archief = _Inhoud.model_validate(opname)
    if len({g.id for g in archief.gebruikers}) != len(archief.gebruikers):
        raise ValueError("Dubbele gebruiker.")
    if any(not item_id or item["id"] != item_id for item_id, item in archief.items.items()):
        raise ValueError("De item-ID komt niet overeen.")
    for g in archief.gebruikers:
        ids = set(g.zichtbaar) | g.kijkgegevens.keys() | g.spoorkeuzes.keys() | set(g.benoemde_favorieten)
        if not ids.issubset(archief.items) or g.spoorkeuzes_niet_gelezen:
            raise ValueError("De kijkgegevens of spoorkeuzes zijn onvolledig.")
    return gemaakt


def lees_archief(bron: Path, backup: Path, now: datetime) -> Meting:
    """Leest uitsluitend gewone bestanden op twee vaste plaatsen. Geef alleen meetgegevens terug."""
    try:
        data, identiteit = _lees(bron, BESTAND, MAX_BYTES)
    except FileNotFoundError:
        return Meting(status="unknown", reden="ontbreekt", observed_at=now, aanwezig=False)
    except (OSError, ValueError):
        return Meting(status="unknown", reden="ongeldig", observed_at=now)
    try:
        digest = _controlesom(bron, data)
        gemaakt = _exporttijd(data)
        if gemaakt > now:
            raise ValueError("Exporttijd ligt in de toekomst.")
    except (OSError, ValueError, TypeError, RecursionError):
        return Meting(status="unknown", reden="ongeldig", observed_at=now, aanwezig=True)
    del data
    try:
        kopie, kopie_id = _lees(backup, BESTAND, MAX_BYTES)
        gedekt = kopie_id != identiteit and _controlesom(backup, kopie) == digest
    except (OSError, ValueError):
        gedekt = False
    return Meting(
        status="gedekt" if gedekt else "degraded",
        reden=None if gedekt else "kopie",
        observed_at=now,
        gemaakt_op=gemaakt,
        aanwezig=True,
        in_backup=gedekt,
    )
