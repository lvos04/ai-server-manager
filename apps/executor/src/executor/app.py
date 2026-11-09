"""HTTP-API van de executor: gezondheid, statuspagina met koppelen (contract 1.2 §3.9) en een uitvoer-endpoint dat
alles weigert (allowlist leeg tot P2).

Koppelen kan alleen op de statuspagina, met een koppelcode (30 min) en de Hub-vingerafdruk, zolang de executor nog nooit
gekoppeld is. De TrueNAS-schrijfkey (en daarmee ontkoppelen/opnieuw koppelen op deze pagina) volgt in P2: tot dan geeft
dat ``capability_unavailable``, nooit gesimuleerd succes.
"""

from __future__ import annotations

import contextlib
import hmac
import os
import secrets
import threading
import time
import uuid
from collections import deque
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from executor import APP_ID, __version__
from executor.allowlist import ALLOWLIST, check
from executor.bodylimit import BodyLimit
from executor.config import Settings, get_settings
from executor.firststart import IDENTITY, VAULT_KEY, public_jwk
from executor.hublink import (
    ERRORS_NL,
    AuthFailed,
    EnrollFailed,
    HubLinkStore,
    KeyRotationPoller,
    confirm,
    enroll_with_pairing_code,
    public_status,
    resume_after_restart,
    valid_fingerprint,
    valid_pairing_code,
    validate_hub_url,
    verify_hub_jwt,
)
from executor.replay import ReplayCache, ReplayUnavailable
from executor.statuspagina import executor_page

CSRF_COOKIE = "executor_csrf"
MAX_FORM_BYTES = 4096
AUTH_MESSAGES = {
    "not_linked": "De executor is niet gekoppeld.",
    "revoked": "De koppeling is ingetrokken door de Hub.",
    "service_token_not_accepted": "Een service-token wordt hier niet geaccepteerd; de Hub stuurt een dienst-JWT.",
    "unknown_key": "Onbekende sleutel: niet gepind bij het koppelen.",
    "token_expired": "Het token is verlopen.",
    "invalid_token": "Ongeldig token.",
    "token_use_invalid": "Dit soort token is hier niet toegestaan.",
    "jti_missing": "Het token heeft geen jti.",
    "token_replayed": "Dit token is al gebruikt voor een andere wijziging.",
}
# Rollen in een gebruikers-JWT (contract §4.2); 'kind' wint altijd van andere rollen in dezelfde JWT.
ROLE_RANK = {"kind": 0, "viewer": 1, "operator": 2, "admin": 3}


def user_rank(claims: dict[str, Any]) -> int:
    roles = [r for r in claims.get("roles") or [] if r in ROLE_RANK]
    if not roles or "kind" in roles:
        return 0
    return max(ROLE_RANK[r] for r in roles)


class ExecuteIn(BaseModel):
    """Vorm volgt later ``ExecutionRequest`` (contract §8); in P0 wordt alleen ``action_id`` gelezen om te weigeren."""

    model_config = ConfigDict(extra="allow")
    action_id: str = Field(min_length=1, max_length=128)


def _err_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details or {}, "trace_id": str(uuid.uuid4())}


def _err(code: str, message: str, status: int, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(_err_body(code, message, details), status_code=status)


class PairingThrottle:
    """Max. 5 pogingen per 15 min per bron-IP én 20 per 15 min voor de hele executor (één API-proces)."""

    def __init__(self, per_ip: int, total: int, window: int) -> None:
        self.per_ip, self.total, self.window = per_ip, total, window
        self._ip: dict[str, deque[float]] = {}
        self._all: deque[float] = deque()
        self._lock = threading.Lock()

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        with self._lock:
            for q in (self._all, *self._ip.values()):
                while q and now - q[0] > self.window:
                    q.popleft()
            mine = self._ip.setdefault(ip, deque())
            if len(mine) >= self.per_ip or len(self._all) >= self.total:
                return False
            mine.append(now)
            self._all.append(now)
            return True


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    store = HubLinkStore(settings.secrets_dir)
    rotations = KeyRotationPoller(store)
    replays = ReplayCache(settings.replay_db)
    stop = threading.Event()

    def poll_loop() -> None:
        while not stop.wait(15 * 60):  # contract 1.2 §4.5: hooguit elke 15 minuten
            rotations.poll(force=True)

    throttle = PairingThrottle(
        settings.pairing_attempts_per_ip, settings.pairing_attempts_total, settings.pairing_window_seconds
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if settings.secrets_dir.exists():
            resume_after_restart(store)
            link = store.read()
            if link.get("state") == "gekoppeld" and not link.get("confirmed_at"):
                threading.Thread(target=confirm, args=(store,), daemon=True).start()
        threading.Thread(target=poll_loop, daemon=True).start()
        yield
        stop.set()

    app = FastAPI(
        title="AI Server Manager — executor",
        version=__version__,
        description="Executor van TrueNAS Home Platform V2. Koppelen met de Hub via de statuspagina (koppelcode + "
        "vingerafdruk, contract 1.2 §3.9). De allowlist is leeg tot P2: elke actie wordt geweigerd. Geen shell, sudo "
        "of Docker.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
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

    # 1 MiB vóór routering en authenticatie, ook chunked (contract §5); binnen de header-middleware hieronder.
    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def _headers(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'"
        )
        return response

    def link_status() -> dict[str, Any]:
        return public_status(store.read())

    def status() -> dict[str, Any]:
        link = link_status()
        linked = link["state"] == "gekoppeld"
        return {
            "app": APP_ID,
            "versie": __version__,
            "gekoppeld": linked,
            "koppeling": link,
            "toelichting": "Gekoppeld met de Hub. De TrueNAS-API-key met schrijfrechten en de allowlist volgen in "
            "fase P2; tot die tijd voert de executor niets uit."
            if linked
            else "Nog niet gekoppeld. Koppel met een koppelcode (30 min) en de vingerafdruk uit de Hub-UI. De "
            "TrueNAS-API-key met schrijfrechten volgt in fase P2; tot die tijd voert de executor niets uit.",
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
        link = link_status() if secrets_ok else {"state": "nooit_gekoppeld"}
        checks = [
            {"name": "geheimen", "status": "ok" if secrets_ok else "down"},
            {"name": "datamap", "status": "ok" if writable else "down"},
            {"name": "koppeling", "status": str(link["state"])},
        ]
        ok = secrets_ok and writable
        return JSONResponse(
            {"status": "ready" if ok else "not_ready", "gekoppeld": link["state"] == "gekoppeld", "checks": checks},
            status_code=200 if ok else 503,
        )

    @app.get("/api/v1/status", tags=["status"], summary="Koppelstatus (witte lijst) en (lege) allowlist")
    def api_status() -> dict[str, Any]:
        return status()

    def _hub_auth(request: Request) -> dict[str, Any] | JSONResponse:
        auth = request.headers.get("authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        if not token:
            return _err("unauthorized", "Niet aangemeld.", 401, {"reason": "invalid_token"})
        try:
            return verify_hub_jwt(token, store.read(), audience=APP_ID)
        except AuthFailed as exc:
            if exc.reason == "unknown_key":
                rotations.trigger_background()
            return _err("unauthorized", AUTH_MESSAGES[exc.reason], 401, {"reason": exc.reason})

    @app.get(
        "/connector/v1/hub-link",
        tags=["connector"],
        summary="Koppelstatus (witte lijst §3.5 + gepinde kid's); dienst-JWT of gebruikers-JWT viewer+",
    )
    def hub_link(request: Request) -> JSONResponse:
        claims = _hub_auth(request)
        if isinstance(claims, JSONResponse):
            return claims
        if claims.get("token_use") == "user" and user_rank(claims) < ROLE_RANK["viewer"]:
            return _err("forbidden", "Hiervoor is minimaal de rol 'viewer' nodig.", 403)
        link = store.read()
        pins = link.get("pins") or {}
        return JSONResponse(
            {
                **public_status(link),
                "pinned_kids": {
                    "jwt": [p["kid"] for p in pins.get("jwt", [])],
                    "policy": [p["kid"] for p in pins.get("policy", [])],
                },
                "rotation_sequence": pins.get("rotation_sequence", 0),
            }
        )

    def _mutation_guard(request: Request, claims: dict[str, Any]) -> tuple[str, JSONResponse | None]:
        """Mutatie met een Hub-JWT: ``Idempotency-Key`` verplicht, daarna de jti-replaycontrole (§4.6, fail-closed)."""
        key = request.headers.get("idempotency-key", "")
        if not key:
            return key, _err("idempotency_key_required", "Header Idempotency-Key (UUID) is verplicht.", 400)
        try:
            key = str(uuid.UUID(key))
        except ValueError:
            return key, _err("idempotency_key_invalid", "Idempotency-Key moet een UUID zijn.", 400)
        try:
            claim = replays.claim(
                iss=str(claims["iss"]),
                jti=str(claims["jti"]),
                exp=int(claims["exp"]),
                method=request.method,
                path=request.url.path,
                idempotency_key=key,
            )
        except ReplayUnavailable:
            return key, _err(
                "replay_check_unavailable",
                "De replaycontrole is niet beschikbaar; er is niets uitgevoerd. Controleer de opslag in /appdata.",
                503,
            )
        if claim.kind == "replayed":
            return key, _err("unauthorized", AUTH_MESSAGES["token_replayed"], 401, {"reason": "token_replayed"})
        if claim.kind == "in_progress":
            return key, _err("idempotency_in_progress", "Een verzoek met dit token en deze sleutel loopt al.", 409)
        if claim.kind == "repeat":
            status = claim.status or 500
            return key, JSONResponse(claim.body, status_code=status, headers={"Idempotent-Replay": "true"})
        return key, None

    @app.post(
        "/connector/v1/hub-link/unlink",
        tags=["connector"],
        status_code=501,
        summary="Ontkoppelen: nog niet beschikbaar voor de executor (vraagt een live geverifieerde schrijfkey, P2)",
        responses={
            400: {"description": "Idempotency-Key ontbreekt of is geen UUID"},
            401: {"description": "unauthorized (reden §4.7, ook token_replayed)"},
            403: {"description": "gebruikers-JWT zonder rol admin"},
            501: {"description": "capability_unavailable"},
            503: {"description": "replay_check_unavailable"},
        },
    )
    def hub_link_unlink(request: Request) -> JSONResponse:
        claims = _hub_auth(request)
        if isinstance(claims, JSONResponse):
            return claims
        if claims.get("token_use") == "user" and user_rank(claims) < ROLE_RANK["admin"]:
            return _err("forbidden", "Ontkoppelen vraagt de rol 'admin' (of een dienst-JWT van de Hub).", 403)
        _, refused = _mutation_guard(request, claims)
        if refused is not None:
            return refused
        body = _err_body(
            "capability_unavailable",
            "Ontkoppelen van de executor vraagt een live geverifieerde TrueNAS-schrijfkey tegen het vastgelegde "
            "NAS-adres (contract §3.9); dat volgt in fase P2. Er is niets ontkoppeld.",
        )
        # Er is niets uitgevoerd; lukt vastleggen niet, dan krijgt een herhaling 409 (loopt nog) i.p.v. dit antwoord.
        with contextlib.suppress(ReplayUnavailable):
            replays.store_result(iss=str(claims["iss"]), jti=str(claims["jti"]), status=501, body=body)
        return JSONResponse(body, status_code=501)

    @app.post(
        "/api/v1/execute",
        tags=["uitvoeren"],
        status_code=403,
        summary="Weigert alles (allowlist leeg tot P2)",
        responses={403: {"description": "Actie geweigerd"}},
    )
    def execute(body: ExecuteIn) -> JSONResponse:
        verdict = check(body.action_id)
        return _err(
            verdict.code,
            verdict.message,
            403,
            {"action_id": body.action_id, "gekoppeld": link_status()["state"] == "gekoppeld"},
        )

    def _page(
        message: str | None = None,
        *,
        error: bool = False,
        status_code: int = 200,
        veld: dict[str, str] | None = None,
    ) -> HTMLResponse:
        """Statuspagina in het Peil-sjabloon (C-55). ``message`` komt altijd uit vaste teksten, nooit uit invoer."""
        link = link_status()
        show_form = not link.get("first_linked_at")
        csrf = secrets.token_urlsafe(32) if show_form else ""
        last = link.get("last_error")
        melding: dict[str, str] | None = None
        if message:
            melding = {
                "toon": "fout" if error else "info",
                "titel": "Koppelen is mislukt" if error else message.split(".")[0] + ".",
                "tekst": message if error else "Controleer dat de vingerafdruk hieronder gelijk is aan de Hub-UI.",
            }
        elif last:
            melding = {
                "toon": "fout",
                "titel": "Laatste koppelpoging mislukt",
                "tekst": str(last.get("melding") or last.get("code")),
            }
        secrets_ok = all((settings.secrets_dir / n).exists() for n in (IDENTITY, VAULT_KEY))
        ready = [
            {"name": "geheimen", "status": "ok" if secrets_ok else "down"},
            {"name": "datamap", "status": "ok" if os.access(settings.data_dir, os.W_OK) else "down"},
        ]
        html = executor_page(
            versie=__version__, link=link, ready_checks=ready, csrf=csrf, melding=melding, veldfout=veld
        )
        resp = HTMLResponse(html, status_code=status_code)
        if csrf:
            resp.set_cookie(CSRF_COOKIE, csrf, httponly=True, samesite="strict", path="/", max_age=3600)
        return resp

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def page() -> HTMLResponse:
        return _page()

    @app.post("/koppelen", response_class=HTMLResponse, include_in_schema=False)
    async def pair(request: Request) -> HTMLResponse:
        ip = request.client.host if request.client else "onbekend"
        host = request.headers.get("host", "")
        origin = request.headers.get("origin", "")
        if origin not in (f"http://{host}", f"https://{host}"):
            return _page("Geweigerd: het formulier komt niet van deze pagina.", error=True, status_code=403)
        raw = await request.body()
        if len(raw) > MAX_FORM_BYTES:
            return _page("Het formulier is te groot.", error=True, status_code=413)
        form = {k: v[0] for k, v in parse_qs(raw.decode(errors="replace"), max_num_fields=8).items() if v}
        cookie = request.cookies.get(CSRF_COOKIE, "")
        if not cookie or not hmac.compare_digest(cookie, form.get("csrf", "")):
            return _page("Geweigerd: de formuliercode klopt niet. Laad de pagina opnieuw.", error=True, status_code=403)
        if store.read().get("first_linked_at"):
            return _page("Deze executor is al eens gekoppeld; opnieuw koppelen gaat via de Hub.", error=True,
                         status_code=409)  # fmt: skip
        if not throttle.allow(ip):
            return _page("Te veel pogingen; probeer het over een kwartier opnieuw.", error=True, status_code=429)
        # Veldnamen van het Peil-sjabloon (hub_adres, hub_vingerafdruk); de oude namen blijven geldig.
        code = form.get("koppelcode", "")
        fingerprint = form.get("hub_vingerafdruk") or form.get("vingerafdruk", "")
        try:
            hub_url = validate_hub_url(
                form.get("hub_adres") or form.get("hub_url", ""), allow_loopback=settings.allow_loopback_hub
            )
        except ValueError:
            msg = "Het Hub-adres is ongeldig: alleen http(s)://adres[:poort]."
            return _page(msg, error=True, status_code=422, veld={"hub_adres": msg})
        bad: dict[str, str] = {}
        if not valid_pairing_code(code):
            bad["koppelcode"] = "Koppelcode: 12 tekens in groepen van 4 (XXXX-XXXX-XXXX)."
        if not valid_fingerprint(fingerprint):
            bad["vingerafdruk"] = "Vingerafdruk: 16 tekens in groepen van 4 (XXXX-XXXX-XXXX-XXXX)."
        if bad:
            return _page("Koppelcode (12 tekens) of vingerafdruk (16 tekens) heeft niet het juiste formaat.",
                         error=True, status_code=422, veld=bad)  # fmt: skip
        identity = public_jwk(settings.secrets_dir)
        if identity is None:
            return _page("De eigen sleutel ontbreekt; herstart de executor.", error=True, status_code=503)
        try:
            # Blokkerende HTTP-aanroep (max. 5 s + 15 s) buiten de event loop.
            result = await run_in_threadpool(
                enroll_with_pairing_code,
                store,
                app_id=APP_ID,
                version=__version__,
                identity_jwk=identity,
                hub_url=hub_url,
                pairing_code=code,
                fingerprint=fingerprint,
            )
        except EnrollFailed:
            return _page("Deze executor is al eens gekoppeld; opnieuw koppelen gaat via de Hub.", error=True,
                         status_code=409)  # fmt: skip
        if result["state"] == "gekoppeld":
            return _page("Gekoppeld met de Hub. Controleer dat de vingerafdruk hierboven gelijk is aan de Hub-UI.")
        err = result.get("last_error") or {}
        code_err = str(err.get("code"))
        text = ERRORS_NL.get(code_err, "Koppelen mislukt.")
        field = {
            "hub_vingerafdruk_onjuist": "vingerafdruk",
            "hub_weigerde": "koppelcode",
            "hub_onbereikbaar": "hub_adres",
        }
        return _page(text, error=True, status_code=400, veld={field[code_err]: text} if code_err in field else None)

    return app
