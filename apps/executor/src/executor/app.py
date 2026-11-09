"""HTTP-API van de executor (fase P0): gezondheid, statuspagina en een uitvoer-endpoint dat alles weigert."""

from __future__ import annotations

import os
import uuid
from collections.abc import Awaitable, Callable
from html import escape
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from executor import APP_ID, __version__
from executor.allowlist import ALLOWLIST, check
from executor.config import Settings, get_settings
from executor.firststart import IDENTITY, VAULT_KEY, public_jwk


class ExecuteIn(BaseModel):
    """Vorm volgt later ``ExecutionRequest`` (contract §8); in P0 wordt alleen ``action_id`` gelezen om te weigeren."""

    model_config = ConfigDict(extra="allow")
    action_id: str = Field(min_length=1, max_length=128)


def _err(code: str, message: str, status: int, details: dict[str, Any] | None = None) -> JSONResponse:
    body = {"code": code, "message": message, "details": details or {}, "trace_id": str(uuid.uuid4())}
    return JSONResponse(body, status_code=status)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="AI Server Manager — executor",
        version=__version__,
        description="Executor van TrueNAS Home Platform V2. Fase P0: nog niet gekoppeld; de allowlist is leeg en "
        "elke actie wordt geweigerd. Geen shell, sudo of Docker.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _err(
            "not_found" if exc.status_code == 404 else "http_error",
            "Niet gevonden." if exc.status_code == 404 else "Er ging iets mis.",
            exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _err(
            "validation_error",
            "De invoer is ongeldig.",
            422,
            {"fouten": [{"veld": ".".join(str(p) for p in e["loc"]), "fout": e["msg"]} for e in exc.errors()]},
        )

    @app.middleware("http")
    async def _headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    def status() -> dict[str, Any]:
        return {
            "app": APP_ID,
            "versie": __version__,
            "gekoppeld": False,
            "toelichting": "Nog niet gekoppeld. Koppelen met de Hub (koppelcode + TrueNAS-API-key met schrijfrechten) "
            "volgt in fase P2. Tot die tijd voert de executor niets uit.",
            "allowlist": sorted(ALLOWLIST),
            "identiteit": public_jwk(settings.secrets_dir),
        }

    @app.get("/healthz", tags=["gezondheid"], summary="Proces leeft")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "app": APP_ID, "version": __version__}

    @app.get("/readyz", tags=["gezondheid"], summary="Eigen geheimen aanwezig en datamap beschrijfbaar")
    def readyz() -> JSONResponse:
        secrets_ok = all((settings.secrets_dir / n).exists() for n in (IDENTITY, VAULT_KEY))
        writable = os.access(settings.data_dir, os.W_OK)
        checks = [
            {"name": "geheimen", "status": "ok" if secrets_ok else "down"},
            {"name": "datamap", "status": "ok" if writable else "down"},
            {"name": "koppeling", "status": "niet_gekoppeld"},
        ]
        ok = secrets_ok and writable
        return JSONResponse(
            {"status": "ready" if ok else "not_ready", "gekoppeld": False, "checks": checks},
            status_code=200 if ok else 503,
        )

    @app.get("/api/v1/status", tags=["status"], summary="Koppelstatus en (lege) allowlist")
    def api_status() -> dict[str, Any]:
        return status()

    @app.post(
        "/api/v1/execute",
        tags=["uitvoeren"],
        status_code=403,
        summary="Weigert alles (allowlist leeg in P0)",
        responses={403: {"description": "Actie geweigerd"}},
    )
    def execute(body: ExecuteIn) -> JSONResponse:
        verdict = check(body.action_id)
        return _err(verdict.code, verdict.message, 403, {"action_id": body.action_id, "gekoppeld": False})

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def page() -> HTMLResponse:
        s = status()
        return HTMLResponse(f"""<!doctype html><html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Executor — nog niet gekoppeld</title>
<style>body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}}
.badge{{display:inline-block;padding:.1rem .5rem;border-radius:.5rem;background:#fde68a}}</style></head><body>
<h1>AI Server Manager — executor</h1>
<p>Versie {escape(__version__)} · <span class="badge">nog niet gekoppeld</span></p>
<p>{escape(s["toelichting"])}</p>
<p>Voer hier nog <strong>geen</strong> TrueNAS-API-key in: er is in deze versie geen koppelformulier.
Toegestane acties: <strong>geen</strong> (de allowlist is leeg).</p>
<p>Gezondheid: <a href="/healthz">/healthz</a> · <a href="/readyz">/readyz</a></p>
</body></html>""")

    return app
