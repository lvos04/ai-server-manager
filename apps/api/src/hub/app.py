"""FastAPI-applicatie van de Hub."""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from hub import __version__
from hub.config import Settings, get_settings
from hub.db import make_engine, make_sessionmaker
from hub.errors import install_error_handlers
from hub.firststart import ensure_secrets, log_lines
from hub.keys import KeyRing
from hub.onboarding.service import seed
from hub.routers import (
    alerts,
    auth,
    backups,
    breakglass,
    catalog,
    events,
    health,
    inventory,
    metrics,
    monitoring,
    notifications,
    observability,
    onboarding,
    services,
)
from hub.vault import Vault

log = logging.getLogger("hub")
MAX_BODY_BYTES = 1024 * 1024


class BodyLimit:
    """Harde grens van 1 MiB per verzoek (contract §5), **vóór routering en authenticatie**, ook zonder
    ``Content-Length`` (chunked).

    Een te grote ``Content-Length`` wordt direct geweigerd. Anders leest deze laag de body (tellend, hooguit 1 MiB in
    het geheugen) vóórdat de app iets doet, en breekt af met ``413 payload_too_large`` zodra er meer binnenkomt. Zo
    krijgt ook een route die de body zelf niet leest, of een verzoek zonder aanmelding, altijd 413 en nooit eerst
    401/404/405. Daarna krijgt de app de gebufferde body.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def _too_large(self, scope: Scope, send: Send) -> None:
        state = scope.get("state") or {}
        trace = str(state.get("trace_id") or uuid.uuid4()) if isinstance(state, dict) else str(uuid.uuid4())
        body = {
            "code": "payload_too_large",
            "message": "Het verzoek is te groot (maximaal 1 MiB).",
            "details": {"max_bytes": self.max_bytes},
            "trace_id": trace,
        }
        await JSONResponse(body, status_code=413, headers={"Connection": "close"})(scope, _no_receive, send)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers") or []:
            if name == b"content-length":
                text = value.decode("latin-1").strip()
                if not text.isdigit():
                    await JSONResponse(
                        {"code": "bad_request", "message": "Ongeldige Content-Length.", "details": {},
                         "trace_id": str(uuid.uuid4())},
                        status_code=400,
                    )(scope, _no_receive, send)  # fmt: skip
                    return
                if int(text) > self.max_bytes:
                    await self._too_large(scope, send)
                    return
        chunks: list[bytes] = []
        total, more = 0, True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                # Client is weg vóór de body compleet was: niets uitvoeren, alleen netjes afsluiten.
                await JSONResponse(
                    {"code": "bad_request", "message": "Verbinding verbroken.", "details": {},
                     "trace_id": str(uuid.uuid4())},
                    status_code=400,
                )(scope, _no_receive, send)  # fmt: skip
                return
            part = message.get("body", b"")
            total += len(part)
            if total > self.max_bytes:
                await self._too_large(scope, send)
                return
            chunks.append(part)
            more = bool(message.get("more_body", False))
        buffered: Message = {"type": "http.request", "body": b"".join(chunks), "more_body": False}
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return buffered
            return await receive()  # daarna alleen nog http.disconnect

        await self.app(scope, replay, send)


async def _no_receive() -> Message:
    return {"type": "http.disconnect"}


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
        "name": "appcatalogus",
        "description": "Centrale appcatalogus (B01-002): identiteit, herkomst, image/digest, gezondheid; alleen-lezen.",
    },
    {
        "name": "monitoring",
        "description": "Bronnen (Uptime Kuma, Beszel), healthchecks en heartbeat van eigen diensten (B09-002).",
    },
    {
        "name": "observability",
        "description": "Live NAS-metingen met bron en laatst bijgewerkt; alleen TrueNAS (B01-004).",
    },
    {
        "name": "tijdreeksen",
        "description": "Genormaliseerde reeksen met bron en veroudering; ruw → 5 min → 1 uur met retentie (B09-003).",
    },
    {
        "name": "alerts",
        "description": "Alertregels met drempel, duur en hysterese; dempen; geen pushstorm (B09-003).",
    },
    {
        "name": "meldingen",
        "description": "Meldingskanalen (Gotify) en notification.send (R0) met rate-limit en stille uren.",
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
        catalog.router,
        monitoring.router,
        observability.router,
        metrics.router,
        alerts.router,
        notifications.router,
        backups.router,
        events.router,
    ):
        app.include_router(r)
    return app
