"""Controle van een reeds afgeleverd Emby-exportarchief en zijn afzonderlijke back-upkopie (contract §2.3.8)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import datetime
from functools import cache
from importlib import resources
from io import BytesIO
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


class _InventarisBron(_Archiefdeel):
    server_id: Annotated[str, Field(min_length=1)]


class _Bron(_InventarisBron):
    product: Literal["Emby Server"]


class _Tool(_Archiefdeel):
    naam: Literal["jelly-leon-emby-overname"]
    versie: Annotated[str, Field(min_length=1)]


class _Inhoud(_Archiefdeel):
    tool: _Tool
    bron: _Bron
    bibliotheken: list[dict[str, Any]]
    classificaties: list[dict[str, Any]]
    plugins: list[dict[str, Any]]
    items: dict[str, dict[str, Any]]
    gebruikers: Annotated[list[_Gebruiker], Field(min_length=1)]


def _export(data: bytes) -> tuple[datetime, _Inhoud, str]:
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
    return gemaakt, archief, inhoud


class _Naam(_Archiefdeel):
    naam: Annotated[str, Field(min_length=1)]


class _Inventaris(_Archiefdeel):
    schema_naam: Literal["jelly-leon/emby-inventaris/1"] = Field(alias="schema")
    emby: _InventarisBron
    gebruikers: Annotated[list[_Naam], Field(min_length=1)]


class _Exportbewijs(_Archiefdeel):
    sha256: str
    inhoud_sha256: str
    leeslog_sha256: str
    gebruikers: int
    items_met_kijkgegevens: int


_GLOBAL_GET = {"/System/Info", "/Users", "/Library/VirtualFolders/Query", "/Localization/ParentalRatings", "/Plugins"}
_FAVORIET_GET = {"/Persons", "/Artists", "/Genres", "/Studios"}
_VIDEO = {"Movie", "Episode", "Video", "MusicVideo", "AudioBook", "Trailer"}


def _gelezen(data: bytes, archief: _Inhoud, gemaakt: datetime) -> bool:
    # cmd_export leest eerst de gebruikerslijst en daarna de items, favorieten en PlaybackInfo per gebruiker.
    # De bron logt alleen querysleutels. De paginalezing opent daarom het bereik voor één gebruiker.
    vereist: set[tuple[str | None, str]] = {(None, route) for route in _GLOBAL_GET}
    for g in archief.gebruikers:
        vereist.add((None, f"/Users/{g.id}"))
        vereist.add((g.id, f"/Users/{g.id}/Items"))
        vereist.update((g.id, route) for route in _FAVORIET_GET)
        opties = [g.configuratie.get(k) for k in ("RememberAudioSelections", "RememberSubtitleSelections")]
        if any(optie is not None and type(optie) is not bool for optie in opties):
            return False
        videos = {i for i in g.kijkgegevens if archief.items[i]["type"] in _VIDEO}
        if videos and not any(opties) and None in opties:
            return False
        sporen = videos if any(opties) else set()
        if sporen != g.spoorkeuzes.keys():
            return False
        # Ook de expliciete uitkomst 'geen standaardspoor' heeft twee velden in de bron.
        if any(not {"bestand", "audio", "ondertitel"}.issubset(keuze) for keuze in g.spoorkeuzes.values()):
            return False
        vereist.update((g.id, f"/Items/{i}/PlaybackInfo") for i in sporen)

    paginas = {f"/Users/{g.id}/Items": g.id for g in archief.gebruikers}
    gebruiker = None
    for regel in BytesIO(data):
        melding = json.loads(regel)
        if not isinstance(melding, dict) or melding.get("doel") != "Emby" or melding.get("methode") != "GET":
            return False
        if tijd(melding.get("tijd")) > gemaakt:
            return False
        status, pad, query = melding.get("status"), melding.get("pad"), melding.get("query_sleutels")
        if (
            type(status) is not int
            or not 200 <= status < 300
            or not isinstance(pad, str)
            or not isinstance(query, list)
        ):
            return False
        if pad in paginas and {"StartIndex", "EnableUserData"}.issubset(query):
            gebruiker = paginas[pad]
            vereist.discard((gebruiker, pad))
        elif "UserId" in query and (pad in _FAVORIET_GET or pad.endswith("/PlaybackInfo")):
            vereist.discard((gebruiker, pad))
        elif not query:
            vereist.discard((None, pad))
    return not vereist


def _bevestigd(mapje: Path, pin: str | None, archief: _Inhoud, digest: str, inhoud: str, gemaakt: datetime) -> bool:
    # De inventaris en de uitdraai van cmd_export komen langs de bevestigde lokale overnamebron.
    # De Hub schrijft hier nooit en neemt geen identiteit over uit een aangeboden archief.
    if not pin:
        return False
    inventaris, _ = _lees(mapje, "inventaris.json", MAX_BYTES)
    if hashlib.sha256(inventaris).hexdigest() != pin:
        return False
    bron = _Inventaris.model_validate_json(inventaris)
    namen = {g.naam for g in archief.gebruikers}
    bewijs = _Exportbewijs.model_validate_json(_lees(mapje, "exportbewijs.json", 8192)[0])
    if not (
        bron.emby.server_id == archief.bron.server_id
        and len(namen) == len(archief.gebruikers) == len(bron.gebruikers) == bewijs.gebruikers
        and namen == {g.naam for g in bron.gebruikers}
        and bewijs.sha256 == digest
        and bewijs.inhoud_sha256 == inhoud
        and bewijs.items_met_kijkgegevens == sum(len(g.kijkgegevens) for g in archief.gebruikers)
    ):
        return False
    leeslog, _ = _lees(mapje, "emby-export.log.jsonl", MAX_BYTES)
    return hashlib.sha256(leeslog).hexdigest() == bewijs.leeslog_sha256 and _gelezen(leeslog, archief, gemaakt)


def lees_archief(bron: Path, backup: Path, now: datetime, bronreferentie: str | None = None) -> Meting:
    """Controleert het archief, het afzonderlijk aangeleverde bronbewijs en de back-upkopie."""
    try:
        data, identiteit = _lees(bron, BESTAND, MAX_BYTES)
    except FileNotFoundError:
        return Meting(status="unknown", reden="ontbreekt", observed_at=now, aanwezig=False)
    except (OSError, ValueError):
        return Meting(status="unknown", reden="ongeldig", observed_at=now)
    try:
        digest = _controlesom(bron, data)
        gemaakt, archief, inhoud = _export(data)
        if gemaakt > now:
            raise ValueError("Exporttijd ligt in de toekomst.")
    except (OSError, ValueError, TypeError, RecursionError):
        return Meting(status="unknown", reden="ongeldig", observed_at=now, aanwezig=True)
    del data
    try:
        bevestigd = _bevestigd(bron.parent / "overnamebron", bronreferentie, archief, digest, inhoud, gemaakt)
    except (OSError, ValueError, TypeError, RecursionError):
        bevestigd = False
    if not bevestigd:
        return Meting(status="unknown", reden="leesbewijs", observed_at=now, aanwezig=True)
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
