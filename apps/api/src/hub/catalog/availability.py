"""Begrensde TrueNAS-catalogusmeting en uitlezen van een exacte pin (contract §4.4, M3)."""

from __future__ import annotations

import asyncio
import math
import re
import time
import uuid
from contextlib import suppress
from datetime import datetime, timedelta
from threading import Event, Thread, Timer
from typing import Any, Literal

from cryptography.exceptions import InvalidTag
from psycopg import OperationalError
from psycopg.errors import IdleInTransactionSessionTimeout, QueryCanceled
from sqlalchemy import Connection, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from hub.config import Settings
from hub.errors import HubError
from hub.models import CatalogReadWindow, CatalogSnapshot, Decision, Service, TrueNASConnection
from hub.security import sha256_hex
from hub.timeutil import utcnow
from hub.truenas.client import TrueNASClient, TrueNASError
from hub.truenas.connection import API_KEY_REF, NasTarget, current_target, tls_for
from hub.truenas.normalize import key_scope
from hub.vault import Vault, VaultError

Train = Literal["stable", "community", "enterprise"]
Availability = Literal["ja", "nee", "onbekend"]
TRAINS = ("stable", "community", "enterprise")
APP_PATTERN = r"[a-z0-9][a-z0-9-]{0,62}"
VERSION_PATTERN = r"v?[0-9]+\.[0-9]+\.[0-9]+([.+_-][0-9A-Za-z.+_-]+)?"
MAX_VERSION_LENGTH = 64
MAX_COMBINATIONS = 50_000
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MEASUREMENT_TIMEOUT = 15.0
ROLLBACK_BUDGET = 0.1
MEASUREMENT_INTERVAL = timedelta(seconds=300)
MEASUREMENT_LOCK = 0x41534D4D33
RESERVATION_MARK = 0x41534D4D34  # sessielock zolang een meetstart wordt vastgelegd: pins zijn dan onbekend
RESERVATION_CAP = 60
DETAILS_PER_ROUND = 4
IX_APP = ("stable", "ix-app")


def _binding(db: Session, target: NasTarget, connection: TrueNASConnection) -> str:
    """Een nieuwe koppeling, sleutel of vertrouwensbevestiging maakt een meting onbruikbaar."""
    decision = db.get(Decision, "D03")
    return sha256_hex(
        f"{target.url}|{decision.ingevuld_op if decision else None}|"
        f"{connection.api_key_set_at}|{connection.pinned_at}|{connection.pinned_fingerprint}"
    )


def _valid_version(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) <= MAX_VERSION_LENGTH and re.fullmatch(VERSION_PATTERN, value) is not None
    )


def _catalog_index(raw: Any) -> dict[str, dict[str, str | None]]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Geen leesbare catalogusindex.")
    catalog: dict[str, dict[str, str | None]] = {}
    count = 0
    for train in TRAINS:
        if train not in raw:
            continue
        entries = raw[train]
        if not isinstance(entries, dict):
            raise ValueError("Ongeldige catalogustrein.")
        count += len(entries)
        if count > MAX_COMBINATIONS:
            raise ValueError("Te veel catalogusversies.")
        apps: dict[str, str | None] = {}
        for app, entry in entries.items():
            if (
                re.fullmatch(APP_PATTERN, app) is None
                or not isinstance(entry, dict)
                or entry.get("name") != app
                or type(entry.get("healthy")) is not bool
            ):
                raise ValueError("Ongeldige catalogusapp.")
            if entry["healthy"] and not _valid_version(entry.get("latest_version")):
                raise ValueError("Ongeldige indexversie.")
            apps[app] = entry["latest_version"] if entry["healthy"] else None
        catalog[train] = apps
    return catalog


async def _collect(client: TrueNASClient, round_number: int) -> dict[str, dict[str, dict[str, Any]]]:
    if key_scope(await client.call("auth.me")) != "alleen_lezen":
        raise ValueError("Alleen-lezen sleutel vereist voor catalogusmeting.")
    methods = await client.call("core.get_methods")
    if not isinstance(methods, dict | list) or not {"catalog.apps", "catalog.get_app_details"}.issubset(methods):
        raise ValueError("Leesmethoden voor catalogus ontbreken.")
    # cache_only voorkomt het vullen of synchroon verversen van de broncatalogus.
    catalog = _catalog_index(
        await client.call("catalog.apps", [{"cache": True, "cache_only": True, "retrieve_all_trains": True}])
    )
    remaining = MAX_COMBINATIONS - sum(len(apps) for apps in catalog.values())
    candidates = sorted(
        (train, app)
        for train, apps in catalog.items()
        for app, latest in apps.items()
        if latest is not None and (train, app) != IX_APP
    )
    # De versie van het Custom App-sjabloon wordt elke ronde gemeten. Andere apps rouleren op indexvolgorde.
    batch_size = DETAILS_PER_ROUND - 1
    offset = (round_number * batch_size) % len(candidates) if candidates else 0
    selected = (candidates[offset:] + candidates[:offset])[:batch_size]
    if catalog.get("stable", {}).get("ix-app") is not None:
        selected.insert(0, IX_APP)
    measured: dict[str, dict[str, dict[str, bool]]] = {}
    for train, app in selected:
        latest = catalog[train][app]
        detail = await client.call("catalog.get_app_details", [app, {"train": train}])
        versions = detail.get("versions") if isinstance(detail, dict) and detail.get("name") == app else None
        if (
            not isinstance(versions, dict)
            or detail.get("healthy") is not True
            or detail.get("latest_version") != latest
            or latest not in versions
        ):
            raise ValueError("Onvolledige catalogusversies.")
        remaining -= len(versions) - 1  # de indexversie telde al mee
        if remaining < 0:
            raise ValueError("Te veel catalogusversies.")
        if any(
            not _valid_version(version) or not isinstance(info, dict) or info.get("version") != version
            for version, info in versions.items()
        ):
            raise ValueError("Ongeldig versierecord.")
        measured.setdefault(train, {})[app] = dict.fromkeys(versions, True)
    return {"measured_versions": measured} if measured else {}


async def _measure(client: TrueNASClient, round_number: int, deadline: float) -> dict[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return {}
    try:
        async with asyncio.timeout(remaining):
            await client.open()
            catalog = await _collect(client, round_number)
            await client.close()
        return catalog
    except (TrueNASError, OSError, TypeError, ValueError):
        pass  # Sla nooit ongefilterde brondata of bronfouten op.
    finally:
        # Ook als open() tijdens de aanmelding faalde, blijft er geen verbinding achter.
        client.abort()
    return {}


def _storage_budget(conn: Connection, deadline: float) -> bool:
    milliseconds = int((deadline - time.monotonic()) * 1000)
    if milliseconds <= 0:  # PostgreSQL zou 0 als onbeperkt uitleggen.
        return False
    conn.execute(
        text(
            "SELECT set_config('statement_timeout', :ms, true), "
            "set_config('idle_in_transaction_session_timeout', :ms, true)"
        ),
        {"ms": str(milliseconds)},
    )
    return True


def _publish(db: Session, catalog: dict[str, Any], observed: datetime, deadline: float) -> None:
    conn = db.connection()
    if not _storage_budget(conn, deadline):
        return
    driver = conn.connection.driver_connection
    assert driver is not None

    # PostgreSQL 16 stopt de statement_timeout vóór de afhandeling van COMMIT.
    # Voer uitgestelde controles al bij de UPDATE uit en bewaak COMMIT tot de verbinding terugkeert.
    def cancel_publication() -> None:
        # Bij een weggevallen verbinding blijven de tijdgrenzen op de server zelf gelden.
        with suppress(OperationalError):
            driver.cancel_safe(timeout=ROLLBACK_BUDGET)

    timer = Timer(max(0.0, deadline - time.monotonic()), cancel_publication)
    timer.start()
    try:
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        db.execute(update(CatalogSnapshot).where(CatalogSnapshot.id == 1).values(catalog=catalog, observed_at=observed))
        if _storage_budget(conn, deadline) and time.monotonic() < deadline:
            db.commit()
    finally:
        timer.cancel()
        timer.join()


def _reserve(factory: sessionmaker[Session], snapshot: CatalogSnapshot, klaar: Event, uitkomst: list[bool]) -> None:
    """Leg de meetstart vast op een eigen verbinding. Wacht op een rijvergrendeling mag langer duren dan de meting.

    De pins blijven onbekend (RESERVATION_MARK) totdat dit klaar is, ook nadat de meetpoging zelf is verlopen.
    """
    try:
        with factory() as session:
            if not session.scalar(text("SELECT pg_try_advisory_lock(:k)"), {"k": RESERVATION_MARK}):
                return
            try:
                session.execute(
                    text("SELECT set_config('statement_timeout', :ms, true)"), {"ms": str(RESERVATION_CAP * 1000)}
                )
                session.merge(snapshot)
                session.commit()
                uitkomst.append(True)
                klaar.set()
            finally:
                session.rollback()
                session.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": RESERVATION_MARK})
                session.commit()
    except DBAPIError:
        pass  # Zonder vastlegging volgt geen meting; de volgende ronde probeert opnieuw.
    finally:
        klaar.set()


def refresh_if_due(factory: sessionmaker[Session], settings: Settings, vault: Vault) -> None:
    # Houd de meetverbinding ook na commit uitgecheckt tot de annuleerder klaar is.
    # Zo raakt een annulering nooit een andere gebruiker van de pool.
    with factory.kw["bind"].connect() as conn:
        try:
            with factory(bind=conn) as db:
                _refresh(db, factory, settings, vault)
        except DBAPIError as exc:
            if not exc.connection_invalidated and not isinstance(
                exc.orig, (QueryCanceled, IdleInTransactionSessionTimeout)
            ):
                raise


def _refresh(db: Session, factory: sessionmaker[Session], settings: Settings, vault: Vault) -> None:
    # De tijdgrens geldt vanaf de reservering tot en met de commit en publicatie.
    deadline = time.monotonic() + MEASUREMENT_TIMEOUT - min(ROLLBACK_BUDGET, MEASUREMENT_TIMEOUT / 10)
    if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": MEASUREMENT_LOCK}):
        return
    target = current_target(db)
    connection = db.get(TrueNASConnection, 1)
    if target is None or connection is None:
        return
    binding = _binding(db, target, connection)
    now = utcnow()
    previous = db.get(CatalogSnapshot, 1)
    if previous is not None and now - previous.started_at < MEASUREMENT_INTERVAL:
        return
    round_number = previous.round_number + 1 if previous is not None and previous.binding == binding else 0
    # Commit de start onder dezelfde Hub-brede lock, zodat een afgebroken worker het interval niet vergeet.
    snapshot = CatalogSnapshot(
        id=1, started_at=now, binding=binding, round_number=round_number, catalog={}, observed_at=None
    )
    klaar, uitkomst = Event(), list[bool]()
    Thread(target=_reserve, args=(factory, snapshot, klaar, uitkomst), daemon=True).start()
    if not klaar.wait(max(0.0, deadline - time.monotonic())) or not uitkomst:
        return  # De reservering loopt zo nodig door op haar eigen verbinding; de meetlock komt nu vrij.
    if not _storage_budget(db.connection(), deadline):
        return
    try:
        api_key = vault.get(db, API_KEY_REF)
    except (VaultError, InvalidTag, ValueError):
        return
    if not api_key or time.monotonic() >= deadline:
        return
    client = TrueNASClient(
        target.url,
        api_key,
        tls=tls_for(connection, target, settings),
        connect_timeout=settings.truenas_connect_timeout,
        read_timeout=settings.truenas_read_timeout,
        response_budget=MAX_SOURCE_BYTES,
    )
    catalog = asyncio.run(_measure(client, round_number, deadline))
    if catalog and time.monotonic() < deadline:
        _publish(db, catalog, now, deadline)


def read_pin(db: Session, train: Train, app: str, version: str) -> tuple[Availability, datetime | None]:
    target, connection = current_target(db), db.get(TrueNASConnection, 1)
    if target is None or connection is None:
        return "onbekend", None
    if db.scalar(
        text(
            "SELECT EXISTS (SELECT FROM pg_locks WHERE locktype = 'advisory' AND objsubid = 1 AND granted "
            "AND (classid::bigint << 32) | objid::bigint = :k)"
        ),
        {"k": RESERVATION_MARK},
    ):
        return "onbekend", None  # een meetstart wordt vastgelegd of wacht nog; de vorige meting geldt niet meer
    catalog = CatalogSnapshot.catalog
    # Alleen een gevalideerde versielijst uit deze ronde bewijst aanwezigheid of afwezigheid.
    # Eerdere Hub-versies sloegen ook de bronindex op. Hun momentopnamen tellen hier niet mee.
    versions = catalog["measured_versions"][train][app]
    row = db.execute(
        select(CatalogSnapshot.observed_at, versions.bool_op("?")(version)).where(
            CatalogSnapshot.id == 1, CatalogSnapshot.binding == _binding(db, target, connection)
        )
    ).first()
    if row is None or row[0] is None or not -120 <= (utcnow() - row[0]).total_seconds() <= 900:
        return "onbekend", None
    measured, present = row
    if present is True:
        return "ja", measured
    if present is False:
        return "nee", measured
    return "onbekend", None


def charge_read(db: Session, service_id: str) -> None:
    """Eén begrensd schuivend venster per registratie, gedeeld door alle tokens en API-processen."""
    service_uuid = uuid.UUID(service_id)
    if db.scalar(select(Service.status).where(Service.id == service_uuid).with_for_update()) != "active":
        raise HubError(401, "unauthorized", "Deze dienst is ingetrokken.", {"reason": "revoked"})
    now = utcnow()
    row = db.get(CatalogReadWindow, service_uuid)
    recent = [at for at in row.requests if (now - at).total_seconds() < 60] if row else []
    if len(recent) >= 60:
        wait = max(1, math.ceil(60 - (now - min(recent)).total_seconds()))
        raise HubError(429, "rate_limited", "Te veel catalogusverzoeken.", headers={"Retry-After": str(wait)})
    db.merge(CatalogReadWindow(service_id=service_uuid, requests=[*recent, now]))
    db.commit()
