"""Begrensde TrueNAS-catalogusmeting en uitlezen van een exacte pin (contract §4.4, M3)."""

from __future__ import annotations

import asyncio
import math
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select, text, update
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
MEASUREMENT_INTERVAL = timedelta(seconds=300)
MEASUREMENT_LOCK = 0x41534D4D33
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


def _catalog_index(raw: Any) -> dict[str, dict[str, dict[str, Any]]]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError("Geen leesbare catalogusindex.")
    catalog: dict[str, dict[str, dict[str, Any]]] = {}
    count = 0
    for train in TRAINS:
        if train not in raw:
            continue
        entries = raw[train]
        if not isinstance(entries, dict):
            raise ValueError("Ongeldige catalogustrein.")
        # Een lege trein heeft geen bewijs dat de bron deze trein volledig heeft ingelezen.
        if not entries:
            continue
        count += len(entries)
        if count > MAX_COMBINATIONS:
            raise ValueError("Te veel catalogusversies.")
        apps: dict[str, dict[str, Any]] = {}
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
            apps[app] = {"latest": entry["latest_version"] if entry["healthy"] else None}
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
        for app, entry in apps.items()
        if entry["latest"] is not None and (train, app) != IX_APP
    )
    # De versie van het Custom App-sjabloon wordt elke ronde gemeten. Andere apps rouleren op indexvolgorde.
    batch_size = DETAILS_PER_ROUND - 1
    offset = (round_number * batch_size) % len(candidates) if candidates else 0
    selected = (candidates[offset:] + candidates[:offset])[:batch_size]
    if catalog.get("stable", {}).get("ix-app", {}).get("latest") is not None:
        selected.insert(0, IX_APP)
    for train, app in selected:
        entry = catalog[train][app]
        detail = await client.call("catalog.get_app_details", [app, {"train": train}])
        versions = detail.get("versions") if isinstance(detail, dict) and detail.get("name") == app else None
        if (
            not isinstance(versions, dict)
            or detail.get("healthy") is not True
            or detail.get("latest_version") != entry["latest"]
            or entry["latest"] not in versions
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
        entry["versions"] = dict.fromkeys(versions, True)
    return catalog


async def _measure(client: TrueNASClient, round_number: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        async with asyncio.timeout(MEASUREMENT_TIMEOUT):
            await client.open()
            catalog = await _collect(client, round_number)
            await client.close()
        if time.monotonic() - started <= MEASUREMENT_TIMEOUT:
            return catalog
    except (TrueNASError, OSError, TypeError, ValueError):
        pass  # Sla nooit ongefilterde brondata of bronfouten op.
    finally:
        # Ook als open() tijdens de aanmelding faalde, blijft er geen verbinding achter.
        client.abort()
    return {}


def refresh_if_due(factory: sessionmaker[Session], settings: Settings, vault: Vault) -> None:
    with factory.begin() as db:
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": MEASUREMENT_LOCK}):
            return
        target = current_target(db)
        connection = db.get(TrueNASConnection, 1)
        if target is None or connection is None:
            return
        binding = _binding(db, target, connection)
        now = utcnow()
        # Commit de start onder dezelfde Hub-brede lock, zodat een afgebroken worker het interval niet vergeet.
        with factory.begin() as reservation:
            previous = reservation.get(CatalogSnapshot, 1)
            if previous is not None and now - previous.started_at < MEASUREMENT_INTERVAL:
                return
            round_number = previous.round_number + 1 if previous is not None and previous.binding == binding else 0
            reservation.merge(
                CatalogSnapshot(
                    id=1, started_at=now, binding=binding, round_number=round_number, catalog={}, observed_at=None
                )
            )
        try:
            api_key = vault.get(db, API_KEY_REF)
        except VaultError:
            return
        if not api_key:
            return
        client = TrueNASClient(
            target.url,
            api_key,
            tls=tls_for(connection, target, settings),
            connect_timeout=settings.truenas_connect_timeout,
            read_timeout=settings.truenas_read_timeout,
            response_budget=MAX_SOURCE_BYTES,
        )
        catalog = asyncio.run(_measure(client, round_number))
        if catalog:
            db.execute(update(CatalogSnapshot).where(CatalogSnapshot.id == 1).values(catalog=catalog, observed_at=now))


def read_pin(db: Session, train: Train, app: str, version: str) -> tuple[Availability, datetime | None]:
    target, connection = current_target(db), db.get(TrueNASConnection, 1)
    if target is None or connection is None:
        return "onbekend", None
    catalog = CatalogSnapshot.catalog
    entry = catalog[train][app]
    row = db.execute(
        select(
            CatalogSnapshot.observed_at,
            catalog[train].bool_op("?")(app),
            entry["latest"].as_string(),
            entry["versions"].bool_op("?")(version),
        ).where(CatalogSnapshot.id == 1, CatalogSnapshot.binding == _binding(db, target, connection))
    ).first()
    if row is None or row[0] is None or not -120 <= (utcnow() - row[0]).total_seconds() <= 900:
        return "onbekend", None
    measured, exists, latest, present = row
    if latest == version or present is True:
        return "ja", measured
    if exists is False or present is False:  # gemeten trein zonder deze app, of volledige versielijst zonder de pin
        return "nee", measured
    return "onbekend", None


def charge_read(db: Session, service_id: str) -> None:
    """Eén begrensd schuivend venster per registratie, gedeeld door alle tokens en API-processen."""
    service_uuid = uuid.UUID(service_id)
    if db.scalar(select(Service.status).where(Service.id == service_uuid).with_for_update()) != "active":
        raise HubError(401, "unauthorized", "Deze dienst is ingetrokken.")
    now = utcnow()
    row = db.get(CatalogReadWindow, service_uuid)
    recent = [at for at in row.requests if (now - at).total_seconds() < 60] if row else []
    if len(recent) >= 60:
        wait = max(1, math.ceil(60 - (now - min(recent)).total_seconds()))
        raise HubError(429, "rate_limited", "Te veel catalogusverzoeken.", headers={"Retry-After": str(wait)})
    db.merge(CatalogReadWindow(service_id=service_uuid, requests=[*recent, now]))
    db.commit()
