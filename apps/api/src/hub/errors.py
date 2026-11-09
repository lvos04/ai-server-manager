"""Uniform foutformaat (contract §5): ``{code, message (NL), details, trace_id}``."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("hub.errors")


class HubError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
        self.details = details or {}
        self.headers = headers or {}


def trace_id_of(request: Request) -> str:
    tid = getattr(request.state, "trace_id", None)
    return str(tid) if tid else str(uuid.uuid4())


def error_body(request: Request, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details or {}, "trace_id": trace_id_of(request)}


_STATUS_CODES = {
    400: ("bad_request", "Ongeldig verzoek."),
    401: ("unauthorized", "Niet aangemeld of ongeldige aanmelding."),
    403: ("forbidden", "Geen toestemming voor deze handeling."),
    404: ("not_found", "Niet gevonden."),
    405: ("method_not_allowed", "Deze methode is hier niet toegestaan."),
    409: ("conflict", "Conflict met de huidige toestand."),
    413: ("payload_too_large", "Het verzoek is te groot."),
    415: ("unsupported_media_type", "Alleen JSON wordt ondersteund."),
    429: ("rate_limited", "Te veel verzoeken; probeer het later opnieuw."),
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HubError)
    async def _hub_error(request: Request, exc: HubError) -> JSONResponse:
        return JSONResponse(
            error_body(request, exc.code, exc.message, exc.details), status_code=exc.status, headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fouten = [
            {"veld": ".".join(str(p) for p in err.get("loc", ())), "fout": err.get("msg", ""), "type": err.get("type")}
            for err in exc.errors()
        ]
        return JSONResponse(
            error_body(request, "validation_error", "De invoer is ongeldig.", {"fouten": fouten}), status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _STATUS_CODES.get(exc.status_code, ("http_error", "Er ging iets mis."))
        return JSONResponse(error_body(request, code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("onverwachte fout (trace_id=%s)", trace_id_of(request))
        return JSONResponse(
            error_body(request, "internal_error", "Interne fout; de details staan in de app-log onder deze trace_id."),
            status_code=500,
        )
