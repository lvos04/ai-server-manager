"""FastAPI-applicatie van de Hub."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hub import __version__
from hub.config import Settings, get_settings
from hub.db import make_engine, make_sessionmaker
from hub.errors import error_body, install_error_handlers
from hub.firststart import ensure_secrets, log_lines
from hub.keys import KeyRing
from hub.onboarding.service import seed
from hub.routers import auth, backups, breakglass, events, health, inventory, onboarding, services
from hub.vault import Vault

log = logging.getLogger("hub")
MAX_BODY_BYTES = 1024 * 1024


class BodyLimit:
    """Harde grens van 1 MiB per verzoek, ook zonder ``Content-Length`` (chunked): de body wordt tijdens het lezen
    geteld en bij overschrijding afgebroken met 413 ``payload_too_large`` (nooit eerst alles in het geheugen)."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        total = 0

        async def limited() -> Message:
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > self.max_bytes:
                    # FastAPI's HTTPException wordt door de body-parser doorgegeven (en niet tot 400 gemaakt).
                    raise HTTPException(status_code=413)
            return message

        await self.app(scope, limited, send)


OPENAPI_TAGS = [
    {"name": "gezondheid", "description": "healthz/readyz zonder auth en zonder geheimen."},
    {
        "name": "aanmelden en gebruikers",
        "description": "Setupcode → eerste admin, sessies + CSRF, rollen, JWKS, dienst-JWT.",
    },
    {
        "name": "diensten en enrollment",
        "description": "Eenmalige enrollment-tokens/koppelcodes en service-tokens (alleen hashes).",
    },
    {
        "name": "onboarding en gates",
        "description": "Besluiten D01–D18, metingen, bewijs, gates en de alleen-lezen TrueNAS-koppeling.",
    },
    {
        "name": "inventaris",
        "description": "Alleen-lezen inventaris met observed_at/veroudering en het dienstenregister.",
    },
    {
        "name": "back-up en herstel",
        "description": "Dekking, snapshotbeleid (voorstel), eigen pg_dump-export, hersteltests.",
    },
    {
        "name": "events en connector",
        "description": "Events-inbox met dedupe, audit en het connectorcontract van de Hub.",
    },
]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)
    factory = make_sessionmaker(engine)

    @lru_cache(maxsize=1)
    def keyring() -> KeyRing:
        return KeyRing.load(settings.secrets_dir)

    @lru_cache(maxsize=1)
    def vault() -> Vault:
        return Vault.from_file(settings.secrets_dir / "vault.key")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Alleen ontbrekende geheimen aanmaken; een bestaande geldige setupcode blijft gelden (ADR-0004).
        result = ensure_secrets(
            settings.secrets_dir, setup_code_ttl_seconds=settings.setup_code_ttl_seconds, new_setup_code=False
        )
        for line in log_lines(result):
            log.warning(line) if "SETUPCODE" in line else log.info(line)
        try:
            with factory() as db:
                seed(db)
                db.commit()
        except Exception as exc:
            log.warning("besluiten nog niet geïnitialiseerd: %s", type(exc).__name__)
        yield
        engine.dispose()

    app = FastAPI(
        title="AI Server Manager — Hub API",
        version=__version__,
        description="Centrale Hub van TrueNAS Home Platform V2 (B01/B02/B09/B12). Fouten: "
        "`{code, message, details, trace_id}`; mutaties vereisen `Idempotency-Key` (UUID).",
        openapi_tags=OPENAPI_TAGS,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = factory
    app.state.keyring = keyring
    app.state.vault = vault
    install_error_handlers(app)
    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def _middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        incoming = request.headers.get("x-trace-id", "")
        try:
            trace = str(uuid.UUID(incoming))
        except ValueError:
            trace = str(uuid.uuid4())
        request.state.trace_id = trace
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse(error_body(request, "payload_too_large", "Het verzoek is te groot."), status_code=413)
        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace
        if getattr(request.state, "hub_token_rotation", False):
            response.headers["Hub-Token-Rotation"] = "required"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        if request.url.path.startswith(("/api/", "/connector/")):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    for r in (
        health.router,
        auth.router,
        breakglass.router,
        services.router,
        onboarding.router,
        inventory.router,
        backups.router,
        events.router,
    ):
        app.include_router(r)
    return app
