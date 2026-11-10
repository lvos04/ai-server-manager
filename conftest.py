"""Gedeelde testfixtures (unit, integratie en dienst-E2E).

Integratietests gebruiken een eigen tijdelijke database ``asm_test_<id>`` op de PostgreSQL uit
``HUB_TEST_ADMIN_URL`` (standaard ``postgresql://postgres@127.0.0.1:5432/postgres``); die wordt na de run verwijderd.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ADMIN_URL = os.environ.get("HUB_TEST_ADMIN_URL", "postgresql://postgres@127.0.0.1:5432/postgres")
STRONG_PASSWORD = "Correct-Paard-Batterij-Nietje-42"


def _psycopg_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def _libpq(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    import psycopg

    name = f"asm_test_{uuid.uuid4().hex[:8]}"
    try:
        with psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=5) as conn:
            conn.execute(f'CREATE DATABASE "{name}"')
    except psycopg.OperationalError as exc:
        if os.environ.get("CI") or os.environ.get("HUB_TEST_REQUIRE_PG"):
            # In CI nooit stil overslaan: zonder database zouden de integratie- en E2E-tests 'groen' lijken.
            pytest.fail(f"PostgreSQL vereist (CI) maar niet bereikbaar: {exc}")
        pytest.skip(f"geen PostgreSQL voor integratietests: {exc}")
    base = ADMIN_URL.rsplit("/", 1)[0]
    url = f"{base}/{name}"
    from hub import migrations

    migrations.upgrade(_psycopg_url(url))
    yield url
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
def clean_db(pg_url: str) -> str:
    import psycopg

    with psycopg.connect(pg_url, autocommit=True) as conn:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'"
            )
        ]
        if tables:
            # Alleen tests: het auditspoor weigert TRUNCATE (trigger, migratie 0010); als superuser tussen tests
            # leegmaken met triggers uit voor deze ene opdracht.
            conn.execute("SET session_replication_role = replica")
            conn.execute("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE")
            conn.execute("RESET session_replication_role")
    return pg_url


@pytest.fixture
def settings(clean_db: str, tmp_path: Path) -> Any:
    from hub.config import Settings

    return Settings(
        data_dir=tmp_path / "appdata",
        database_url=_psycopg_url(clean_db),
        inventory_ttl_seconds=900,
        truenas_connect_timeout=3,
        truenas_read_timeout=3,
        login_max_failures=5,
        service_token_rotation_grace_seconds=600,
        # Alleen tests: de fakes (Uptime Kuma, Beszel, Gotify) draaien op 127.0.0.1.
        outbound_allow_loopback=True,
        service_call_connect_timeout=2,
        service_call_read_timeout=3,
    )


@pytest.fixture
def setup_code(settings: Any) -> str:
    from hub.firststart import ensure_secrets

    res = ensure_secrets(settings.secrets_dir, new_setup_code=True)
    assert res.setup_code
    return res.setup_code


@pytest.fixture
def app(settings: Any, setup_code: str) -> Any:
    from hub.app import create_app

    return create_app(settings)


@pytest.fixture
def client(app: Any) -> Iterator[Any]:
    from fastapi.testclient import TestClient

    with TestClient(app, base_url="https://testserver") as c:
        yield c


def idem() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}


@pytest.fixture
def admin(client: Any, setup_code: str) -> Any:
    """Client die als eerste beheerder is aangemeld (via de setupcode), met CSRF-header."""
    r = client.post(
        "/api/v1/setup/admin",
        json={
            "setup_code": setup_code,
            "username": "beheerder",
            "password": STRONG_PASSWORD,
        },
    )
    assert r.status_code == 200, r.text
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return client


def make_user(admin_client: Any, username: str, role: str) -> None:
    r = admin_client.post(
        "/api/v1/users",
        json={"username": username, "password": STRONG_PASSWORD, "role": role},
        headers=idem(),
    )
    assert r.status_code == 201, r.text


def login_as(app: Any, username: str) -> Any:
    from fastapi.testclient import TestClient

    c = TestClient(app, base_url="https://testserver")
    r = c.post("/api/v1/auth/login", json={"username": username, "password": STRONG_PASSWORD})
    assert r.status_code == 200, r.text
    c.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return c


@pytest.fixture
def fake_nas() -> Iterator[Any]:
    from fakes.fake_truenas import FakeTrueNAS

    nas = FakeTrueNAS().start()
    yield nas
    nas.stop()


@pytest.fixture
def periodic_run(app: Any, settings: Any) -> Any:
    """Periodieke worker-taken direct draaien met een vaste 'nu' (``force`` negeert het interval)."""
    from hub.monitoring import periodic

    def run(*names: str, now: Any = None) -> dict[str, Any]:
        out = periodic.run_due(
            app.state.sessionmaker,
            settings,
            app.state.vault(),
            app.state.keyring(),
            now=now,
            force=True,
            only=set(names) if names else None,
        )
        return {r["taak"]: r for r in out}

    return run


@pytest.fixture
def worker_once(app: Any, settings: Any) -> Any:
    from hub import worker

    def run(schedule: bool = False) -> list[dict[str, Any]]:
        return worker.run_once(app.state.sessionmaker, settings, app.state.vault(), schedule=schedule)

    return run


def service_jwk(seed: bytes | None = None) -> dict[str, str]:
    """Publieke Ed25519-identiteit van een dienst zoals contract 1.2 §3.3 vraagt: ``{kty, crv, x, kid=thumbprint}``."""
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from hub.keys import jwk_thumbprint

    key = Ed25519PrivateKey.from_private_bytes(seed) if seed else Ed25519PrivateKey.generate()
    raw = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    jwk = {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": base64.urlsafe_b64encode(raw).rstrip(b"=").decode(),
    }
    jwk["kid"] = jwk_thumbprint(jwk)
    return jwk


def enroll_body(
    app_id: str,
    *,
    token: str | None = None,
    code: str | None = None,
    jwk: dict[str, str] | None = None,
    version: str = "0.1.0",
    base_url: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "app_id": app_id,
        "version": version,
        "base_url": base_url,
        "public_key_jwk": jwk or service_jwk(),
    }
    if token is not None:
        body["enrollment_token"] = token
    if code is not None:
        body["pairing_code"] = code
    return body
