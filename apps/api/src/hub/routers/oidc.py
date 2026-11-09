"""SSO-login via OIDC (B01-006): instellen, testen, inschakelen, inloggen (Authorization Code + PKCE) en sessies.

- Instellen, testen en inschakelen alleen door een beheerder; het zijn geen ``action_id``'s (contract §8). Inschakelen
  vraagt een geslaagde testlogin met de huidige instellingen en gate ``authentik`` (D17 Getest). "OIDC verplicht"
  vraagt daarnaast een werkend noodaccount.
- ``/auth/oidc/login`` en ``/auth/oidc/callback`` zijn openbaar (de browser komt van de identity provider). De
  transactie is eenmalig, 10 minuten geldig en aan de browser gebonden via een apart cookie (SameSite=Lax, alleen op
  ``/api/v1/auth/oidc``). Na een geslaagde aanmelding stuurt een kleine pagina zonder JavaScript door naar de Hub, zodat
  de SameSite=Strict-sessiecookie bij de volgende pagina gewoon meegaat.
- Starten van een (test)login en de callback zijn, net als inloggen, uitgezonderd van ``Idempotency-Key`` (ADR-0006).
"""

from __future__ import annotations

import html
import uuid
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import audit, breakglass
from hub.deps import DB, Admin, Idem, SettingsDep, get_keyring, get_vault
from hub.errors import HubError
from hub.keys import KeyRing
from hub.models import OidcConfig, OidcIdentity, Service, User, WebSession
from hub.oidc import client, service
from hub.routers.auth import client_ip, create_session, set_session_cookies
from hub.security import Role, failures_in_window, record_failure
from hub.servicecalls import ServiceCallError, call
from hub.timeutil import iso, utcnow
from hub.vault import Vault

router = APIRouter(tags=["aanmelden en gebruikers"])
VaultDep = Annotated[Vault, Depends(get_vault)]
TX_COOKIE = "hub_oidc"
TX_PATH = "/api/v1/auth/oidc"
START_MAX = 30  # aanmeldpogingen per bron-IP per venster (tegen het volschrijven van de transactietabel)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Koppeling(Strict):
    groep: str = Field(min_length=1, max_length=128)
    rol: Role


class OidcIn(Strict):
    issuer: str = Field(min_length=8, max_length=512)
    client_id: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9._~:-]+$")
    client_secret: str | None = Field(default=None, min_length=8, max_length=512, description="Alleen schrijven")
    client_secret_wissen: bool = False
    redirect_uri: str = Field(min_length=10, max_length=512)
    scopes: str = Field(default="openid profile email", max_length=256, pattern=r"^[A-Za-z0-9_:. -]+$")
    groepen_claim: str = Field(default="groups", min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")
    rolkoppelingen: list[Koppeling] = Field(default_factory=list, max_length=50)
    sessie_minuten: int = Field(default=480, ge=15, le=720)

    @field_validator("scopes")
    @classmethod
    def _openid(cls, v: str) -> str:
        if "openid" not in v.split():
            raise ValueError("scope 'openid' is verplicht")
        return " ".join(dict.fromkeys(v.split()))

    @field_validator("redirect_uri")
    @classmethod
    def _redirect(cls, v: str) -> str:
        from urllib.parse import urlsplit

        p = urlsplit(v)
        if p.scheme not in ("http", "https") or not p.hostname or p.query or p.fragment or p.username:
            raise ValueError("redirect_uri: http(s)://host[:poort]/api/v1/auth/oidc/callback, zonder query")
        if p.path != service.CALLBACK_PATH:
            raise ValueError(f"redirect_uri moet eindigen op {service.CALLBACK_PATH}")
        return v


class InschakelenIn(Strict):
    ingeschakeld: bool
    verplicht: bool = False


class RevokeIn(Strict):
    reden: str = Field(min_length=3, max_length=300)


def _audit(db: Session, actor: str, action: str, details: dict[str, Any] | None = None) -> None:
    audit.record(
        db, actor_type="user", actor_id=actor, action=action, target_type="oidc", target_id="hub", details=details
    )


@router.get("/api/v1/auth/oidc/beschikbaar", summary="Openbaar: is inloggen via SSO beschikbaar (zonder geheimen)?")
def available(db: DB) -> dict[str, Any]:
    cfg = db.get(OidcConfig, 1)
    on = bool(cfg and cfg.ingeschakeld)
    return {
        "ingeschakeld": on,
        "verplicht": service.effective_required(db),
        "login_url": "/api/v1/auth/oidc/login" if on else None,
        "noodlogin": "Bij nood (SSO werkt niet): de noodlogin van de Hub, alleen vanaf het thuisnetwerk.",
    }


@router.get("/api/v1/auth/oidc", summary="SSO-instellingen en -status (admin; clientgeheim nooit terug)")
def get_oidc(db: DB, settings: SettingsDep, _: Admin) -> dict[str, Any]:
    cfg = service.config(db)
    out = service.config_dict(db, cfg)
    out["gate_authentik"] = _gate(db, settings)
    db.commit()
    return out


def _gate(db: Session, settings: Any) -> dict[str, Any]:
    from hub.onboarding import gates as gates_mod
    from hub.routers.onboarding import gate_inputs

    for g in gates_mod.evaluate(gate_inputs(db, settings)):
        if g["id"] == "authentik":
            return {"status": g["status"], "redenen": g["redenen"]}
    return {"status": "unknown", "redenen": []}


@router.put("/api/v1/auth/oidc", summary="SSO instellen (admin); wijzigen van issuer/client zet SSO uit")
def put_oidc(
    body: OidcIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem, vault: VaultDep
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    try:
        issuer = client.validate_issuer(body.issuer, allow_loopback=settings.outbound_allow_loopback)
    except client.OidcError as exc:
        raise HubError(422, exc.reden, exc.uitleg) from exc
    cfg = service.config(db)
    mappings = [m.model_dump(mode="json") for m in body.rolkoppelingen]
    critical = (cfg.issuer, cfg.client_id, cfg.redirect_uri, cfg.rolkoppelingen, cfg.groepen_claim) != (
        issuer,
        body.client_id,
        body.redirect_uri,
        mappings,
        body.groepen_claim,
    )
    if body.client_secret:
        vault.put(db, service.SECRET_REF, body.client_secret, actor=principal.actor)
        cfg.client_secret_ref, critical = service.SECRET_REF, True
    elif body.client_secret_wissen:
        cfg.client_secret_ref, critical = None, True
    if (cfg.issuer, cfg.client_id) != (issuer, body.client_id):
        cfg.discovery, cfg.jwks, cfg.discovery_op, cfg.jwks_op = {}, {}, None, None
    revoked = 0
    if critical:
        cfg.config_versie += 1
        if cfg.ingeschakeld:
            cfg.ingeschakeld = cfg.verplicht = False
            revoked = service.revoke_sessions(db)
    cfg.issuer, cfg.client_id, cfg.redirect_uri = issuer, body.client_id, body.redirect_uri
    cfg.scopes, cfg.groepen_claim, cfg.rolkoppelingen = body.scopes, body.groepen_claim, mappings
    cfg.sessie_minuten = body.sessie_minuten
    cfg.bijgewerkt_door, cfg.bijgewerkt_op, cfg.version = principal.actor, utcnow(), cfg.version + 1
    _audit(
        db,
        principal.name,
        "auth.oidc.config_updated",
        {
            **body.model_dump(mode="json", exclude={"client_secret"}),
            "clientgeheim_gewijzigd": bool(body.client_secret),
            "sso_uitgezet": revoked > 0 or critical,
            "sessies_ingetrokken": revoked,
        },
    )
    db.flush()
    return idem.save(200, service.config_dict(db, cfg))


@router.post("/api/v1/auth/oidc/discover", summary="Discovery en JWKS van de issuer nu ophalen en controleren (admin)")
def discover(db: DB, settings: SettingsDep, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    cfg = service.config(db)
    if not cfg.issuer:
        raise HubError(409, "oidc_niet_ingericht", "Stel eerst de issuer in.")
    policy = settings.outbound_policy()
    try:
        meta = client.discover(cfg.issuer, policy)
        jwks = client.fetch_jwks(meta, policy)
    except client.OidcError as exc:
        _audit(db, principal.name, "auth.oidc.discover_failed", {"reden": exc.reden})
        db.flush()
        return idem.save(
            200,
            {"resultaat": "mislukt", "reden": exc.reden, "uitleg": exc.uitleg, "oidc": service.config_dict(db, cfg)},
        )
    if meta != cfg.discovery:
        cfg.config_versie += 1
    cfg.discovery, cfg.discovery_op, cfg.jwks, cfg.jwks_op = meta, utcnow(), jwks, utcnow()
    _audit(db, principal.name, "auth.oidc.discovered", {"issuer": cfg.issuer, "sleutels": len(jwks["keys"])})
    db.flush()
    return idem.save(200, {"resultaat": "ok", "oidc": service.config_dict(db, cfg)})


def _tx_cookie(resp: Response, request: Request, settings: Any, value: str) -> None:
    secure = settings.cookie_secure == "true" or (settings.cookie_secure == "auto" and request.url.scheme == "https")
    resp.set_cookie(TX_COOKIE, value, max_age=600, httponly=True, secure=secure, samesite="lax", path=TX_PATH)


def _start_limit(db: Session, settings: Any, ip: str) -> None:
    key = f"oidc-start:{ip}"
    if failures_in_window(db, key, settings.login_window_seconds) >= START_MAX:
        raise HubError(
            429,
            "rate_limited",
            "Te veel aanmeldpogingen; probeer het later opnieuw.",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )
    record_failure(db, key)  # telt elke start (niet alleen mislukte)


@router.post("/api/v1/auth/oidc/test", summary="Testlogin starten (admin): volledige aanmelding zonder sessie")
def oidc_test_start(request: Request, db: DB, settings: SettingsDep, principal: Admin) -> JSONResponse:
    cfg = service.config(db)
    _start_limit(db, settings, client_ip(request))
    try:
        url, browser = service.start(
            db, cfg, settings, doel="test", terug="/", actor=principal.actor, ip=client_ip(request)
        )
    except client.OidcError as exc:
        raise HubError(409, exc.reden, exc.uitleg) from exc
    db.commit()
    resp = JSONResponse(
        {"autorisatie_url": url, "toelichting": "Open deze URL in dezelfde browser."},
        headers={"Cache-Control": "no-store"},
    )
    _tx_cookie(resp, request, settings, browser)
    return resp


@router.post("/api/v1/auth/oidc/inschakelen", summary="SSO aan/uit en 'OIDC verplicht' (admin)")
def enable(body: InschakelenIn, db: DB, settings: SettingsDep, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    cfg = service.config(db)
    revoked = 0
    if body.ingeschakeld:
        test = cfg.laatste_test or {}
        if test.get("resultaat") != "geslaagd" or test.get("config_versie") != cfg.config_versie:
            raise HubError(409, "testlogin_vereist", "Doe eerst een geslaagde testlogin met de huidige instellingen.")
        gate = _gate(db, settings)
        if gate["status"] != "toegestaan":
            raise HubError(
                409, "gate_authentik_dicht", "Gate 'Authentik/OIDC' is dicht: D17 moet Getest zijn.", {"gate": gate}
            )
        if body.verplicht:
            breakglass.assert_oidc_required_allowed(db)
    elif cfg.ingeschakeld:
        revoked = service.revoke_sessions(db)
    if not body.ingeschakeld and body.verplicht:
        raise HubError(422, "validation_error", "'OIDC verplicht' kan alleen met SSO ingeschakeld.")
    before = (cfg.ingeschakeld, cfg.verplicht)
    cfg.ingeschakeld, cfg.verplicht = body.ingeschakeld, body.verplicht
    cfg.bijgewerkt_door, cfg.bijgewerkt_op, cfg.version = principal.actor, utcnow(), cfg.version + 1
    _audit(
        db,
        principal.name,
        "auth.oidc.enabled" if body.ingeschakeld else "auth.oidc.disabled",
        {"voor": list(before), "na": [body.ingeschakeld, body.verplicht], "sessies_ingetrokken": revoked},
    )
    db.flush()
    return idem.save(200, service.config_dict(db, cfg))


def _login_error(code: str) -> RedirectResponse:
    return RedirectResponse(f"/inloggen?sso_fout={code}", status_code=303, headers={"Cache-Control": "no-store"})


@router.get(
    "/api/v1/auth/oidc/login",
    summary="Openbaar: aanmelden via SSO starten (302 naar de identity provider)",
    responses={302: {"description": "naar de identity provider"}, 303: {"description": "terug met sso_fout"}},
)
def oidc_login(
    request: Request,
    db: DB,
    settings: SettingsDep,
    terug: Annotated[str, Query(max_length=256)] = "/",
) -> Response:
    cfg = db.get(OidcConfig, 1)
    if cfg is None or not cfg.ingeschakeld:
        return _login_error("sso_uit")
    _start_limit(db, settings, client_ip(request))
    try:
        if cfg.discovery_op is None or utcnow() - cfg.discovery_op > timedelta(hours=24):
            meta = client.discover(str(cfg.issuer), settings.outbound_policy())
            if meta != cfg.discovery:
                # Gewijzigde discovery = nieuwe test nodig; tot dan geen SSO (break-glass blijft werken).
                cfg.ingeschakeld = cfg.verplicht = False
                cfg.config_versie += 1
                audit.record(
                    db,
                    actor_type="system",
                    actor_id="hub",
                    action="auth.oidc.disabled",
                    target_type="oidc",
                    target_id="hub",
                    details={"reden": "discovery_gewijzigd"},
                )
                db.commit()
                return _login_error("sso_gewijzigd")
            cfg.discovery_op = utcnow()
        url, browser = service.start(db, cfg, settings, doel="login", terug=terug, actor=None, ip=client_ip(request))
    except client.OidcError as exc:
        db.commit()
        return _login_error(exc.reden)
    db.commit()
    resp = RedirectResponse(url, status_code=302, headers={"Cache-Control": "no-store"})
    _tx_cookie(resp, request, settings, browser)
    return resp


def _page(titel: str, tekst: str, *, refresh_to: str | None = None, status: int = 200) -> HTMLResponse:
    meta = f'<meta http-equiv="refresh" content="0;url={html.escape(refresh_to)}">' if refresh_to else ""
    link = f'<p><a href="{html.escape(refresh_to)}">Verder naar de Hub</a></p>' if refresh_to else ""
    body = (
        f'<!doctype html><html lang="nl"><head><meta charset="utf-8"><title>{html.escape(titel)}</title>{meta}'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
        f"<body><main><h1>{html.escape(titel)}</h1><p>{html.escape(tekst)}</p>{link}</main></body></html>"
    )
    return HTMLResponse(
        body,
        status_code=status,
        headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; base-uri 'none'"},
    )


def _record_test(db: Session, cfg: OidcConfig, actor: str, result: dict[str, Any]) -> None:
    cfg.laatste_test = {**result, "config_versie": cfg.config_versie, "door": actor}
    cfg.laatste_test_op = utcnow()
    audit.record(
        db,
        actor_type="user",
        actor_id=actor.split(":", 1)[-1],
        action="auth.oidc.tested",
        target_type="oidc",
        target_id="hub",
        details=result,
    )


@router.get("/api/v1/auth/oidc/callback", summary="Openbaar: terugkeer van de identity provider (code + state)")
def oidc_callback(
    request: Request,
    db: DB,
    settings: SettingsDep,
    vault: VaultDep,
    state: Annotated[str, Query(min_length=1, max_length=256)],
    code: Annotated[str | None, Query(max_length=2048)] = None,
    error: Annotated[str | None, Query(max_length=128)] = None,
) -> Response:
    ip = client_ip(request)
    cfg = service.config(db)
    try:
        tx = service.claim_transaction(db, state, request.cookies.get(TX_COOKIE))
    except client.OidcError as exc:
        db.commit()  # 'gebruikt' blijft staan: ook een mislukte poging maakt de state waardeloos
        audit.record(
            db,
            actor_type="user",
            actor_id="onbekend",
            action="auth.oidc.login_failed",
            details={"reden": exc.reden, "ip": ip},
        )
        db.commit()
        return _login_error(exc.reden)
    db.commit()
    is_test = tx.doel == "test"
    actor = tx.gestart_door or "onbekend"
    try:
        if error or not code:
            raise client.OidcError("idp_weigerde", f"De identity provider gaf: {(error or 'geen code')[:64]}.")
        if not is_test and not cfg.ingeschakeld:
            raise client.OidcError("sso_uit", "SSO is uitgeschakeld.")
        info = service.finish(db, cfg, settings, vault, tx, code)
    except client.OidcError as exc:
        db.rollback()
        cfg = service.config(db)
        if is_test:
            _record_test(db, cfg, actor, {"resultaat": "mislukt", "reden": exc.reden, "uitleg": exc.uitleg})
            db.commit()
            return _page("Testlogin mislukt", f"{exc.uitleg} (reden: {exc.reden})", status=400)
        audit.record(
            db,
            actor_type="user",
            actor_id="onbekend",
            action="auth.oidc.login_failed",
            details={"reden": exc.reden, "ip": ip},
        )
        db.commit()
        return _login_error(exc.reden)
    db.commit()  # eventueel opnieuw opgehaalde JWKS bewaren
    role = Role(info["rol"]) if info["rol"] else None
    if is_test:
        _record_test(db, cfg, actor, {"resultaat": "geslaagd" if role else "geen_rol", **info})
        db.commit()
        rol_tekst = f"rol '{role.value}'" if role else "GEEN rol (geen gekoppelde groep: inloggen zou geweigerd worden)"
        return _page(
            "Testlogin klaar",
            f"Issuer en ID-token zijn geldig. Gebruiker '{info['gebruikersnaam']}', "
            f"{len(info['groepen'])} groep(en), {rol_tekst}. Je kunt dit venster sluiten.",
        )
    if role is None:
        ident_users = [
            i.user_id
            for i in db.scalars(
                select(OidcIdentity).where(OidcIdentity.issuer == cfg.issuer, OidcIdentity.sub == info["sub"])
            )
        ]
        n = service.revoke_sessions(db, user_ids=ident_users)
        audit.record(
            db,
            actor_type="user",
            actor_id=info["gebruikersnaam"][:64] or "onbekend",
            action="auth.oidc.login_failed",
            details={"reden": "geen_rol", "groepen": info["groepen"][:20], "sessies_ingetrokken": n, "ip": ip},
        )
        db.commit()
        return _login_error("geen_rol")
    user, created = service.upsert_user(db, cfg, info, role)
    if user.disabled:
        audit.record(
            db,
            actor_type="user",
            actor_id=user.username,
            action="auth.oidc.login_failed",
            details={"reden": "account_uitgeschakeld", "ip": ip},
        )
        db.commit()
        return _login_error("account_uitgeschakeld")
    ttl = min(cfg.sessie_minuten * 60, settings.session_ttl_seconds)
    token, csrf, _sess, ttl = create_session(
        request,
        db,
        settings,
        user,
        ttl_seconds=ttl,
        auth_bron="oidc",
        action="auth.oidc.login",
        details={"nieuw_account": created, "rol": role.value, "groepen_bron": info["groepen_bron"], "ip": ip},
    )
    resp = _page("Aangemeld", "Je bent aangemeld via SSO en wordt doorgestuurd naar de Hub.", refresh_to=tx.terug)
    set_session_cookies(resp, request, settings, token, csrf, ttl)
    resp.delete_cookie(TX_COOKIE, path=TX_PATH)
    return resp


# ------------------------------------------------------------------ sessies (admin)
@router.get("/api/v1/sessions", summary="Alle actieve sessies (admin): gebruiker, bron (lokaal/oidc), noodlogin")
def all_sessions(db: DB, _: Admin) -> dict[str, Any]:
    now = utcnow()
    rows = db.execute(
        select(WebSession, User)
        .join(User, User.id == WebSession.user_id)
        .where(WebSession.revoked_at.is_(None), WebSession.expires_at > now)
        .order_by(WebSession.created_at.desc())
        .limit(500)
    ).all()
    return {
        "items": [
            {
                "id": str(s.id),
                "gebruiker": u.username,
                "rol": u.role,
                "auth_bron": s.auth_bron,
                "noodlogin": s.break_glass,
                "aangemaakt": iso(s.created_at),
                "laatst_gezien": iso(s.last_seen_at),
                "verloopt": iso(s.expires_at),
                "ip": s.client_ip,
            }
            for s, u in rows
        ]
    }


@router.post("/api/v1/users/{user_id}/sessions/revoke", summary="Alle sessies van een gebruiker intrekken (admin)")
def revoke_user_sessions(user_id: uuid.UUID, body: RevokeIn, db: DB, principal: Admin, idem: Idem) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        return replay
    user = db.get(User, user_id)
    if user is None:
        raise HubError(404, "not_found", "Gebruiker niet gevonden.")
    n = service.revoke_sessions(db, user_ids=[user.id], only_oidc=False)
    audit.record(
        db,
        actor_type="user",
        actor_id=principal.name,
        action="auth.sessions_revoked_by_admin",
        target_type="user",
        target_id=str(user.id),
        details={"sessies": n, "reden": body.reden},
    )
    db.flush()
    return idem.save(200, {"gebruiker": user.username, "ingetrokken": n})


# ------------------------------------------------------------------ advies van home-control-hub (B13)
LP_WEERGAVE = {"te_ruim": "fout", "onbekend": "onbekend", "deels_gecontroleerd": "waarschuwing"}
RECHTEN_WEERGAVE = {"ok": "ok", "verouderd": "verouderd", "onbekend": "onbekend"}


@router.get(
    "/api/v1/sso/status",
    summary="SSO-advies van home-control-hub (admin): least privilege en rechtenkaart, nooit groen op aannames",
)
def sso_status(
    db: DB, settings: SettingsDep, principal: Admin, keyring: Annotated[KeyRing, Depends(get_keyring)]
) -> dict[str, Any]:
    from hub.registry import service_base_url

    out: dict[str, Any] = {
        "bron": "home-control-hub",
        "rol": "adviseur (nooit poortwachter); de Hub beslist zelf over toegang",
        "least_privilege": {"waarde": None, "weergave": "onbekend"},
        "rechten": {"status": None, "weergave": "onbekend"},
        "rolkoppelingen_hub": None,
        "bijgewerkt_op": iso(utcnow()),
    }
    svc = db.scalars(select(Service).where(Service.app_id == "home-control-hub", Service.status == "active")).first()
    if svc is None:
        return {**out, "status": "onbekend", "reden": "home_control_hub_niet_gekoppeld"}
    base, why = service_base_url(db, settings, svc)
    if base is None:
        return {**out, "status": "onbekend", "reden": why}

    def get(path: str, bearer: str) -> dict[str, Any] | None:
        try:
            res = call(
                base,
                "GET",
                path,
                bearer=bearer,
                connect_timeout=settings.service_call_connect_timeout,
                read_timeout=settings.service_call_read_timeout,
            )
        except ServiceCallError:
            return None
        return res.body if res.status == 200 and isinstance(res.body, dict) else None

    svc_jwt, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    detect = get("/integrations/v1/sso/authentik", svc_jwt)
    user_jwt, _ = keyring.issue_user_jwt(
        subject=principal.id, audience=svc.app_id, roles=["admin"], ttl_seconds=settings.jwt_ttl_seconds
    )
    rights = get("/integrations/v1/sso/rights", user_jwt)
    svc_jwt2, _ = keyring.issue_hub_service_jwt(audience=svc.app_id, service_id=str(svc.id))
    maps = get("/integrations/v1/sso/role-mappings?app_id=ai-server-manager", svc_jwt2)
    lp = ((detect or {}).get("detection") or {}).get("token", {}).get("least_privilege") if detect else None
    rstatus = (rights or {}).get("status")
    out["least_privilege"] = {
        "waarde": lp,
        # Contract: 'deels_gecontroleerd' en onbekende waarden zijn nooit groen; 'ok' bestaat niet (ADR-0009 HCH).
        "weergave": LP_WEERGAVE.get(str(lp), "onbekend"),
        "melding": (((detect or {}).get("detection") or {}).get("token") or {}).get("message_nl"),
    }
    out["rechten"] = {
        "status": rstatus,
        "weergave": RECHTEN_WEERGAVE.get(str(rstatus), "onbekend"),
        "melding": ((rights or {}).get("freshness") or {}).get("message_nl") or (rights or {}).get("message_nl"),
    }
    out["rolkoppelingen_hub"] = (maps or {}).get("items") if maps else None
    out["status"] = "ok" if detect is not None else "onbekend"
    return out
