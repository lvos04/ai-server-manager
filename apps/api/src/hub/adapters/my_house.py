"""Leeskoppeling met my_house volgens ADR-0034 en de Hub-doelbinding in my_house."""

from __future__ import annotations

import hashlib
import hmac
import math
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from time import monotonic
from typing import Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, BeforeValidator, Field, TypeAdapter, ValidationError, field_validator, model_validator

from hub import outbound
from hub.adapters import basis
from hub.models import AdapterLink
from hub.timeutil import UtcDateTime, age_seconds, utcnow

APP_ID = "my_house"
RENEW_BEFORE = timedelta(days=30)
TOKEN_LIFETIME = timedelta(days=180, minutes=2)
# Grenzen uit de systeemchecks van my_house.
ZIGBEE_MAX_AGE_S = 180
SENSOR_MIN_AGE_S = 300
SENSOR_MAX_AGE_S = 7200
WORKER_OK_S = 120
BACKUP_WARN_H = 36
TOKEN = re.compile(r"shc_[A-Za-z0-9_-]{43}")
CODE = re.compile(r"[A-HJ-NP-Z2-9]{4}-?[A-HJ-NP-Z2-9]{4}", re.IGNORECASE | re.ASCII)
SENSITIVE_LABEL = re.compile(r"shc_|\b[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}\b", re.IGNORECASE)
RAW_CODE = re.compile(r"\b[A-HJ-NP-Z2-9]{8}\b")
INVALID = "antwoord_ongeldig"


class Route(StrEnum):
    HEALTH = "/api/v1/health"
    IDENTITY = "/api/v1/pairing/identity"
    REDEEM = "/api/v1/pairing/redeem"
    REFRESH = "/api/v1/clients/self/refresh"
    SYSTEM = "/api/v1/system/status"
    HOMES = "/api/v1/homes"
    ZONES = "/api/v1/homes/{home_id}/zones"
    LIGHTS = "/api/v1/homes/{home_id}/lights"
    ALERTS = "/api/v1/homes/{home_id}/alerts"
    DEVICES = "/api/v1/homes/{home_id}/devices"
    SETTINGS = "/api/v1/system/settings"


ERROR_REASONS = {
    (400, "invalid_code"): "bron_koppelcode_ongeldig",
    (401, "token_expired"): "bron_token_verlopen",
    (401, "token_revoked"): "bron_token_ingetrokken",
    (401, "auth_required"): "bron_credential_geweigerd",
    (403, "forbidden"): "bron_recht_geweigerd",
    (404, "not_found"): "bron_niet_gevonden",
    (429, "rate_limited"): "bron_te_veel_verzoeken",
    (503, "identity_unavailable"): "bron_identiteit_onbekend",
}


def _uuid(value: Any) -> UUID:
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("Ongeldige identificatie.")
    result = UUID(value)
    if str(result) != value:
        raise ValueError("Ongeldige identificatie.")
    return result


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not 20 <= len(value) <= 35:
        raise ValueError("Ongeldige meettijd.")
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("Tijdzone ontbreekt.")
    return result


def _label(value: Any) -> str | None:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 100
        or not all(char.isalnum() or char in " _-'’()" for char in value)
        or SENSITIVE_LABEL.search(value)
        or RAW_CODE.search(value)
    ):
        return None
    return value


def _timezone(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_]{1,24}(?:/[A-Za-z_+0-9-]{1,32}){0,2}", value):
        return None
    try:
        return ZoneInfo(value).key
    except ZoneInfoNotFoundError:
        return None


Identifier = Annotated[UUID, BeforeValidator(_uuid)]
Timestamp = Annotated[UtcDateTime, BeforeValidator(_timestamp)]
Label = Annotated[str | None, BeforeValidator(_label)]
Timezone = Annotated[str | None, BeforeValidator(_timezone)]
Version = Annotated[str, Field(max_length=48, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][a-zA-Z0-9.-]+)?$")]
type Rows[T] = Annotated[list[T], Field(max_length=200)]


class Liveness(BaseModel):
    status: Literal["ok"]
    version: Version


class Check(BaseModel):
    key: Annotated[
        str,
        Field(
            pattern=r"^(database|worker|worker_loops|disk|backup|time|safe_mode|maintenance|restore|"
            r"integration:[0-9a-f-]{36}(:mqtt|:dongle)?)$"
        ),
    ]
    state: Literal["ok", "warn", "error", "unknown"]

    @model_validator(mode="before")
    @classmethod
    def _known_state(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("state") not in ("ok", "warn", "error"):
            return {**data, "state": "unknown"}
        return data


class System(BaseModel):
    version: Version
    checks: Annotated[list[Check], Field(min_length=1, max_length=200)]


CHECK_STATUS: dict[str, basis.Status] = {"ok": "healthy", "unknown": "unknown", "warn": "degraded", "error": "down"}
SEVERITY = {"healthy": 0, "unknown": 1, "degraded": 2, "down": 3}


class CheckReading(Check):
    """Versheid van de workercheck, vanaf de gekozen meettijd.

    Bron en meettijd                                        | Uitkomst
    ok, hartslag binnen de grens                            | healthy
    error, eigen bevestiging binnen de grens                | down
    error, hartslag na de vorige storingsbevestiging        | down binnen de grens vanaf de huidige verzoekstart
    meettijd voorbij de grens                               | unknown (meting_verouderd)
    meettijd ontbreekt of is ongeldig                       | unknown (meettijd_onbekend)
    idempotente herhaling                                   | dezelfde meettijd en vervalgrens
    """

    observed_at: datetime | None
    max_age_s: int
    # Oudere werkermetingen gebruikten de ontvangsttijd en mogen niet meer als vers tellen.
    worker_observed_at: datetime | None = None
    worker_error_observed_at: datetime | None = None

    def measurement(self, now: datetime) -> basis.Measurement:
        observed_at = self.observed_at
        if self.key == "worker":
            observed_at = self.worker_observed_at
            if self.state == "error" and observed_at is not None:
                observed_at = self.worker_error_observed_at
        if observed_at is not None and observed_at.tzinfo is None:
            observed_at = None
        return basis.fresh_measurement(
            basis.Measurement(status=CHECK_STATUS[self.state], observed_at=observed_at),
            now=now,
            max_age_s=self.max_age_s,
        )

    def project(self, now: datetime) -> Check:
        state = "unknown" if self.measurement(now).reason_code else self.state
        return Check(key=self.key, state=state)


CheckReadings = TypeAdapter(list[CheckReading])


def _integration_time(raw: dict[str, Any], now: datetime) -> datetime | None:
    details = raw.get("details")
    try:
        observed = _timestamp(details.get("checked_at") if isinstance(details, dict) else None)
    except ValueError:
        return None
    return observed if observed <= now else None


def _backup_max_age(age_h: Any) -> int:
    if type(age_h) not in (int, float) or not 0 <= age_h <= BACKUP_WARN_H:
        return 0
    # De bron rondt op tienden van een uur af. De grens kan dus 180 s eerder vallen.
    return max(0, min(basis.MAX_AGE_S, int((BACKUP_WARN_H - age_h) * 3600) - 180))


def _worker_time(age_s: Any, state: str, requested_at: datetime) -> datetime | None:
    if type(age_s) is not int or age_s < 0:
        return None
    if (state == "ok" and age_s >= WORKER_OK_S) or (state == "error" and age_s < WORKER_OK_S):
        return None
    # De bron rondt naar beneden af en meet pas na de start van het verzoek.
    try:
        return requested_at - timedelta(seconds=age_s + 1)
    except OverflowError:
        return None


def _system_readings(
    data: Any, requested_at: datetime, received_at: datetime, *, previous_worker_error_at: datetime | None = None
) -> tuple[System, list[CheckReading]]:
    system = _validate(TypeAdapter(System), data)
    by_key = {raw["key"]: raw for raw in data["checks"]}
    if len(by_key) != len(system.checks):
        raise outbound.OutboundError(INVALID)
    readings = []
    for check in system.checks:
        observed: datetime | None = received_at
        worker_observed = None
        worker_error_observed = None
        max_age = basis.MAX_AGE_S
        if check.key.startswith("integration:"):
            parent = ":".join(check.key.split(":")[:2])
            raw = by_key.get(parent, {})
            observed = _integration_time(raw, received_at)
            if raw.get("provider") == "zigbee" or parent != check.key:
                max_age = ZIGBEE_MAX_AGE_S
        elif check.key in {"time", "restore"}:
            # Deze bestaande checks bevatten geen bruikbare bronmeettijd.
            observed = None
        elif check.key == "worker":
            observed = None
            worker_observed = _worker_time(by_key[check.key].get("age_s"), check.state, requested_at)
            max_age = WORKER_OK_S
            if check.state == "error":
                # De bron beoordeelt de hartslag tijdens het verzoek. De verzoekstart
                # begrenst de versheid bij vertraging. Een hartslag na de vorige
                # bevestiging bewijst dat deze uitval nieuw is.
                worker_error_observed = previous_worker_error_at
                if worker_observed is not None and (
                    previous_worker_error_at is None or worker_observed > previous_worker_error_at
                ):
                    worker_error_observed = requested_at
        elif check.key == "backup" and check.state == "ok" and "age_h" in by_key[check.key]:
            max_age = _backup_max_age(by_key[check.key]["age_h"])
        readings.append(
            CheckReading(
                key=check.key,
                state=check.state,
                observed_at=observed,
                max_age_s=max_age,
                worker_observed_at=worker_observed,
                worker_error_observed_at=worker_error_observed,
            )
        )
    return system, readings


class Home(BaseModel):
    id: Identifier
    name: Label
    timezone: Timezone
    active: bool


class Sensor(BaseModel):
    value: Annotated[float, Field(allow_inf_nan=False)] | None
    unit: Literal["°C", "%"]
    quality: Literal["measured", "estimated", "derived", "missing"]
    at: Timestamp | None
    stale: bool
    max_age_s: Annotated[int, Field(ge=SENSOR_MIN_AGE_S, le=basis.MAX_AGE_S)] = SENSOR_MIN_AGE_S

    def met_meettijd(self, now: datetime, unit: Literal["°C", "%"]) -> Sensor:
        age = (now - self.at).total_seconds() if self.at is not None else -1
        if self.stale or not 0 <= age <= self.max_age_s or self.unit != unit or self.quality == "missing":
            return self.model_copy(update={"value": None, "stale": True, "unit": unit})
        return self


class Zone(BaseModel):
    id: Identifier
    name: Label
    unit_status: Literal["online", "offline", "not_linked"]
    online: bool
    mode: Literal["off", "auto", "cool", "heat", "dry", "fan"]
    temperature: Sensor
    humidity: Sensor
    target_c: float | None = None

    @field_validator("target_c", mode="before")
    @classmethod
    def _target_c(cls, value: Any) -> float | None:
        return float(value) if type(value) in (float, int) and 5 <= value <= 35 else None


class Light(BaseModel):
    id: Identifier
    name: Label
    on: bool
    brightness: Annotated[float, Field(ge=0, le=100)] | None
    reachable: bool | None = None


class Scene(BaseModel):
    id: Identifier
    group_id: Identifier | None
    active: bool


class Lights(BaseModel):
    groups: Rows[Light]
    scenes: Rows[Scene]
    lights: Rows[Light]


class Alert(BaseModel):
    id: Identifier
    severity: Literal["info", "warn", "warning", "error", "critical"]
    created_at: Timestamp | None = None


class Alerts(BaseModel):
    items: Rows[Alert]
    open: int
    begrensd: bool
    observed_at: UtcDateTime | None = None


class Device(BaseModel):
    id: Identifier
    kind: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")]
    online: bool
    last_seen: Timestamp | None
    compatibility: Literal["unknown", "untested", "tested", "limited", "unsupported", "pairable", "discovered"]
    lifecycle: Literal["active", "replaced", "archived"]


class Settings(BaseModel):
    safe_mode: bool
    maintenance: bool


class HouseSettings(Settings):
    link: str | None
    observed_at: UtcDateTime | None = None


class BackupReading(BaseModel):
    age_h: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    observed_at: UtcDateTime


class Overview(BaseModel):
    woning: Home
    zones: Rows[Zone]
    licht: Lights
    meldingen: Alerts
    apparaten: Rows[Device]


class Snapshot(BaseModel):
    observed_at: UtcDateTime
    databaseprobe: Liveness
    systeem: System
    woningen: list[Overview]
    instellingen: HouseSettings
    laatste_backup: BackupReading | None = None


class SnapshotReading(BaseModel):
    snapshot: Snapshot
    checks: list[CheckReading]

    def project(self, now: datetime) -> Snapshot:
        snapshot = self.snapshot.model_copy(deep=True)
        snapshot.systeem.checks = [check.project(now) for check in self.checks]
        for home in snapshot.woningen:
            for zone in home.zones:
                zone.temperature = zone.temperature.met_meettijd(now, "°C")
                zone.humidity = zone.humidity.met_meettijd(now, "%")
        return snapshot


class _Identity(BaseModel):
    server_id: Identifier


class _Client(BaseModel):
    id: Identifier
    role: Literal["viewer"]
    purpose: Literal["hub"]
    revoked: Literal[False]
    expired: Literal[False]
    expires_at: Timestamp


@dataclass(frozen=True)
class Credential:
    __repr__ = object.__repr__
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class Pairing:
    credential: Credential
    client_id: UUID


def user_link(base: str, lan_url: object, remote_url: object) -> str | None:
    for candidate in (lan_url, remote_url):
        if not isinstance(candidate, str):
            continue
        try:
            if basis.validate_base_url(candidate) == base:
                return base
        except outbound.OutboundError:
            continue
    return None


def _validate[T](model: TypeAdapter[T], data: Any, *, reason: str = INVALID) -> T:
    try:
        return model.validate_python(data, strict=True)
    except ValidationError:
        raise outbound.OutboundError(reason) from None


def _error(response_status: int, data: Any) -> str:
    detail = data.get("detail") if isinstance(data, dict) else None
    code = detail.get("code") if isinstance(detail, dict) else None
    fallback = "bron_credential_geweigerd" if response_status in (401, 403) else "onverwachte_statuscode"
    return ERROR_REASONS.get((response_status, code), fallback) if isinstance(code, str) else fallback


def _credential(token: Any, expires_at: datetime, now: datetime, *, old: Credential | None = None) -> Credential:
    if (
        not isinstance(token, str)
        or TOKEN.fullmatch(token) is None
        or not now < expires_at <= now + TOKEN_LIFETIME
        or (old is not None and (token == old.token or expires_at <= old.expires_at))
    ):
        raise outbound.OutboundError(INVALID)
    return Credential(token, expires_at)


class Adapter:
    def __init__(
        self, link: AdapterLink, policy: outbound.OutboundPolicy, *, check_binding: Callable[[], None]
    ) -> None:
        self.link = link
        self.policy = policy
        self.check_binding = check_binding
        self.deadline = monotonic() + 30

    def _request(
        self,
        route: Route,
        *,
        token: str | None = None,
        code: str | None = None,
        home_id: UUID | None = None,
        challenge: dict[str, str] | None = None,
    ) -> Any:
        self.check_binding()
        if self.link.app_id != APP_ID or not self.link.peer_addresses:
            raise outbound.OutboundError("doelbinding")
        base = basis.validate_base_url(self.link.basis_url)
        remaining = (self.deadline - monotonic()) / 2
        if remaining <= 0:
            raise outbound.OutboundError("tijdslimiet")
        policy = replace(
            self.policy,
            allow_loopback=False,
            allowed_peer_addresses=frozenset(self.link.peer_addresses),
            connect_timeout=min(remaining, self.policy.connect_timeout),
            read_timeout=min(remaining, self.policy.read_timeout),
        )
        method = "POST" if route in (Route.REDEEM, Route.REFRESH) else "GET"
        try:
            response = outbound.request(
                base,
                method,
                route.format(home_id=home_id),
                policy=policy,
                headers={"Authorization": f"Bearer {token}"} if token else None,
                json_body={"code": code, "device_name": "Hub"} if route == Route.REDEEM else None,
                query=challenge,
                max_bytes=basis.MAX_RESPONSE_BYTES,
            )
            data = response.json()
        except (OSError, ValueError, RecursionError):
            raise outbound.OutboundError(INVALID) from None
        if response.status != 200:
            raise outbound.OutboundError(_error(response.status, data))
        return data

    def _identity(self, token: str | None = None) -> None:
        challenge = None
        if token is not None:
            if self.link.my_house_client_id is None:
                raise outbound.OutboundError("bron_identiteit_onbekend")
            challenge = {"nonce": secrets.token_urlsafe(24), "client_id": str(self.link.my_house_client_id)}
        if self.link.my_house_server_id is None:
            raise outbound.OutboundError("bron_identiteit_onbekend")
        data = self._request(Route.IDENTITY, challenge=challenge)
        server = _validate(TypeAdapter(_Identity), data).server_id
        if server != self.link.my_house_server_id:
            raise outbound.OutboundError("bron_identiteit_gewijzigd")
        if challenge is not None and token is not None:
            message = f"shc-identity-v1\n{server}\n{challenge['nonce']}".encode()
            key = hashlib.sha256(token.encode()).hexdigest().encode()
            expected = hmac.digest(key, message, "sha256").hex()
            proof = data.get("proof")
            if (
                data.get("proof_alg") != "hmac-sha256-v1"
                or not isinstance(proof, str)
                or not re.fullmatch(r"[0-9a-f]{64}", proof)
                or not hmac.compare_digest(proof, expected)
            ):
                raise outbound.OutboundError("bron_identiteit_onbewezen")

    def pair(self, code: str) -> Pairing:
        if CODE.fullmatch(code) is None:
            raise outbound.OutboundError("bron_koppelcode_ongeldig")
        code = code.upper().replace("-", "")
        code = f"{code[:4]}-{code[4:]}"
        self._identity()
        data = self._request(Route.REDEEM, code=code)
        if not isinstance(data, dict):
            raise outbound.OutboundError(INVALID)
        client = _validate(TypeAdapter(_Client), data.get("client"), reason="bron_recht_ongeldig")
        server = _validate(TypeAdapter(_Identity), data.get("server"))
        if server.server_id != self.link.my_house_server_id:
            raise outbound.OutboundError("bron_identiteit_gewijzigd")
        credential = _credential(data.get("token"), client.expires_at, utcnow())
        return Pairing(credential, client.id)

    def refresh(self, old: Credential, now: datetime) -> Credential:
        self._identity(old.token)
        data = self._request(Route.REFRESH, token=old.token)
        if not isinstance(data, dict):
            raise outbound.OutboundError(INVALID)
        expires_at = _validate(TypeAdapter(Timestamp), data.get("expires_at"))
        return _credential(data.get("token"), expires_at, now, old=old)

    def snapshot(self, token: str) -> Snapshot:
        return self.read_snapshot(token).project(utcnow())

    def read_snapshot(self, token: str) -> SnapshotReading:
        liveness = _validate(TypeAdapter(Liveness), self._request(Route.HEALTH))
        observed = utcnow()
        self._identity(token)
        previous_checks = CheckReadings.validate_python(self.link.my_house_checks or [])
        previous_worker_error_at = next(
            (
                check.worker_error_observed_at
                for check in previous_checks
                if check.key == "worker" and check.state == "error"
            ),
            None,
        )
        requested_at = utcnow()
        system_data = self._request(Route.SYSTEM, token=token)
        system, checks = _system_readings(
            system_data, requested_at, utcnow(), previous_worker_error_at=previous_worker_error_at
        )
        backup_age = next((check.get("age_h") for check in system_data["checks"] if check["key"] == "backup"), None)
        backup = None
        if isinstance(backup_age, (int, float)) and not isinstance(backup_age, bool) and 0 <= backup_age < math.inf:
            backup = BackupReading(age_h=backup_age, observed_at=requested_at)
        homes = _validate(TypeAdapter(Rows[Home]), self._request(Route.HOMES, token=token))
        if len({home.id for home in homes}) != len(homes):
            raise outbound.OutboundError(INVALID)
        settings_observed_at = utcnow()
        settings = self._request(Route.SETTINGS, token=token)
        flags = _validate(TypeAdapter(Settings), settings)
        return SnapshotReading(
            snapshot=Snapshot(
                observed_at=observed,
                databaseprobe=liveness,
                systeem=system,
                woningen=[self._overview(home, token) for home in homes],
                instellingen=HouseSettings(
                    **flags.model_dump(),
                    link=user_link(self.link.basis_url, settings.get("lan_url"), settings.get("remote_url")),
                    observed_at=settings_observed_at,
                ),
                laatste_backup=backup,
            ),
            checks=checks,
        )

    def _overview(self, home: Home, token: str) -> Overview:
        zone_data = self._request(Route.ZONES, token=token, home_id=home.id)
        zones = _validate(TypeAdapter(Rows[Zone]), zone_data)
        observed = utcnow()
        for zone, raw in zip(zones, zone_data, strict=True):
            policy = raw.get("policy")
            source_age = policy.get("stale_after_s") if isinstance(policy, dict) else None
            max_age = SENSOR_MIN_AGE_S
            if isinstance(source_age, int) and SENSOR_MIN_AGE_S <= source_age <= SENSOR_MAX_AGE_S:
                max_age = min(source_age, basis.MAX_AGE_S)
            zone.temperature = zone.temperature.model_copy(update={"max_age_s": max_age}).met_meettijd(observed, "°C")
            zone.humidity = zone.humidity.model_copy(update={"max_age_s": max_age}).met_meettijd(observed, "%")
        lights = _validate(TypeAdapter(Lights), self._request(Route.LIGHTS, token=token, home_id=home.id))
        alerts_observed_at = utcnow()
        alerts = _validate(TypeAdapter(Rows[Alert]), self._request(Route.ALERTS, token=token, home_id=home.id))
        devices = _validate(TypeAdapter(Rows[Device]), self._request(Route.DEVICES, token=token, home_id=home.id))
        return Overview(
            woning=home,
            zones=zones,
            licht=lights,
            meldingen=Alerts(
                items=alerts, open=len(alerts), begrensd=len(alerts) >= 100, observed_at=alerts_observed_at
            ),
            apparaten=devices,
        )


def health(checks: list[CheckReading], now: datetime) -> basis.Measurement:
    measurements = [check.measurement(now) for check in checks]
    if not {"database", "worker"} <= {check.key for check in checks}:
        measurements.append(basis.Measurement(status="unknown", reason_code="meting_onbekend"))
    return max(
        measurements,
        key=lambda item: (
            SEVERITY[item.status],
            item.reason_code == "meting_verouderd",
            age_seconds(item.observed_at, now) or 0,
        ),
    )
