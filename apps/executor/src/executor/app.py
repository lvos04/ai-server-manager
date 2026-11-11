"""HTTP-API van de executor: gezondheid, statuspagina (koppelen, TrueNAS-schrijfsleutel, beheer; contract 1.3 §3.7,
§3.9) en het uitvoer-endpoint voor ondertekende ``ExecutionRequest``-berichten (§8, ADR-0030).

Koppelen kan alleen op de statuspagina, met een koppelcode (30 min) en de Hub-vingerafdruk, zolang de executor nog nooit
gekoppeld is en het koppelbestand leesbaar is. Daarna vult de beheerder op dezelfde pagina de TrueNAS-API-sleutel met
schrijfrechten in (``/schrijfsleutel``, in twee stappen: eerst de TLS-vingerafdruk van TrueNAS tonen en laten
bevestigen, dan pas de sleutel live testen en versleuteld opslaan). Ontkoppelen, de sleutel vervangen en een gestopte
executor vrijgeven kan alleen met een live geverifieerde schrijfsleutel tegen het vastgelegde NAS-adres en certificaat
(``/beheer``). **Elke** formulier-POST doorloopt eerst de herkomstcontrole (exacte ``Origin`` met het schema van het
verzoek, ``Sec-Fetch-Site``, ``Host``-beperking tegen DNS-rebinding, formuliertoken) en telt daarna als poging.

Uitvoeren (``/api/v1/execute``): alleen met een dienst-JWT van de Hub én een ``ExecutionRequest`` dat de executor zelf
opnieuw controleert (handtekening met de gepinde policy-sleutel, geldigheid, nonce, allowlist, parameterschema,
``policy_hash``, risicoklasse, goedkeuring en precondities) — zie :mod:`executor.uitvoeren`. Geen vrije doorgeefroute,
geen shell, sudo of Docker.

Hub-JWT's (§4.7): eerst de authenticatie (state → tokensoort → handtekening/kid → claims → token_use → jti, die bij
**elke** POST/PUT/PATCH/DELETE wordt verbruikt), daarna pas rol (403), ``Idempotency-Key`` (400) en de body (422).
"""

from __future__ import annotations

import contextlib
import hmac
import json
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

from asm_policy import Policy, PolicyError, load_policy
from asm_policy.loader import default_policy_dir, is_read_only
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from executor import APP_ID, __version__
from executor.adres import AdresOngeldig, check_address, host_allowed_for_post, parse_host, split_host_header
from executor.bodylimit import BodyLimit
from executor.config import Settings, get_settings
from executor.firststart import IDENTITY, VAULT_KEY, public_jwk
from executor.hublink import (
    ERRORS_NL,
    AuthFailed,
    EnrollFailed,
    HubLinkStore,
    KeyRotationPoller,
    b64url_decode,
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
from executor.journal import Journal, JournalUnavailable
from executor.naslink import MAX_KEY_LEN, NasLinkOnleesbaar, NasLinkStore
from executor.replay import ReplayCache, ReplayUnavailable
from executor.statuspagina import executor_page, onleesbaar_melding, vingerafdruk_melding
from executor.truenas import NasFout, display_fingerprint, fetch_fingerprint, verify_key
from executor.uitvoeren import Uitvoerder

CSRF_COOKIE = "executor_csrf"
MAX_FORM_BYTES = 4096
MAX_FORM_FIELDS = 8  # de formulieren hebben er hooguit 4 (csrf + drie velden)
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


# Vorm van een ``ExecutionRequest`` (contract 1.3 §8) voor de OpenAPI; de executor controleert de inhoud zelf opnieuw
# (:mod:`asm_policy.verify`), dit schema is alleen documentatie.
EXECUTION_REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["proposal", "approval", "policy_decision", "issued_at", "expires_at", "nonce", "signature"],
    "additionalProperties": False,
    "properties": {
        "proposal": {"type": "object", "description": "ActionProposal (§8), ongewijzigd zoals beoordeeld door de Hub."},
        "approval": {
            "type": ["object", "null"],
            "description": "Gebonden goedkeuring (verplicht bij R2/R3): preview_hash, resource_etag, policy_hash, "
            "risk_class, expires_at (≤ 15 min), one_time_nonce, backup_checkpoint_id, action_scope.",
        },
        "policy_decision": {
            "type": "object",
            "required": ["risk_class", "rule_ids", "policy_hash"],
            "properties": {
                "risk_class": {"type": "string", "enum": ["R0", "R1", "R2", "R3"]},
                "rule_ids": {"type": "array", "items": {"type": "string"}},
                "policy_hash": {"type": "string"},
            },
        },
        "issued_at": {"type": "string", "format": "date-time"},
        "expires_at": {"type": "string", "format": "date-time"},
        "nonce": {"type": "string", "format": "uuid"},
        "signature": {"type": "string", "description": "Ed25519 over de canonieke JSON zonder dit veld (base64url)."},
    },
}


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
    # ---- TrueNAS-schrijfsleutel en beheer (§3.9); dezelfde regels als het koppelformulier.
    "niet_gekoppeld": (409, "Sleutel instellen kan niet", "Koppel de executor eerst met de Hub."),
    "sleutel_al_ingesteld": (
        409,
        "Sleutel instellen kan niet",
        "Er is al een schrijfsleutel ingesteld. Vervangen kan onder 'Ontkoppelen of sleutel vervangen'.",
    ),
    "geen_schrijfsleutel": (409, "Dit kan nog niet", "Er is nog geen TrueNAS-schrijfsleutel ingesteld."),
    "sleutelopslag_onleesbaar": (
        409,
        "De TrueNAS-koppeling is onleesbaar",
        "De executor kon zijn opgeslagen TrueNAS-koppeling niet lezen. Er is niets gewijzigd en hij voert niets uit.",
    ),
    "sleutel_ongeldig": (
        422,
        "De sleutel is niet goed ingevuld",
        f"Vul de TrueNAS-API-sleutel in: hooguit {MAX_KEY_LEN} tekens, zonder spaties. Er is niets gewijzigd.",
    ),
    "nieuwe_sleutel_ontbreekt": (
        422,
        "De nieuwe sleutel ontbreekt",
        "Vul bij 'Sleutel vervangen' ook de nieuwe sleutel in. Er is niets gewijzigd.",
    ),
    "actie_onbekend": (
        422,
        "Kies een actie",
        "Kies 'Sleutel vervangen' of 'Ontkoppelen van de Hub'. Er is niets gewijzigd.",
    ),
    "nas_adres_onbekend": (
        409,
        "Het adres van TrueNAS is onbekend",
        "De executor leidt het adres van TrueNAS af uit het adres van deze pagina. Open deze pagina via het IP-adres "
        "van de NAS, of stel EXECUTOR_TRUENAS_HOST in bij de Custom App. Er is niets opgeslagen.",
    ),
    "truenas_onbereikbaar": (
        502,
        "TrueNAS was niet bereikbaar",
        "TrueNAS was niet bereikbaar op het NAS-adres. Er is niets gewijzigd.",
    ),
    "truenas_timeout": (502, "TrueNAS was niet bereikbaar", "TrueNAS antwoordde niet op tijd. Er is niets gewijzigd."),
    "truenas_fout": (502, "TrueNAS gaf een fout", "TrueNAS gaf een fout bij het testen. Er is niets gewijzigd."),
    "truenas_geen_toegang": (
        400,
        "TrueNAS weigerde de sleutel",
        "TrueNAS gaf deze sleutel geen toegang. Er is niets gewijzigd.",
    ),
    "certificaat_gewijzigd": (
        409,
        "Het certificaat van TrueNAS is anders",
        "Het TLS-certificaat van TrueNAS is anders dan de vastgelegde vingerafdruk. De sleutel is niet verstuurd en "
        "er is niets gewijzigd.",
    ),
    "sleutel_geweigerd": (
        400,
        "TrueNAS weigerde de sleutel",
        "TrueNAS weigerde deze sleutel. Er is niets gewijzigd.",
    ),
    "schrijfrechten_ontbreken": (
        400,
        "De sleutel heeft geen schrijfrechten",
        "Deze sleutel is alleen-lezen. De executor heeft een TrueNAS-API-sleutel met schrijfrechten nodig. Er is "
        "niets gewijzigd.",
    ),
    "journaal_niet_beschikbaar": (
        503,
        "Het journaal is niet beschikbaar",
        "De executor kon zijn journaal niet lezen. Er is niets gewijzigd; controleer de opslag in /appdata.",
    ),
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
    journal = Journal(settings.replay_db, settings.secrets_dir)
    naslink = NasLinkStore(settings.secrets_dir)
    stop = threading.Event()
    # Het beleid is ingebakken in het image (read-only, contract 1.3 §8). Onleesbaar beleid = niets uitvoeren.
    policy: Policy | None
    try:
        policy = load_policy(default_policy_dir())
        policy_fout = ""
    except (PolicyError, OSError) as exc:
        policy, policy_fout = None, type(exc).__name__
    policy_read_only = policy is not None and is_read_only(policy.bron)
    uitvoerder = (
        Uitvoerder(
            policy=policy,
            journal=journal,
            naslink=naslink,
            settle_seconds=settings.readback_wait_seconds,
            poll_seconds=settings.readback_poll_seconds,
            timeout=settings.truenas_timeout_seconds,
        )
        if policy is not None
        else None
    )

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
        "vingerafdruk, contract 1.3 §3.9). Voert alleen acties van de allowlist uit het ingebakken beleid uit, en "
        "alleen met een door de Hub ondertekend ExecutionRequest dat de executor zelf opnieuw controleert (§8). Geen "
        "shell, sudo of Docker.",
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

    def gestopt() -> dict[str, Any] | None:
        """De toestand "gestopt na een afwijking"; een onleesbaar journaal telt als gestopt (fail-closed)."""
        try:
            return journal.stopped()
        except JournalUnavailable:
            return {"code": "journaal_niet_beschikbaar"}

    def policy_status() -> dict[str, Any]:
        return {
            "geladen": policy is not None,
            "hash": policy.hash if policy is not None else None,
            "read_only": policy_read_only,
            "fout": policy_fout or None,
        }

    def kan_uitvoeren() -> tuple[bool, str]:
        """Of de executor nu een geldig verzoek zou uitvoeren, met de reden waarom niet (voor status en pagina)."""
        raw = store.read()
        if raw.get("_onleesbaar"):
            return False, "koppelstatus_onleesbaar"
        if raw.get("state") != "gekoppeld":
            return False, "niet_gekoppeld"
        if policy is None:
            return False, "policy_niet_beschikbaar"
        if not policy_read_only and not settings.allow_writable_policy:
            return False, "policy_niet_read_only"
        nas = naslink.public()
        if nas.get("onleesbaar"):
            return False, "sleutelopslag_onleesbaar"
        if not nas.get("ingesteld"):
            return False, "schrijfsleutel_ontbreekt"
        if gestopt() is not None:
            return False, "executor_gestopt"
        return True, ""

    def status() -> dict[str, Any]:
        raw = store.read()
        link = public_status(raw)
        linked = link["state"] == "gekoppeld"
        ready_ok = all(c["status"] == "ok" for c in ready_checks())
        nas = naslink.public()
        stopped = gestopt()
        kan, waarom = kan_uitvoeren()
        if kan:
            toelichting = "Gekoppeld met de Hub; voert alleen ondertekende acties van de allowlist uit."
        elif raw.get("_onleesbaar"):
            toelichting = "De koppelstatus is onleesbaar: de executor vertrouwt de Hub niet en voert niets uit."
        elif not linked:
            toelichting = (
                "Nog niet gekoppeld. Koppel met een koppelcode (30 min) en de vingerafdruk uit de Hub-UI; vul daarna "
                "op de executorpagina de TrueNAS-API-sleutel met schrijfrechten in. Tot dan voert de executor niets "
                "uit."
            )
        elif waarom == "schrijfsleutel_ontbreekt":
            toelichting = (
                "Gekoppeld met de Hub. De TrueNAS-API-sleutel met schrijfrechten is nog niet ingesteld op de "
                "executorpagina; tot dan voert de executor niets uit."
            )
        elif waarom == "executor_gestopt":
            toelichting = (
                "Gestopt na een afwijking: de executor voert niets uit tot een beheerder hem op de executorpagina "
                "vrijgeeft met de TrueNAS-schrijfsleutel."
            )
        else:
            toelichting = "De executor voert niets uit; zie 'uitvoeren.reden'."
        return {
            "app": APP_ID,
            "versie": __version__,
            "gekoppeld": linked,
            # Contract 1.3 §3.7: Gereed = /readyz in orde én gekoppeld en bevestigd.
            "gereed": ready_ok and linked and bool(raw.get("confirmed_at")),
            "koppeling": link,
            "toelichting": toelichting,
            "uitvoeren": {"mogelijk": kan, "reden": waarom or None},
            "policy": policy_status(),
            "allowlist": policy.executor_allowlist() if policy is not None else [],
            # Nooit de sleutel zelf: alleen de laatste 4 tekens (§3.9).
            "schrijfsleutel": {
                "ingesteld": bool(nas.get("ingesteld")),
                "onleesbaar": bool(nas.get("onleesbaar")),
                "laatste4": nas.get("laatste4"),
                "ingesteld_op": nas.get("ingesteld_op"),
            },
            "truenas": {
                "adres": nas.get("nas_adres"),
                "poort": nas.get("nas_poort"),
                "tls_vingerafdruk": nas.get("tls_vingerafdruk"),
            },
            "gestopt": (
                {"sinds": stopped.get("at"), "reden": stopped.get("code"), "request_id": stopped.get("request_id")}
                if stopped is not None
                else None
            ),
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

    @app.get(
        "/api/v1/status",
        tags=["status"],
        summary="Koppelstatus (witte lijst), Gereed, beleid (policy_hash), allowlist en toestand van de schrijfsleutel",
    )
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
        summary="Ontkoppelen via de Hub kan niet: alleen op de executorpagina met een live geverifieerde schrijfkey",
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
                "NAS-adres (contract §3.9) en kan daarom alleen op de executorpagina, niet via de Hub. Er is niets "
                "ontkoppeld.",
            ),
        )

    def _policy_keys() -> list[Ed25519PublicKey]:
        """De bij het koppelen gepinde policy-sleutel(s) van de Hub (§4.5); alleen daarmee telt een handtekening."""
        keys: list[Ed25519PublicKey] = []
        for pin in (store.read().get("pins") or {}).get("policy") or []:
            try:
                keys.append(Ed25519PublicKey.from_public_bytes(b64url_decode(str(pin["jwk"]["x"]))))
            except (KeyError, TypeError, ValueError):
                continue
        return keys

    @app.post(
        "/api/v1/execute",
        tags=["uitvoeren"],
        summary="Ondertekend ExecutionRequest uitvoeren (dienst-JWT van de Hub; de executor controleert alles opnieuw)",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": EXECUTION_REQUEST_SCHEMA}},
            }
        },
        responses={
            200: {"description": "Uitgevoerd en teruggelezen: before/after-hash, nieuwe resource_etag en readback"},
            400: {"description": "Idempotency-Key ontbreekt of is geen UUID (pas na de authenticatie)"},
            401: {"description": "unauthorized (§4.7): zonder geldige aanmelding altijd 401, ook bij een foute body"},
            403: {
                "description": "Geen dienst-JWT van de Hub, of het verzoek is geweigerd: handtekening_ongeldig, "
                "verzoek_verlopen, actie_geweigerd, actie_niet_toegestaan, risicoklasse_te_laag, "
                "goedkeuring_ontbreekt, goedkeuring_verlopen, goedkeuring_ongeldig"
            },
            409: {
                "description": "Niets uitgevoerd: policy_hash_verschilt, nonce_al_gebruikt, goedkeuring_al_gebruikt, "
                "goedkeuring_past_niet, doel_gewijzigd, doel_bestaat_niet, doel_bestaat_al, doel_past_niet, "
                "pool_niet_gezond, backup_checkpoint_ontbreekt, herstelpunt_onbekend, executor_bezet, "
                "executor_gestopt. Of ná de aanroep: afwijking (readback wijkt af; de executor is gestopt)"
            },
            422: {"description": "validation_error, execution_request_ongeldig of parameters_ongeldig"},
            501: {"description": "capability_unavailable (geen schrijfsleutel, of TrueNAS kent de methode niet)"},
            502: {"description": "uitvoering_mislukt of truenas_fout (de toestand is onveranderd teruggelezen)"},
            503: {
                "description": "replay_check_unavailable, journaal_niet_beschikbaar, policy_niet_beschikbaar, "
                "policy_niet_read_only, schrijfsleutel_onleesbaar of TrueNAS onbereikbaar (niets uitgevoerd)"
            },
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
            body = json.loads(await request.body())
        except ValueError:
            body = None
        if not isinstance(body, dict):
            return _finish(
                claims,
                422,
                _err_body("validation_error", "De invoer is ongeldig: verwacht een ExecutionRequest (JSON-object)."),
            )
        if uitvoerder is None:
            return _finish(
                claims,
                503,
                _err_body(
                    "policy_niet_beschikbaar",
                    "Het risicobeleid van de executor is niet leesbaar; er is niets uitgevoerd.",
                ),
            )
        if not policy_read_only and not settings.allow_writable_policy:
            return _finish(
                claims,
                503,
                _err_body(
                    "policy_niet_read_only",
                    "Het risicobeleid van de executor is beschrijfbaar; dat hoort alleen-lezen in het image te staan. "
                    "Er is niets uitgevoerd.",
                ),
            )
        uit = await run_in_threadpool(uitvoerder.run, body, _policy_keys())
        return _finish(claims, uit.status, uit.body)

    @app.get(
        "/api/v1/executions/{request_id}",
        tags=["uitvoeren"],
        summary="Journaal van één actieverzoek (dienst-JWT van de Hub): methode, uitkomst, before/after-hash",
        responses={
            401: {"description": "unauthorized (§4.7)"},
            403: {"description": "geen dienst-JWT van de Hub"},
            422: {"description": "request_id is geen UUID"},
            503: {"description": "journaal_niet_beschikbaar"},
        },
    )
    def executions(request_id: str, request: Request) -> JSONResponse:
        claims = _authenticate(request)
        if isinstance(claims, JSONResponse):
            return claims
        if claims.get("token_use") != "hub_service":
            return _err("forbidden", "Alleen de Hub (dienst-JWT) kan het journaal opvragen.", 403)
        try:
            rid = str(uuid.UUID(request_id))
        except ValueError:
            return _err("validation_error", "request_id moet een UUID zijn.", 422)
        try:
            rows = journal.entries(rid)
            stopped = journal.stopped()
        except JournalUnavailable:
            return _err("journaal_niet_beschikbaar", "Het journaal van de executor is niet beschikbaar.", 503)
        out = []
        for row in rows:
            try:
                target = json.loads(row["target"])
            except ValueError:
                target = None
            out.append({**{k: v for k, v in row.items() if k != "nonce"}, "target": target})
        return JSONResponse({"request_id": rid, "uitvoeringen": out, "gestopt": stopped is not None})

    def _page(
        melding: dict[str, str] | None = None,
        *,
        status_code: int = 200,
        veld: dict[str, str] | None = None,
    ) -> HTMLResponse:
        """Statuspagina in het Peil-sjabloon 1.1.1 (C-55). Meldingen komen altijd uit vaste teksten, nooit uit invoer.
        Zonder ``melding`` van dít verzoek: een bestaande toestand (onleesbaar, laatste fout) zonder live-rol."""
        raw = store.read()
        nas = naslink.public()
        linked = not raw.get("_onleesbaar") and raw.get("state") == "gekoppeld"
        wacht = naslink.pending() if linked and not nas.get("ingesteld") and not nas.get("onleesbaar") else None
        show_form = (
            (not raw.get("_onleesbaar") and not raw.get("first_linked_at") and raw.get("pending") is None)
            or (linked and not nas.get("ingesteld") and not nas.get("onleesbaar"))
            or bool(nas.get("ingesteld"))
        )
        csrf = secrets.token_urlsafe(32) if show_form else ""
        if melding is None:
            if raw.get("_onleesbaar"):
                melding = onleesbaar_melding(sleutel_ingesteld=bool(nas.get("ingesteld")))
            elif wacht is not None:
                # Bestaande toestand (geen live-rol): de vingerafdruk wacht nog op bevestiging.
                melding = vingerafdruk_melding(display_fingerprint(str(wacht.get("fingerprint") or "")), rol="")
            elif (last := (public_status(raw).get("last_error") or {})).get("code"):
                melding = {
                    "toon": "fout",
                    "rol": "",
                    "titel": "Laatste koppelpoging mislukt",
                    "tekst": str(last.get("melding") or "Koppelen is mislukt."),
                    "code": str(last.get("code")),
                }
        html = executor_page(
            versie=__version__,
            link=raw,
            ready_checks=ready_checks(),
            csrf=csrf,
            melding=melding,
            veldfout=veld,
            nas={**nas, "wacht_op_bevestiging": wacht is not None},
            gestopt=gestopt(),
            allowlist=policy.executor_allowlist() if policy is not None else None,
            policy={**policy_status(), "toegestaan": settings.allow_writable_policy},
        )
        resp = HTMLResponse(html, status_code=status_code)
        if csrf:
            resp.set_cookie(CSRF_COOKIE, csrf, httponly=True, samesite="strict", path="/", max_age=3600)
        return resp

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def page() -> HTMLResponse:
        return _page()

    def _afgehandeld(
        code: str, trace: str, *, veld: dict[str, str] | None = None, soort: str = "koppelpoging"
    ) -> HTMLResponse:
        """Eén logregel per afgehandelde poging (code + trace-ID; nooit het Hub-adres van een mislukte poging of een
        geheim), en de vaste melding van dít verzoek (rol ``alert``, code + trace-ID)."""
        log.info("%s afgehandeld: code=%s trace_id=%s", soort, code, trace)
        status_code, titel, tekst = FORM_MESSAGES[code]
        melding = {"toon": "fout", "rol": "alert", "titel": titel, "tekst": tekst, "code": code, "trace_id": trace}
        return _page(melding, status_code=status_code, veld=veld)

    def _gelukt(code: str, trace: str, titel: str, tekst: str, *, soort: str, pad: str = "") -> HTMLResponse:
        log.info("%s afgehandeld: code=%s trace_id=%s", soort, code, trace)
        return _page({"toon": "info", "rol": "status", "titel": titel, "tekst": tekst, "pad": pad})

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

    async def _formulier(request: Request, trace: str, soort: str) -> dict[str, str] | HTMLResponse:
        """§3.7 voor **elk** formulier op deze pagina (§3.9): herkomst → grootte → velden → formuliertoken →
        pogingenlimiet. Geeft de velden terug, of de vaste melding waarmee het verzoek is afgehandeld."""
        # 1. Herkomst (een geweigerd verzoek gaat nergens heen, telt niet als poging en verandert niets).
        if (refused := _herkomst(request)) is not None:
            return _afgehandeld(refused, trace, soort=soort)
        raw_body = await request.body()
        if len(raw_body) > MAX_FORM_BYTES:
            return _afgehandeld("formulier_te_groot", trace, soort=soort)
        try:
            fields = parse_qs(raw_body.decode(errors="replace"), max_num_fields=MAX_FORM_FIELDS)
        except ValueError:  # meer velden dan het formulier heeft: vaste melding, nooit een kale 500
            return _afgehandeld("formulier_te_groot", trace, soort=soort)
        form = {k: v[0] for k, v in fields.items() if v}
        cookie = request.cookies.get(CSRF_COOKIE, "")
        if not cookie or not hmac.compare_digest(cookie.encode(), form.get("csrf", "").encode()):
            return _afgehandeld("formuliercode_onjuist", trace, soort=soort)
        # 2. Elke POST die de herkomstcontrole doorstaat, telt als poging: ook bij ongeldige invoer, een lopende poging,
        #    een onleesbaar koppelbestand of een executor die al eens gekoppeld is (§3.7, RV7).
        ip = request.client.host if request.client else "onbekend"
        if not throttle.allow(ip):
            return _afgehandeld("rate_limited", trace, soort=soort)
        return form

    @app.post("/koppelen", response_class=HTMLResponse, include_in_schema=False)
    async def pair(request: Request) -> HTMLResponse:
        trace = str(uuid.uuid4())
        form = await _formulier(request, trace, "koppelpoging")
        if isinstance(form, HTMLResponse):
            return form
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

    # ------------------------------------------------------------------ TrueNAS-schrijfsleutel en beheer (§3.9)
    def _sleutel_ok(value: str) -> bool:
        return 0 < len(value) <= MAX_KEY_LEN and value.isascii() and value.isprintable() and " " not in value

    def _nas_adres(request: Request) -> tuple[str, int] | None:
        """Het adres van TrueNAS: ``EXECUTOR_TRUENAS_HOST`` (door de beheerder ingesteld bij de Custom App), anders het
        IP-adres waarop deze pagina is geopend — de executor draait op de NAS zelf. Een naam in de ``Host``-header
        wordt niet gebruikt (naamresolutie is geen bewijs van het NAS-adres)."""
        if settings.truenas_host:
            return settings.truenas_host, settings.truenas_port
        host, _bracketed = split_host_header(request.headers.get("host", ""))
        try:
            name, ip = parse_host(host)
            if ip is None:
                return None
            check_address(ip)
        except AdresOngeldig:
            return None
        return name, settings.truenas_port

    def _sleutelfout(code: str, trace: str, soort: str, *, veld: bool) -> HTMLResponse:
        code = code if code in FORM_MESSAGES else "truenas_fout"
        return _afgehandeld(code, trace, soort=soort, veld={"sleutel": FORM_MESSAGES[code][2]} if veld else None)

    @app.post("/schrijfsleutel", response_class=HTMLResponse, include_in_schema=False)
    async def write_key(request: Request) -> HTMLResponse:
        """Eerste keer de schrijfsleutel instellen, in twee stappen. Stap 1 haalt alleen de TLS-vingerafdruk van TrueNAS
        op (de sleutel wordt niet verstuurd en niet bewaard) en toont die ter controle. Stap 2 — dezelfde sleutel
        nogmaals invullen = bevestigen — test de sleutel live tegen precies dat certificaat en slaat hem versleuteld
        op. Daarna liggen NAS-adres en vingerafdruk vast."""
        trace, soort = str(uuid.uuid4()), "sleutelpoging"
        form = await _formulier(request, trace, soort)
        if isinstance(form, HTMLResponse):
            return form
        link = store.read()
        if link.get("_onleesbaar"):
            return _afgehandeld("koppelstatus_onleesbaar", trace, soort=soort)
        if link.get("state") != "gekoppeld":
            return _afgehandeld("niet_gekoppeld", trace, soort=soort)
        nas = naslink.public()
        if nas.get("onleesbaar"):
            return _afgehandeld("sleutelopslag_onleesbaar", trace, soort=soort)
        if nas.get("ingesteld"):
            return _afgehandeld("sleutel_al_ingesteld", trace, soort=soort)
        api_key = form.get("truenas_sleutel", "")
        if not _sleutel_ok(api_key):
            return _sleutelfout("sleutel_ongeldig", trace, soort, veld=True)
        adres = _nas_adres(request)
        if adres is None:
            return _afgehandeld("nas_adres_onbekend", trace, soort=soort)
        host, port = adres
        wacht = naslink.pending()
        try:
            if wacht is None or (wacht.get("host"), wacht.get("port")) != (host, port):
                # Stap 1: alleen de TLS-handdruk. De ingevulde sleutel gaat nergens heen en wordt niet bewaard.
                fingerprint = await run_in_threadpool(
                    fetch_fingerprint, host, port, timeout=min(5.0, settings.truenas_timeout_seconds)
                )
                naslink.set_pending(host, port, fingerprint)
                log.info("%s afgehandeld: code=vingerafdruk_getoond trace_id=%s", soort, trace)
                return _page(vingerafdruk_melding(display_fingerprint(fingerprint), rol="status"))
            # Stap 2: bevestigd. Live test tegen precies het getoonde certificaat; pas daarna opslaan.
            fingerprint = str(wacht.get("fingerprint") or "")
            roles, _methods = await run_in_threadpool(
                verify_key, host, port, fingerprint, api_key, timeout=settings.truenas_timeout_seconds
            )
            naslink.save_key(host, port, fingerprint, api_key, roles)
        except NasFout as exc:
            if exc.code == "certificaat_gewijzigd":
                # Het certificaat is sinds stap 1 veranderd: de bevestiging geldt niet meer; opnieuw beginnen.
                with contextlib.suppress(NasLinkOnleesbaar):
                    naslink.clear_pending()
            return _sleutelfout(
                exc.code, trace, soort, veld=exc.code in ("sleutel_geweigerd", "schrijfrechten_ontbreken")
            )
        except NasLinkOnleesbaar:
            return _afgehandeld("sleutelopslag_onleesbaar", trace, soort=soort)
        return _gelukt(
            "sleutel_ingesteld",
            trace,
            "De schrijfsleutel is getest en opgeslagen.",
            "TrueNAS accepteerde de sleutel en hij heeft schrijfrechten. Het NAS-adres en het certificaat liggen nu "
            "vast; de sleutel staat versleuteld in deze dienst en de Hub ziet hem nooit.",
            soort=soort,
        )

    @app.post("/beheer", response_class=HTMLResponse, include_in_schema=False)
    async def manage(request: Request) -> HTMLResponse:
        """Ontkoppelen van de Hub, de sleutel vervangen of een gestopte executor vrijgeven. Bewijs van TrueNAS-beheer:
        een schrijfsleutel die **nu** live wordt geverifieerd tegen het vastgelegde NAS-adres en certificaat. Een
        ander adres of certificaat kan hier niet worden opgegeven (§3.9)."""
        trace, soort = str(uuid.uuid4()), "beheerpoging"
        form = await _formulier(request, trace, soort)
        if isinstance(form, HTMLResponse):
            return form
        nas = naslink.read()
        if nas.get("_onleesbaar"):
            return _afgehandeld("sleutelopslag_onleesbaar", trace, soort=soort)
        if nas.get("key") is None:
            return _afgehandeld("geen_schrijfsleutel", trace, soort=soort)
        actie = form.get("actie", "")
        if actie not in ("vervangen", "ontkoppelen"):
            return _afgehandeld("actie_onbekend", trace, soort=soort)
        bewijs, nieuw = form.get("truenas_sleutel", ""), form.get("nieuwe_sleutel", "")
        if not _sleutel_ok(bewijs) or (nieuw and not _sleutel_ok(nieuw)):
            return _afgehandeld("sleutel_ongeldig", trace, soort=soort)
        host, port, fingerprint = str(nas["host"]), int(nas["port"]), str(nas["fingerprint"])
        try:
            stopped = journal.stopped()
        except JournalUnavailable:
            return _afgehandeld("journaal_niet_beschikbaar", trace, soort=soort)
        if actie == "vervangen" and not nieuw and stopped is None:
            return _afgehandeld("nieuwe_sleutel_ontbreekt", trace, soort=soort)
        try:
            # Het bewijs: live tegen het vastgelegde adres en certificaat, nooit tegen iets uit dit formulier.
            await run_in_threadpool(
                verify_key, host, port, fingerprint, bewijs, timeout=settings.truenas_timeout_seconds
            )
            if actie == "ontkoppelen":
                store.reset()
                return _gelukt(
                    "ontkoppeld",
                    trace,
                    "Ontkoppeld van de Hub.",
                    "De koppeling met de Hub is gewist; de executor voert niets uit tot hij opnieuw is gekoppeld. Het "
                    "NAS-adres, het certificaat en de schrijfsleutel blijven bewaard. Koppel opnieuw met een "
                    "koppelcode uit de Hub.",
                    soort=soort,
                )
            vervangen = False
            if nieuw:
                roles, _methods = await run_in_threadpool(
                    verify_key, host, port, fingerprint, nieuw, timeout=settings.truenas_timeout_seconds
                )
                naslink.save_key(host, port, fingerprint, nieuw, roles)
                vervangen = True
            vrijgegeven = stopped is not None and journal.release()
        except NasFout as exc:
            return _sleutelfout(exc.code, trace, soort, veld=False)
        except NasLinkOnleesbaar:
            return _afgehandeld("sleutelopslag_onleesbaar", trace, soort=soort)
        except JournalUnavailable:
            return _afgehandeld("journaal_niet_beschikbaar", trace, soort=soort)
        if vervangen and vrijgegeven:
            titel, tekst = (
                "De schrijfsleutel is vervangen en de executor is vrijgegeven.",
                "De nieuwe sleutel is live getest en opgeslagen. De executor voert weer ondertekende acties uit.",
            )
        elif vervangen:
            titel, tekst = (
                "De schrijfsleutel is vervangen.",
                "De nieuwe sleutel is live getest en versleuteld opgeslagen; de oude sleutel is hier gewist.",
            )
        else:
            titel, tekst = (
                "De executor is vrijgegeven.",
                "De stop na de afwijking is opgeheven; de sleutel is niet gewijzigd. Controleer in de Hub het "
                "incident voordat je de actie opnieuw aanbiedt.",
            )
        return _gelukt("vervangen" if vervangen else "vrijgegeven", trace, titel, tekst, soort=soort)

    return app
