"""HTTP-API van de executor: gezondheid, statuspagina met koppelen (contract 1.3 §3.7, §3.9) en een uitvoer-endpoint dat
alles weigert (allowlist leeg tot P2).

Koppelen kan alleen op de statuspagina, met een koppelcode (30 min) en de Hub-vingerafdruk, zolang de executor nog nooit
gekoppeld is en het koppelbestand leesbaar is. Elke formulier-POST doorloopt eerst de herkomstcontrole (exacte
``Origin`` met het schema van het verzoek, ``Sec-Fetch-Site``, ``Host``-beperking tegen DNS-rebinding,
formuliertoken) en telt daarna als poging. De TrueNAS-schrijfkey (en daarmee ontkoppelen/opnieuw koppelen op deze
pagina) volgt in P2: tot dan geeft dat ``capability_unavailable``, nooit gesimuleerd succes.

Hub-JWT's (§4.7): eerst de authenticatie (state → tokensoort → handtekening/kid → claims → token_use → jti, die bij
**elke** POST/PUT/PATCH/DELETE wordt verbruikt), daarna pas rol (403), ``Idempotency-Key`` (400) en de body (422).
"""

from __future__ import annotations

import contextlib
import hmac
import logging
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
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from executor import APP_ID, __version__
from executor.adres import AdresOngeldig, host_allowed_for_post
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
    pending_expired,
    public_status,
    resume_after_restart,
    valid_fingerprint,
    valid_pairing_code,
    validate_hub_url,
    verify_hub_authorization,
)
from executor.replay import ReplayCache, ReplayUnavailable
from executor.statuspagina import executor_page, onleesbaar_melding

CSRF_COOKIE = "executor_csrf"
MAX_FORM_BYTES = 4096
MAX_FORM_FIELDS = 8  # het formulier heeft er 4 (csrf, hub_adres, koppelcode, hub_vingerafdruk)
MUTATIONS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Invoerlimieten van §3.7 (als geheel controleren, nooit eerst afkappen).
MAX_HUB_ADRES, MAX_KOPPELCODE, MAX_VINGERAFDRUK = 512, 32, 64
log = logging.getLogger("executor.koppelen")
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
    """Vorm volgt later ``ExecutionRequest`` (contract §8); tot P2 wordt alleen ``action_id`` gelezen om te weigeren."""

    model_config = ConfigDict(extra="allow")
    action_id: str = Field(min_length=1, max_length=128)


def _err_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details or {}, "trace_id": str(uuid.uuid4())}


def _err(code: str, message: str, status: int, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(_err_body(code, message, details), status_code=status)


# Vaste meldingen van het koppelformulier (§3.7): code → (HTTP-status, titel, tekst). Nooit weerspiegelde invoer.
FORM_MESSAGES: dict[str, tuple[int, str, str]] = {
    "herkomst_onjuist": (
        403,
        "Geweigerd",
        "Geweigerd: het formulier komt niet van deze pagina. Laad de pagina opnieuw.",
    ),
    "formuliercode_onjuist": (403, "Geweigerd", "Geweigerd: de formuliercode klopt niet. Laad de pagina opnieuw."),
    "host_niet_toegestaan": (403, "Geweigerd", "Open deze pagina via het IP-adres van de NAS, of koppel via de Hub."),
    "formulier_te_groot": (413, "Geweigerd", "Het formulier is te groot."),
    "rate_limited": (429, "Te veel pogingen", "Te veel pogingen; probeer het over een kwartier opnieuw."),
    "koppelstatus_onleesbaar": (409, "Koppelen kan niet", ERRORS_NL["koppelstatus_onleesbaar"]),
    "al_gekoppeld": (409, "Koppelen kan niet", "Deze executor is al eens gekoppeld; opnieuw koppelen gaat via de Hub."),
    "koppelen_bezig": (409, "Koppelen bezig", "Er loopt al een koppelpoging. Laad de pagina over een minuut opnieuw."),
    "validation_error": (422, "Koppelen is mislukt", "Een of meer velden zijn niet goed ingevuld; zie de velden."),
    "sleutel_ontbreekt": (503, "Koppelen is mislukt", "De eigen sleutel ontbreekt; herstart de executor."),
}
VELD_BIJ_FOUT = {
    "hub_vingerafdruk_onjuist": "vingerafdruk",
    "hub_weigerde": "koppelcode",
    "hub_onbereikbaar": "hub_adres",
}


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
    store = HubLinkStore(settings.secrets_dir, allow_loopback=settings.allow_loopback_hub)
    rotations = KeyRotationPoller(store)
    replays = ReplayCache(settings.replay_db)
    stop = threading.Event()

    def poll_loop() -> None:
        while not stop.wait(15 * 60):  # contract §4.5: hooguit elke 15 minuten
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
        "vingerafdruk, contract 1.3 §3.9). De allowlist is leeg tot P2: elke actie wordt geweigerd. Geen shell, sudo "
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
        # same-origin, nooit no-referrer: met no-referrer stuurt elke browser bij het POST-formulier `Origin: null`,
        # waardoor de exacte Origin-controle koppelen altijd zou weigeren (contract 1.3 §3.7 punt 1).
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'"
        )
        return response

    def link_status() -> dict[str, Any]:
        return public_status(store.read())

    def ready_checks() -> list[dict[str, str]]:
        secrets_ok = all((settings.secrets_dir / n).exists() for n in (IDENTITY, VAULT_KEY))
        writable = os.access(settings.data_dir, os.W_OK)
        return [
            {"name": "geheimen", "status": "ok" if secrets_ok else "down"},
            {"name": "datamap", "status": "ok" if writable else "down"},
        ]

    def status() -> dict[str, Any]:
        raw = store.read()
        link = public_status(raw)
        linked = link["state"] == "gekoppeld"
        ready_ok = all(c["status"] == "ok" for c in ready_checks())
        return {
            "app": APP_ID,
            "versie": __version__,
            "gekoppeld": linked,
            # Contract 1.3 §3.7: Gereed = /readyz in orde én gekoppeld en bevestigd.
            "gereed": ready_ok and linked and bool(raw.get("confirmed_at")),
            "koppeling": link,
            "toelichting": "Gekoppeld met de Hub. De TrueNAS-API-key met schrijfrechten en de allowlist volgen in "
            "fase P2; tot die tijd voert de executor niets uit."
            if linked
            else "De koppelstatus is onleesbaar: de executor vertrouwt de Hub niet en voert niets uit."
            if raw.get("_onleesbaar")
            else "Nog niet gekoppeld. Koppel met een koppelcode (30 min) en de vingerafdruk uit de Hub-UI. De "
            "TrueNAS-API-key met schrijfrechten volgt in fase P2; tot die tijd voert de executor niets uit.",
            "allowlist": sorted(ALLOWLIST),
            "identiteit": public_jwk(settings.secrets_dir),
        }

    @app.get("/healthz", tags=["gezondheid"], summary="Proces leeft")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "app": APP_ID, "version": __version__}

    @app.get(
        "/readyz",
        tags=["gezondheid"],
        summary="Eigen geheimen aanwezig en datamap beschrijfbaar (de koppeling telt niet mee, contract §5)",
    )
    def readyz() -> JSONResponse:
        checks = ready_checks()
        ok = all(c["status"] == "ok" for c in checks)
        link: dict[str, Any] = (
            link_status() if checks[0]["status"] == "ok" else {"state": "nooit_gekoppeld", "last_error": None}
        )
        err: dict[str, Any] = link.get("last_error") or {}
        details: list[dict[str, Any]] = [
            *checks,
            {"name": "koppeling", "status": str(link["state"] or "onleesbaar"), "code": err.get("code")},
        ]
        return JSONResponse(
            {"status": "ready" if ok else "not_ready", "gekoppeld": link["state"] == "gekoppeld", "checks": details},
            status_code=200 if ok else 503,
        )

    @app.get("/api/v1/status", tags=["status"], summary="Koppelstatus (witte lijst), Gereed en (lege) allowlist")
    def api_status() -> dict[str, Any]:
        return status()

    def _authenticate(request: Request) -> dict[str, Any] | JSONResponse:
        """§4.7: state → tokensoort → handtekening/kid → claims → token_use → jti. Bij een mutatie wordt de ``jti``
        altijd verbruikt (ook zonder ``Idempotency-Key``); pas daarna komen rol, ``Idempotency-Key`` en body."""
        try:
            claims = verify_hub_authorization(request.headers.get("authorization"), store.read(), audience=APP_ID)
        except AuthFailed as exc:
            if exc.reason == "unknown_key":
                rotations.trigger_background()
            return _err("unauthorized", AUTH_MESSAGES[exc.reason], 401, {"reason": exc.reason})
        if request.method not in MUTATIONS:
            return claims
        raw_key = request.headers.get("idempotency-key", "")
        try:
            key = str(uuid.UUID(raw_key)) if raw_key else ""
        except ValueError:
            key = ""  # zonder geldige sleutel bestaat geen exacte herhaling (§4.6)
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
            return _err(
                "replay_check_unavailable",
                "De replaycontrole is niet beschikbaar; er is niets uitgevoerd. Controleer de opslag in /appdata.",
                503,
            )
        if claim.kind == "replayed" or (claim.kind != "new" and not key):
            return _err("unauthorized", AUTH_MESSAGES["token_replayed"], 401, {"reason": "token_replayed"})
        if claim.kind == "in_progress":
            return _err("idempotency_in_progress", "Een verzoek met dit token en deze sleutel loopt al.", 409)
        if claim.kind == "repeat":
            return JSONResponse(claim.body, status_code=claim.status or 500, headers={"Idempotent-Replay": "true"})
        return claims

    def _finish(claims: dict[str, Any], status_code: int, body: dict[str, Any]) -> JSONResponse:
        """Uitkomst van een mutatie vastleggen bij de verbruikte ``jti`` (exacte herhaling → zelfde antwoord)."""
        # Lukt vastleggen niet, dan krijgt een herhaling 409 (loopt nog) i.p.v. dit antwoord; er is niets uitgevoerd.
        with contextlib.suppress(ReplayUnavailable):
            replays.store_result(iss=str(claims["iss"]), jti=str(claims["jti"]), status=status_code, body=body)
        return JSONResponse(body, status_code=status_code)

    def _idempotency_key(request: Request) -> tuple[int, dict[str, Any]] | None:
        key = request.headers.get("idempotency-key", "")
        if not key:
            return 400, _err_body("idempotency_key_required", "Header Idempotency-Key (UUID) is verplicht.")
        try:
            uuid.UUID(key)
        except ValueError:
            return 400, _err_body("idempotency_key_invalid", "Idempotency-Key moet een UUID zijn.")
        return None

    @app.get(
        "/connector/v1/hub-link",
        tags=["connector"],
        summary="Koppelstatus (witte lijst §3.5 + gepinde kid's); dienst-JWT of gebruikers-JWT viewer+",
    )
    def hub_link(request: Request) -> JSONResponse:
        claims = _authenticate(request)
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

    @app.post(
        "/connector/v1/hub-link/unlink",
        tags=["connector"],
        status_code=501,
        summary="Ontkoppelen: nog niet beschikbaar voor de executor (vraagt een live geverifieerde schrijfkey, P2)",
        responses={
            400: {"description": "Idempotency-Key ontbreekt of is geen UUID (pas na de authenticatie)"},
            401: {"description": "unauthorized (reden §4.7, ook token_replayed)"},
            403: {"description": "gebruikers-JWT zonder rol admin"},
            501: {"description": "capability_unavailable"},
            503: {"description": "replay_check_unavailable"},
        },
    )
    def hub_link_unlink(request: Request) -> JSONResponse:
        claims = _authenticate(request)
        if isinstance(claims, JSONResponse):
            return claims
        if claims.get("token_use") == "user" and user_rank(claims) < ROLE_RANK["admin"]:
            return _finish(
                claims, 403, _err_body("forbidden", "Ontkoppelen vraagt de rol 'admin' (of een dienst-JWT van de Hub).")
            )
        if (missing := _idempotency_key(request)) is not None:
            return _finish(claims, *missing)
        return _finish(
            claims,
            501,
            _err_body(
                "capability_unavailable",
                "Ontkoppelen van de executor vraagt een live geverifieerde TrueNAS-schrijfkey tegen het vastgelegde "
                "NAS-adres (contract §3.9); dat volgt in fase P2. Er is niets ontkoppeld.",
            ),
        )

    @app.post(
        "/api/v1/execute",
        tags=["uitvoeren"],
        status_code=403,
        summary="Weigert alles (allowlist leeg tot P2); eerst authenticatie met een dienst-JWT van de Hub",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": ExecuteIn.model_json_schema()}},
            }
        },
        responses={
            400: {"description": "Idempotency-Key ontbreekt of is geen UUID (pas na de authenticatie)"},
            401: {"description": "unauthorized (§4.7): zonder geldige aanmelding altijd 401, ook bij een foute body"},
            403: {"description": "Actie geweigerd (allowlist leeg), of geen dienst-JWT van de Hub"},
            422: {"description": "validation_error (pas na de authenticatie)"},
        },
    )
    async def execute(request: Request) -> JSONResponse:
        claims = await run_in_threadpool(_authenticate, request)
        if isinstance(claims, JSONResponse):
            return claims
        if claims.get("token_use") != "hub_service":
            return _finish(claims, 403, _err_body("forbidden", "Alleen de Hub (dienst-JWT) kan acties aanbieden."))
        if (missing := _idempotency_key(request)) is not None:
            return _finish(claims, *missing)
        try:
            body = ExecuteIn.model_validate_json(await request.body())
        except ValidationError as exc:
            fouten = [{"veld": ".".join(str(p) for p in e["loc"]), "fout": e["msg"]} for e in exc.errors()]
            return _finish(claims, 422, _err_body("validation_error", "De invoer is ongeldig.", {"fouten": fouten}))
        verdict = check(body.action_id)
        return _finish(
            claims,
            403,
            _err_body(verdict.code, verdict.message, {"action_id": body.action_id, "gekoppeld": True}),
        )

    def _page(
        melding: dict[str, str] | None = None,
        *,
        status_code: int = 200,
        veld: dict[str, str] | None = None,
    ) -> HTMLResponse:
        """Statuspagina in het Peil-sjabloon 1.1.1 (C-55). Meldingen komen altijd uit vaste teksten, nooit uit invoer.
        Zonder ``melding`` van dít verzoek: een bestaande toestand (onleesbaar, laatste fout) zonder live-rol."""
        raw = store.read()
        show_form = not raw.get("_onleesbaar") and not raw.get("first_linked_at") and raw.get("pending") is None
        csrf = secrets.token_urlsafe(32) if show_form else ""
        if melding is None:
            if raw.get("_onleesbaar"):
                melding = onleesbaar_melding()
            elif (last := (public_status(raw).get("last_error") or {})).get("code"):
                melding = {
                    "toon": "fout",
                    "rol": "",
                    "titel": "Laatste koppelpoging mislukt",
                    "tekst": str(last.get("melding") or "Koppelen is mislukt."),
                    "code": str(last.get("code")),
                }
        html = executor_page(
            versie=__version__, link=raw, ready_checks=ready_checks(), csrf=csrf, melding=melding, veldfout=veld
        )
        resp = HTMLResponse(html, status_code=status_code)
        if csrf:
            resp.set_cookie(CSRF_COOKIE, csrf, httponly=True, samesite="strict", path="/", max_age=3600)
        return resp

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def page() -> HTMLResponse:
        return _page()

    def _afgehandeld(code: str, trace: str, *, veld: dict[str, str] | None = None) -> HTMLResponse:
        """Eén logregel per afgehandelde poging (code + trace-ID; nooit het Hub-adres van een mislukte poging of een
        geheim), en de vaste melding van dít verzoek (rol ``alert``, code + trace-ID)."""
        log.info("koppelpoging afgehandeld: code=%s trace_id=%s", code, trace)
        status_code, titel, tekst = FORM_MESSAGES[code]
        melding = {"toon": "fout", "rol": "alert", "titel": titel, "tekst": tekst, "code": code, "trace_id": trace}
        return _page(melding, status_code=status_code, veld=veld)

    def _herkomst(request: Request) -> str | None:
        """§3.7 punten 1–5: exacte ``Origin`` (= ``<schema>://<Host>`` van dít verzoek; ontbreekt of ``null`` → 403),
        ``Sec-Fetch-Site`` alleen ``same-origin``/``none`` en de ``Host``-beperking tegen DNS-rebinding."""
        host = request.headers.get("host", "")
        origin = request.headers.get("origin", "")
        if not origin or origin == "null" or origin != f"{request.url.scheme}://{host}":
            return "herkomst_onjuist"
        site = request.headers.get("sec-fetch-site")
        if site is not None and site not in ("same-origin", "none"):
            return "herkomst_onjuist"
        if not host_allowed_for_post(host):
            return "host_niet_toegestaan"
        return None

    @app.post("/koppelen", response_class=HTMLResponse, include_in_schema=False)
    async def pair(request: Request) -> HTMLResponse:
        trace = str(uuid.uuid4())
        # 1. Herkomst (een geweigerd verzoek gaat niet naar de Hub, telt niet als poging en verandert niets).
        if (refused := _herkomst(request)) is not None:
            return _afgehandeld(refused, trace)
        raw_body = await request.body()
        if len(raw_body) > MAX_FORM_BYTES:
            return _afgehandeld("formulier_te_groot", trace)
        try:
            fields = parse_qs(raw_body.decode(errors="replace"), max_num_fields=MAX_FORM_FIELDS)
        except ValueError:  # meer velden dan het formulier heeft: vaste melding, nooit een kale 500
            return _afgehandeld("formulier_te_groot", trace)
        form = {k: v[0] for k, v in fields.items() if v}
        cookie = request.cookies.get(CSRF_COOKIE, "")
        if not cookie or not hmac.compare_digest(cookie.encode(), form.get("csrf", "").encode()):
            return _afgehandeld("formuliercode_onjuist", trace)
        # 2. Elke POST die de herkomstcontrole doorstaat, telt als poging: ook bij ongeldige invoer, een lopende poging,
        #    een onleesbaar koppelbestand of een executor die al eens gekoppeld is (§3.7, RV7).
        ip = request.client.host if request.client else "onbekend"
        if not throttle.allow(ip):
            return _afgehandeld("rate_limited", trace)
        link = store.read()
        if link.get("_onleesbaar"):
            return _afgehandeld("koppelstatus_onleesbaar", trace)
        if link.get("first_linked_at"):
            return _afgehandeld("al_gekoppeld", trace)
        if link.get("pending") is not None and not pending_expired(link):
            return _afgehandeld("koppelen_bezig", trace)
        # 3. Invoer als geheel controleren, nooit eerst afkappen (§3.7). Veldnamen van het Peil-sjabloon.
        code = form.get("koppelcode", "")
        fingerprint = form.get("hub_vingerafdruk") or form.get("vingerafdruk", "")
        hub_input = form.get("hub_adres") or form.get("hub_url", "")
        bad: dict[str, str] = {}
        hub_url = ""
        try:
            hub_url = validate_hub_url(hub_input, allow_loopback=settings.allow_loopback_hub)
        except AdresOngeldig:
            bad["hub_adres"] = (
                f"Adres van de Hub: alleen http(s)://IP-adres-of-naam[:poort], hooguit {MAX_HUB_ADRES} tekens; "
                "IPv4 als a.b.c.d, IPv6 tussen [ ]."
            )
        if len(code) > MAX_KOPPELCODE or not valid_pairing_code(code):
            bad["koppelcode"] = "Koppelcode: 12 tekens in groepen van 4 (XXXX-XXXX-XXXX)."
        if len(fingerprint) > MAX_VINGERAFDRUK or not valid_fingerprint(fingerprint):
            bad["vingerafdruk"] = "Vingerafdruk: 16 tekens in groepen van 4 (XXXX-XXXX-XXXX-XXXX)."
        if bad:
            return _afgehandeld("validation_error", trace, veld=bad)
        identity = public_jwk(settings.secrets_dir)
        if identity is None:
            return _afgehandeld("sleutel_ontbreekt", trace)
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
        except EnrollFailed as exc:  # tussen controle en vergrendeling veranderd: niets naar de Hub gestuurd
            return _afgehandeld(exc.code if exc.code in FORM_MESSAGES else "al_gekoppeld", trace)
        if result["state"] == "gekoppeld":
            log.info("koppelpoging afgehandeld: code=gekoppeld trace_id=%s", trace)
            return _page(
                {
                    "toon": "info",
                    "rol": "status",
                    "titel": "Gekoppeld met de Hub.",
                    "tekst": "Controleer dat de vingerafdruk hieronder gelijk is aan de Hub-UI.",
                }
            )
        code_err = str((result.get("last_error") or {}).get("code") or "hub_antwoord_ongeldig")
        log.info("koppelpoging afgehandeld: code=%s trace_id=%s", code_err, trace)
        text = ERRORS_NL.get(code_err, "Koppelen mislukt.")
        field = VELD_BIJ_FOUT.get(code_err)
        return _page(
            {
                "toon": "fout",
                "rol": "alert",
                "titel": "Koppelen is mislukt",
                "tekst": text,
                "code": code_err,
                "trace_id": trace,
            },
            status_code=400,
            veld={field: text} if field else None,
        )

    return app
