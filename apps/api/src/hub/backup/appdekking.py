"""Back-upmeldingen van de eigenaren. Alleen vaste velden en redenen verlaten de adapter."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, field_validator

from hub.adapters import basis, mediaguard_lezen, my_house
from hub.timeutil import binnen_venster, iso

MG, MSO, HUIS, EMBY = "mediaguard", "media-source-optimizer", "my_house", "emby_exportarchief"
NAMEN = {MG: "MediaGuard-voortgang", MSO: "Media Source Optimizer", HUIS: "my_house", EMBY: "Emby-exportarchief"}
BACKUP_UREN = {MG: 48, HUIS: my_house.BACKUP_WARN_H}
FORKS = {"sonarr-series", "sonarr-anime", "radarr-films", "radarr-animefilms"}
REDENEN = {
    "geen_meting": "Geen bevestigde meting van de adapter.",
    "onbereikbaar": "De adapter is onbereikbaar of het leesrecht is niet bevestigd.",
    "ongeldig": "De bronmeting is onvolledig of tegenstrijdig.",
    "verlopen": "De bronmeting is verlopen.",
    "oud": "De back-up is ouder dan de toegestane leeftijd.",
    "fork": "Een forkback-up ontbreekt of is niet geverifieerd.",
    "onderdeel": "Een onderdeel van het herstelrapport is niet geverifieerd.",
    "huis": "De back-upcontrole van my_house meldt een afwijking.",
    "mso": "Geen toegestane onderhoudsroute met leesrecht.",
    "ontbreekt": "nog niet gemaakt (overname, P4-0)",
    "kopie": "Geen afzonderlijke back-upkopie met overeenkomende controlesommen.",
    "rpo": "De maximale archiefleeftijd is nog niet vastgelegd in D16.",
    "volgorde": "Geen nieuwe bronmeting sinds de laatste storing.",
}

_STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z")


def tijd(waarde: object) -> datetime:
    if not isinstance(waarde, str) or not _STAMP.fullmatch(waarde):
        raise ValueError("Ongeldige UTC-meettijd.")
    return datetime.fromisoformat(waarde)


def _opslagtijd(waarde: object) -> datetime:
    if isinstance(waarde, datetime) and waarde.tzinfo == UTC:
        return waarde
    return tijd(waarde)


# Bewaar microseconden. Afronding vóór de vergelijking kan een oudere bronlezing na een storing laten vallen.
Tijd = Annotated[
    datetime,
    BeforeValidator(_opslagtijd),
    PlainSerializer(lambda d: d.isoformat().replace("+00:00", "Z"), return_type=str),
]
Status = Literal["gedekt", "degraded", "unknown"]


class Meting(BaseModel):
    """De enige meetvelden die in de Hub worden bewaard. De geldigheid wordt opnieuw getoetst bij gebruik."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    status: Status
    reden: str | None = None
    observed_at: Tijd
    gemaakt_op: Tijd | None = None  # oudste vereiste kopie
    max_age_s: Annotated[int, Field(ge=0, le=basis.MAX_AGE_S)] = basis.MAX_AGE_S
    aanwezig: bool | None = None
    in_backup: bool | None = None

    @field_validator("reden")
    @classmethod
    def vaste_reden(cls, v: str | None) -> str | None:
        if v is not None and v not in REDENEN:
            raise ValueError("Onbekende reden.")
        return v


@dataclass
class AppBronnen:
    metingen: dict[str, Meting] = field(default_factory=dict)
    afwezig: set[str] = field(default_factory=set)  # alleen uit een volledige, verse inventaris
    rpo_uren: dict[str, float] = field(default_factory=dict)
    runtime_ids: dict[str, str] = field(default_factory=dict)
    binding_tot: dict[str, datetime] = field(default_factory=dict)

    def item(self, app: str, now: datetime) -> dict[str, Any]:
        m = self.metingen.get(app)
        status: Status = "unknown"
        reden = "geen_meting"
        age = None
        geldig_tot = None
        if app == MSO:
            m, reden = None, "mso"
        elif m is None:
            reden = "ontbreekt" if app == EMBY else "geen_meting"
        elif (
            m.observed_at > now
            or not binnen_venster(m.observed_at, now, m.max_age_s)
            or self.binding_tot.get(app, now) < now
        ):
            reden = "verlopen"
        else:
            geldig_tot = m.observed_at + timedelta(seconds=m.max_age_s)
            geldig_tot = min(geldig_tot, self.binding_tot.get(app, geldig_tot))
            status, reden = m.status, m.reden or ""
            if m.gemaakt_op is not None and m.gemaakt_op <= m.observed_at:
                age = (now - m.gemaakt_op).total_seconds() / 3600
            if status == "gedekt":
                uren = self.rpo_uren.get(app, math.inf)
                if app == EMBY:
                    uren = min(uren, self.rpo_uren.get("emby", math.inf))
                grens = min(uren, BACKUP_UREN.get(app, math.inf))
                if age is None or reden or (app == EMBY and not (m.aanwezig is True and m.in_backup is True)):
                    status, reden = "unknown", "ongeldig"
                elif not math.isfinite(grens) or grens <= 0:
                    status, reden = "unknown", "rpo"
                elif not binnen_venster(m.gemaakt_op, now, grens * 3600):
                    status, reden = "degraded", "oud"
                elif m.gemaakt_op is not None and geldig_tot is not None:
                    geldig_tot = min(geldig_tot, m.gemaakt_op + timedelta(hours=grens))
        return {
            "naam": NAMEN[app],
            "status": status,
            "reden": REDENEN.get(reden),
            "observed_at": iso(m.observed_at) if m else None,
            "geldig_tot": iso(geldig_tot),
            "gemaakt_op": iso(m.gemaakt_op) if m else None,
            "leeftijd_uren": round(age, 2) if age is not None else None,
            "aanwezig": m.aanwezig if m and reden != "verlopen" else None,
            "plaats": "backups/emby-export.json"
            if app == EMBY and m and m.in_backup is True and reden != "verlopen"
            else None,
            "vereist": app in (MG, EMBY) or app not in self.afwezig,
        }


class _Bronmodel(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")


class _Deel(_Bronmodel):
    status: Literal["healthy", "degraded"]
    verified: bool
    created_at: str | None
    age_seconds: Annotated[int, Field(ge=0)] | None
    reason_code: str | None


Som = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Versies = Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]


class _Kern(_Deel):
    sha256: Som | None
    schema_versions: Versies | None


class _Kopie(_Bronmodel):
    sha256: Som
    schema_versions: Versies


class _Encoder(_Deel):
    databases: list[_Kopie]


class _Bundel(_Deel):
    enabled: bool
    key_match: bool | None
    fingerprint: Annotated[str, Field(pattern=r"^[a-f0-9]{16}$")] | None


class _Extern(_Deel):
    target_kind: Literal["off", "path", "webdav", "s3", "email"] | None
    sha256: Som | None


class _Fork(_Deel):
    instance_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{1,47}$")]
    name: Annotated[str, Field(pattern=r"(?i)^(sonarr|radarr|nzbdrone)_backup_v?[0-9][.0-9_]{0,55}\.zip$")] | None


class _Rollback(_Bronmodel):
    owner: Literal["mediaguard"]
    pre_update_restore_mode: Literal["bij-stoppen", "handmatig", "wacht op handmatige keuze"]
    staged: bool | None


class _Rapport(_Bronmodel):
    id: Literal["backups"]
    observed_at: str
    status: Literal["healthy", "degraded"]
    core: _Kern
    encoder: _Encoder
    bundle: _Bundel
    offsite: _Extern
    forks: list[_Fork]
    rollback: _Rollback


def herstelrapport(body: dict[str, Any], now: datetime, max_age_s: int) -> Meting:
    """Een bronpagina bevat precies één rapport over de kern, encoder, bundel, externe kopie en alle forks."""
    onbekend = Meting(status="unknown", reden="ongeldig", observed_at=now)
    try:
        pagina = tijd(body.get("observed_at"))
        cijfer, items = mediaguard_lezen.pagina("backups", body, now, max_age_s)
        snapshot = body.get("snapshot_id")
        if (
            cijfer.status != "gemeten"
            or cijfer.waarde != 1
            or len(items) != 1
            or not isinstance(snapshot, str)
            or not re.fullmatch(r"[a-f0-9]{64}", snapshot)
        ):
            return onbekend
        rapport = _Rapport.model_validate(items[0])
        gemeten = tijd(rapport.observed_at)
        if gemeten != pagina or gemeten > now or not binnen_venster(gemeten, now, max_age_s):
            return onbekend
        ids = [fork.instance_id for fork in rapport.forks]
        if len(set(ids)) != len(ids) or "onbekend" in ids:
            return onbekend
        tijden = []
        reden = None
        for deel in (rapport.core, rapport.encoder, rapport.bundle, rapport.offsite, *rapport.forks):
            if deel.created_at is not None or deel.age_seconds is not None:
                gemaakt = tijd(deel.created_at)
                if gemaakt > gemeten or deel.age_seconds != int((gemeten - gemaakt).total_seconds()):
                    return onbekend
                tijden.append(gemaakt)
            elif deel.status == "healthy" and deel.verified:
                return onbekend
            if deel.status != "healthy" or deel.verified is not True or deel.reason_code is not None:
                reden = "fork" if isinstance(deel, _Fork) else reden or "onderdeel"
        if tijden and not binnen_venster(min(tijden), now, BACKUP_UREN[MG] * 3600) and reden != "fork":
            reden = "oud"
    except ValueError:
        return onbekend
    if not FORKS.issubset(ids) or any(not f.name for f in rapport.forks):
        reden = "fork"
    elif not (
        rapport.core.sha256
        and rapport.core.schema_versions
        and rapport.encoder.databases
        and rapport.bundle.enabled
        and rapport.bundle.key_match is True
        and rapport.bundle.fingerprint
        and rapport.offsite.target_kind in ("path", "webdav", "s3")
        and rapport.offsite.sha256
        and rapport.rollback.staged is not None
        and rapport.rollback.pre_update_restore_mode != "wacht op handmatige keuze"
        and rapport.status == "healthy"
    ):
        reden = reden or "onderdeel"
    return Meting(
        status="degraded" if reden else "gedekt",
        reden=reden,
        observed_at=gemeten,
        gemaakt_op=min(tijden, default=None),
        max_age_s=max_age_s,
    )


def huisrapport(body: object, gevraagd: datetime) -> Meting:
    onbekend = Meting(status="unknown", reden="ongeldig", observed_at=gevraagd)
    if not isinstance(body, dict) or not isinstance(body.get("checks"), list):
        return onbekend
    checks = body["checks"]
    if not all(isinstance(c, dict) and isinstance(c.get("key"), str) for c in checks):
        return onbekend
    backup = [c for c in checks if c["key"] == "backup"]
    if len(backup) != 1:
        return onbekend
    r = backup[0]
    state, age, fouten = r.get("state"), r.get("age_h"), r.get("auto_failures")
    if state not in ("ok", "warn", "error") or type(fouten) is not int or fouten < 0:
        return onbekend
    if state != "ok" or fouten > 0:
        return Meting(status="degraded", reden="huis", observed_at=gevraagd)
    if (
        type(age) not in (int, float)
        or not 0 <= age < math.inf
        or "auto_last_error" not in r
        or r["auto_last_error"] is not None
    ):
        return onbekend
    if age >= my_house.BACKUP_WARN_H - 0.05:
        return Meting(status="degraded", reden="oud", observed_at=gevraagd)
    # De bron rondt op tienden. Neem de oudste mogelijke back-up zodat de gate niet te lang openblijft.
    return Meting(status="gedekt", observed_at=gevraagd, gemaakt_op=gevraagd - timedelta(hours=age + 0.05))
