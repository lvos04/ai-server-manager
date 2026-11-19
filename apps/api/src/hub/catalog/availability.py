"""Begrensde TrueNAS-catalogusmeting en uitlezen van een exacte pin (contract §4.4, M3)."""

from __future__ import annotations

import asyncio
import fcntl
import math
import os
import re
import time
import uuid
from collections.abc import Iterator
from concurrent.futures import Future
from contextlib import closing, contextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock, Thread
from time import monotonic_ns, time_ns
from typing import Any, BinaryIO, Literal, NamedTuple

import psycopg
from cryptography.exceptions import InvalidTag
from psycopg import generators, waiting
from psycopg.abc import PQGen
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from sqlalchemy import Connection, and_, create_engine, delete, event, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import TimeoutError as StorageTimeout
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from hub.config import Settings
from hub.errors import HubError
from hub.models import CatalogAttempt, CatalogReadWindow, CatalogSnapshot, Decision, Service, TrueNASConnection
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
FINISH_BUDGET = 0.1
MEASUREMENT_INTERVAL = timedelta(seconds=300)
MEASUREMENT_LOCK = 0x41534D4D33
MEASUREMENT_RECEIPT = "catalogus-meetbewijs"
_LOCAL_MEASUREMENT = Lock()
DETAILS_PER_ROUND = 4
IX_APP = ("stable", "ix-app")


class _Confirmation(NamedTuple):
    attempt_id: int
    started: datetime
    monotonic_start: int
    database_start: datetime


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


def _milliseconds(deadline: float) -> int:
    remaining = int((deadline - time.monotonic()) * 1000)
    if remaining <= 0:  # PostgreSQL zou 0 als onbeperkt uitleggen.
        raise StorageTimeout("De tijd voor de catalogusmeting is verstreken.")
    return remaining


class _MeasurementConnection(psycopg.Connection[tuple[Any, ...]]):
    """Begrens ook de lokale socketwacht op COMMIT of ROLLBACK als PostgreSQL geen statementtimer meer heeft."""

    deadline: float

    def wait[T](self, gen: PQGen[T], interval: float = 0.1, timeout: float | None = None) -> T:
        remaining = max(0.0, self.deadline - time.monotonic())
        try:
            return super().wait(gen, interval, remaining if timeout is None else min(remaining, timeout))
        except psycopg.OperationalError:
            self.close()
            raise


@contextmanager
def _statement_budget(db: Session, deadline: float) -> Iterator[None]:
    """Ook de eerste SELECT, ORM-flush en COMMIT krijgen alleen de resterende tijd."""
    _milliseconds(deadline)
    conn = db.connection()

    def before_statement(_conn: Connection, cursor: Any, *_args: Any) -> None:
        cursor.execute("SELECT set_config('statement_timeout', %s, true)", (str(_milliseconds(deadline)),))

    def before_commit(connection: Connection) -> None:
        with closing(connection.connection.cursor()) as cursor:
            before_statement(connection, cursor)

    event.listen(conn, "before_cursor_execute", before_statement)
    event.listen(conn, "commit", before_commit)
    try:
        yield
    finally:
        event.remove(conn, "commit", before_commit)
        event.remove(conn, "before_cursor_execute", before_statement)


@contextmanager
def _transaction(factory: sessionmaker[Session], deadline: float) -> Iterator[Session]:
    with factory() as db, _statement_budget(db, deadline):
        # Uitgestelde controles vallen zo onder de statement_timeout van de schrijfactie.
        db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        yield db
        db.commit()


def _start_attempt(
    factory: sessionmaker[Session], attempt_id: int, started: datetime, deadline: float
) -> CatalogAttempt | None:
    with _transaction(factory, deadline) as db:
        if not db.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": MEASUREMENT_LOCK}):
            return None
        previous = db.scalar(select(CatalogAttempt).order_by(CatalogAttempt.id.desc()).limit(1))
        if previous is not None:
            if started - previous.started_at < MEASUREMENT_INTERVAL:
                return None
            # Na minstens 300 s kan alleen de vorige poging nog nodig zijn tijdens de nieuwe meting.
            db.execute(delete(CatalogAttempt).where(CatalogAttempt.id < previous.id))
        attempt = CatalogAttempt(id=attempt_id, started_at=started)
        db.add(attempt)
    return attempt


def _measure_attempt(
    factory: sessionmaker[Session], settings: Settings, vault: Vault, attempt: CatalogAttempt, deadline: float
) -> bool:
    with _transaction(factory, deadline) as db:
        target, connection = current_target(db), db.get(TrueNASConnection, 1)
        if target is None or connection is None:
            return False
        binding = _binding(db, target, connection)
        # Alleen de rotatiepositie lezen. Bij een bezette voorraad geen bronverkeer starten.
        previous = db.execute(
            select(CatalogSnapshot.binding, CatalogSnapshot.round_number)
            .where(CatalogSnapshot.id == 1)
            .with_for_update(nowait=True)
        ).first()
        round_number = previous.round_number + 1 if previous and previous.binding == binding else 0
        if previous is None:
            db.add(CatalogSnapshot(id=1, started_at=attempt.started_at, binding=binding, round_number=0, catalog={}))
        api_key = vault.get(db, API_KEY_REF)
        if not api_key:
            return False
        client = TrueNASClient(
            target.url,
            api_key,
            tls=tls_for(connection, target, settings),
            connect_timeout=settings.truenas_connect_timeout,
            read_timeout=settings.truenas_read_timeout,
            response_budget=MAX_SOURCE_BYTES,
        )

    # Tijdens het wachten op de bron is er geen databasesessie of transactie uitgecheckt.
    catalog = asyncio.run(_measure(client, round_number, deadline))
    if not catalog:
        return False
    with _transaction(factory, deadline) as db:
        latest_id = select(CatalogAttempt.id).order_by(CatalogAttempt.id.desc()).limit(1).scalar_subquery()
        published = db.scalar(
            update(CatalogSnapshot)
            .where(CatalogSnapshot.id == 1, CatalogSnapshot.started_at <= attempt.started_at, latest_id == attempt.id)
            .values(
                started_at=attempt.started_at,
                observed_at=attempt.started_at,
                catalog=catalog,
                binding=binding,
                round_number=round_number,
            )
            .returning(CatalogSnapshot.id)
        )
    return published is not None


@contextmanager
def _measurement_sessions(factory: sessionmaker[Session], deadline: float) -> Iterator[sessionmaker[Session]]:
    # Een bezette algemene workerpool mag de toelating niet dertig seconden ophouden.
    # De achtergrondmeting opent uitsluitend korte lokale transacties op dezelfde database.
    url = factory.kw["bind"].url

    def connect() -> _MeasurementConnection:
        ms = _milliseconds(deadline)
        params = conninfo_to_dict(url.set(drivername="postgresql").render_as_string(hide_password=False))
        params["options"] = f"{params.get('options', '')} -c statement_timeout={ms}"
        # libpq connect_timeout kent alleen hele seconden. Poll dezelfde lokale verbinding met het echte restant.
        with closing(generators.connect(make_conninfo("", **params))) as handshake:
            connection = _MeasurementConnection(waiting.wait_conn(handshake, interval=0.1, timeout=ms / 1000))
        connection.deadline = deadline
        return connection

    engine = create_engine(url, poolclass=NullPool, creator=connect, hide_parameters=True)
    try:
        yield sessionmaker(engine, expire_on_commit=False, autoflush=False)
    finally:
        engine.dispose()


def _open_receipt(path: str, flags: int) -> int:
    return os.open(path, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)


def _confirmation(receipt: BinaryIO, confirmation: Path) -> _Confirmation | None:
    """Alleen de na het schrijven aangelegde harde koppeling bevestigt deze meetbeurt."""
    receipt.seek(0)
    try:
        data = receipt.read(193)
        if len(data) > 192:
            return None
        start, earliest, latest, number, ticks, database_start = data.decode("ascii").split()
        started = datetime.fromisoformat(start)
        proof = _Confirmation(int(number), started, int(ticks), datetime.fromisoformat(database_start))
        stamp = confirmation.stat(follow_symlinks=False)
        same_file = os.path.samestat(stamp, os.fstat(receipt.fileno()))
        if not same_file or not int(earliest) <= stamp.st_ctime_ns <= int(latest):
            return None
    except (FileNotFoundError, ValueError):
        return None
    return proof if started.tzinfo is not None else None


def _is_due(guard: BinaryIO, confirmation: Path, now: datetime) -> bool:
    previous = _confirmation(guard, confirmation)
    return previous is None or now - previous.started >= MEASUREMENT_INTERVAL


def _refresh(
    sessions: sessionmaker[Session],
    settings: Settings,
    vault: Vault,
    guard: BinaryIO,
    deadline: float,
    wall_window: tuple[int, int],
) -> None:
    path = settings.data_dir / MEASUREMENT_RECEIPT
    confirmation = path.with_suffix(".bevestigd")
    # Bij een gewone peiling van een verse meting blijven lezers ongehinderd.
    if not _is_due(guard, confirmation, utcnow()):
        return
    # Alle Hub-processen delen de datamap. Het kernelslot blijft tijdens de bronlezing
    # bestaan, ook als de systeemklok verspringt, en vervalt vanzelf bij een processtop.
    try:
        fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    started = utcnow()
    monotonic_start = monotonic_ns()
    if not _is_due(guard, confirmation, started):
        return

    # Reserveer het nummer vóór de eerste wijziging aan bestand of tabel. PostgreSQL
    # draait nextval niet terug als de intrekking of het invoegen van de poging faalt.
    try:
        with _transaction(sessions, deadline) as db:
            attempt_id, database_start = db.execute(
                text("SELECT nextval('catalog_attempt_id_seq'), pg_postmaster_start_time()")
            ).one()
    finally:
        confirmation.unlink(missing_ok=True)
    with open(path, "a+b", buffering=0, opener=_open_receipt) as receipt:
        if os.fstat(receipt.fileno()).st_size:
            receipt.truncate(0)
            os.fsync(receipt.fileno())
        work_until = deadline - min(FINISH_BUDGET, MEASUREMENT_TIMEOUT / 3)
        attempt = _start_attempt(sessions, attempt_id, started, work_until)
        if attempt is None:
            return
        try:
            published = _measure_attempt(sessions, settings, vault, attempt, work_until)
        except (DBAPIError, StorageTimeout, VaultError, InvalidTag, ValueError):
            published = False
        finished = utcnow()
        with _transaction(sessions, deadline) as db:
            db.execute(
                update(CatalogAttempt)
                .where(CatalogAttempt.id == attempt.id)
                .values(completed_at=finished if published else None, failed=not published)
            )
        if not published or time.monotonic() >= deadline:
            return
        wall_start, wall_end = wall_window
        data = (
            f"{started.isoformat()} {wall_start} {wall_end} {attempt_id} "
            f"{monotonic_start} {database_start.isoformat()}\n"
        ).encode("ascii")
        if receipt.write(data) != len(data):
            return
        os.fsync(receipt.fileno())
        if time.monotonic() < deadline:
            # link() publiceert atomair. De lezer toetst de door de kernel gezette
            # ctime, ook als de koppeling zelf pas na het tijdvenster tot stand kwam.
            os.link(path, confirmation, follow_symlinks=False)
            if time.monotonic() > deadline:
                confirmation.unlink(missing_ok=True)


def _run_refresh(
    factory: sessionmaker[Session], settings: Settings, vault: Vault, deadline: float, wall_window: tuple[int, int]
) -> None:
    with _measurement_sessions(factory, deadline) as sessions, suppress(DBAPIError, StorageTimeout):
        try:
            path = settings.data_dir / MEASUREMENT_RECEIPT
            with os.fdopen(_open_receipt(str(path), os.O_RDONLY | os.O_CREAT), "rb", buffering=0) as guard:
                _refresh(sessions, settings, vault, guard, deadline, wall_window)
        except OSError:
            # Ook als de map zelf onbeschrijfbaar is, blijft de pogingstabel
            # onafhankelijk van de mogelijk bezette momentopnamerij.
            with _transaction(sessions, deadline) as db:
                db.execute(update(CatalogAttempt).where(CatalogAttempt.failed.is_(False)).values(failed=True))


def refresh_if_due(factory: sessionmaker[Session], settings: Settings, vault: Vault) -> None:
    # Houd ook tijd over om de periodieke worker na een time-out terug te geven.
    budget = MEASUREMENT_TIMEOUT - min(FINISH_BUDGET, MEASUREMENT_TIMEOUT / 3)
    wall_start = time_ns()
    deadline = time.monotonic() + budget
    wall_window = (wall_start, wall_start + round(budget * 1_000_000_000))
    result: Future[None] = Future()

    def measure() -> None:
        try:
            if _LOCAL_MEASUREMENT.acquire(blocking=False):
                try:
                    _run_refresh(factory, settings, vault, deadline, wall_window)
                finally:
                    _LOCAL_MEASUREMENT.release()
        except BaseException as exc:
            result.set_exception(exc)
        else:
            result.set_result(None)

    # Een bestandssysteemaanroep heeft geen annulering op deadline. Laat hoogstens
    # één meting per workerproces afwikkelen en houd de periodieke taken vrij.
    Thread(target=measure, name="catalogusmeting", daemon=True).start()
    with suppress(TimeoutError):
        result.result(timeout=max(0.0, deadline - time.monotonic()))


def read_pin(
    db: Session, settings: Settings, train: Train, app: str, version: str
) -> tuple[Availability, datetime | None]:
    with _statement_budget(db, time.monotonic() + MEASUREMENT_TIMEOUT):
        target, connection = current_target(db), db.get(TrueNASConnection, 1)
        if target is None or connection is None:
            return "onbekend", None
        versions = CatalogSnapshot.catalog["measured_versions"][train][app]
        # Beide pogingen en de voorraad voor deze bronbinding komen uit dezelfde MVCC-lezing.
        rows = db.execute(
            select(
                CatalogAttempt.id,
                CatalogAttempt.started_at,
                CatalogAttempt.completed_at,
                CatalogAttempt.failed,
                CatalogSnapshot.observed_at,
                versions.bool_op("?")(version),
            )
            .outerjoin(
                CatalogSnapshot,
                and_(
                    CatalogSnapshot.id == 1,
                    CatalogSnapshot.started_at == CatalogAttempt.started_at,
                    CatalogSnapshot.binding == _binding(db, target, connection),
                ),
            )
            .order_by(CatalogAttempt.id.desc())
            .limit(2)
        ).all()
        if not rows:
            return "onbekend", None
        path = settings.data_dir / MEASUREMENT_RECEIPT
        try:
            with open(path, "rb", opener=_open_receipt) as receipt:
                try:
                    fcntl.flock(receipt, fcntl.LOCK_SH | fcntl.LOCK_NB)
                except BlockingIOError:
                    return "onbekend", None
                confirmed = _confirmation(receipt, path.with_suffix(".bevestigd"))
                # Controleer onder hetzelfde slot als de schrijver het laatst uitgegeven
                # nummer, ook als de bijbehorende rij nooit kon worden vastgelegd.
                issued, database_start = db.execute(
                    text("SELECT last_value, pg_postmaster_start_time() FROM catalog_attempt_id_seq")
                ).one()
        except FileNotFoundError:
            return "onbekend", None
    now = utcnow()
    # Ook zonder spoor van een opvolger vervalt het bewijs na het volgende interval
    # plus de meetduur. De monotone klok loopt door bij een klokcorrectie. Vergelijk
    # haar alleen binnen dezelfde PostgreSQL-instantie (dus ook dezelfde systeemstart).
    horizon = MEASUREMENT_INTERVAL + timedelta(seconds=MEASUREMENT_TIMEOUT)
    if (
        confirmed is None
        or rows[0].id != issued
        or confirmed.database_start != database_start.astimezone(UTC)
        or now - confirmed.started > horizon
        or not 0 <= monotonic_ns() - confirmed.monotonic_start <= round(horizon.total_seconds() * 1_000_000_000)
    ):
        return "onbekend", None
    for attempt_id, started, completed, failed, observed, present in rows:
        started = started.astimezone(UTC)
        if failed:
            break
        if completed is None:
            if 0 <= (now - started).total_seconds() <= MEASUREMENT_TIMEOUT:
                continue  # De eerdere meting kan tijdens een lopende poging nog geldig zijn.
            break
        if not 0 <= (completed.astimezone(UTC) - started).total_seconds() <= MEASUREMENT_TIMEOUT:
            break
        if confirmed.attempt_id != attempt_id or confirmed.started != started:
            break
        if observed is not None and -120 <= (now - observed).total_seconds() <= 900 and present is not None:
            return ("ja" if present else "nee"), observed
        break
    return "onbekend", None


def charge_read(db: Session, service_id: str) -> None:
    """Eén begrensd schuivend venster per registratie, gedeeld door alle tokens en API-processen."""
    with _statement_budget(db, time.monotonic() + MEASUREMENT_TIMEOUT):
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
