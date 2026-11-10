"""OIDC in de Hub (B01-006): configuratie, groep→rol, aanmeldtransacties, gebruikers en sessie-intrekking.

- **Groep → rol** (alleen in de Hub ingesteld; ``home-control-hub`` is adviseur, nooit poortwachter): de rol ``kind``
  wint altijd (contract §4.2); anders de hoogste gekoppelde rol. Geen gekoppelde groep → geen toegang (nooit een
  standaardrol), en lopende SSO-sessies van die gebruiker worden ingetrokken.
- **Nooit automatisch koppelen** aan een bestaand lokaal account op naam of e-mail: een SSO-gebruiker krijgt een eigen
  account (``auth_bron = oidc``) zonder bruikbaar wachtwoord.
- **Noodlogin blijft altijd werken** (contract 1.2 §4.1): ook bij een onbereikbare of foute issuer, en ook als "OIDC
  verplicht" aan staat. "OIDC verplicht" kan alleen aan met een werkend noodaccount en geldt alleen zolang dat
  noodaccount werkt (anders weer lokaal inloggen: geen SSO-only lock-out).
- **Sessie-intrekking:** uitloggen en intrekken werken direct (de sessie wordt per verzoek gecontroleerd); OIDC
  uitzetten of de issuer/client wijzigen trekt alle SSO-sessies in; het event ``sso.access.revoked`` van
  ``home-control-hub`` trekt de sessies van die Authentik-gebruiker in (alleen intrekken, nooit rechten geven).
"""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from hub import audit, breakglass
from hub.config import Settings
from hub.incidents.rules import EventIn
from hub.models import OidcConfig, OidcIdentity, OidcTransaction, User, WebSession
from hub.oidc import client
from hub.security import ROLE_RANK, Role, sha256_hex
from hub.timeutil import iso, utcnow
from hub.vault import Vault, make_ref

SECRET_REF = make_ref("auth", "oidc-client-secret")
CALLBACK_PATH = "/api/v1/auth/oidc/callback"
TX_TTL = timedelta(minutes=10)
UNUSABLE_PASSWORD = "!oidc-geen-wachtwoord"  # noqa: S105 - geen geheim: argon2 weigert dit altijd
USERNAME_OK = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
HCH = "home-control-hub"


def config(db: Session) -> OidcConfig:
    row = db.get(OidcConfig, 1)
    if row is None:
        row = OidcConfig(
            id=1,
            ingeschakeld=False,
            verplicht=False,
            scopes="openid profile email",
            groepen_claim="groups",
            rolkoppelingen=[],
            sessie_minuten=480,
            discovery={},
            jwks={},
            laatste_test={},
            config_versie=1,
            bijgewerkt_door="system",
            bijgewerkt_op=utcnow(),
            version=1,
        )
        db.add(row)
        db.flush()
    return row


def effective_required(db: Session) -> bool:
    cfg = db.get(OidcConfig, 1)
    return bool(cfg and cfg.ingeschakeld and cfg.verplicht and breakglass.is_working(breakglass.account(db)))


def map_role(groups: list[str], mappings: list[dict[str, Any]]) -> Role | None:
    roles: list[Role] = []
    have = {str(g) for g in groups}
    for m in mappings:
        if str(m.get("groep")) in have:
            try:
                roles.append(Role(str(m.get("rol"))))
            except ValueError:
                continue
    if not roles:
        return None
    if Role.kind in roles:
        return Role.kind
    return max(roles, key=lambda r: ROLE_RANK[r])


# Alleen zichtbare ASCII zonder spatie en zonder backslash: een browser haalt tab/CR/LF uit een URL, waardoor
# "/<tab>/evil.lan" in de meta-refresh na het aanmelden "//evil.lan" (een ander domein) zou worden.
_SAFE_PATH = re.compile(r"/(?![/\\])[!-~]*")


def safe_return(path: str | None) -> str:
    """Terugkeerpad na SSO: alleen een pad binnen de Hub, anders ``/`` (geen open redirect)."""
    p = (path or "/").strip()
    if len(p) > 256 or "\\" in p or "://" in p or not _SAFE_PATH.fullmatch(p):
        return "/"
    return p


def config_dict(db: Session, cfg: OidcConfig) -> dict[str, Any]:
    from hub.models import VaultSecret

    secret = db.scalar(select(VaultSecret).where(VaultSecret.ref == SECRET_REF)) if cfg.client_secret_ref else None
    working = breakglass.is_working(breakglass.account(db))
    test = cfg.laatste_test or {}
    test_actueel = bool(test.get("resultaat") == "geslaagd" and test.get("config_versie") == cfg.config_versie)
    return {
        "ingeschakeld": cfg.ingeschakeld,
        "verplicht": cfg.verplicht,
        "verplicht_effectief": bool(cfg.ingeschakeld and cfg.verplicht and working),
        "noodaccount_werkend": working,
        "issuer": cfg.issuer,
        "client_id": cfg.client_id,
        "client_secret": {"ingesteld": secret is not None, "laatste4": secret.last4 if secret else None},
        "redirect_uri": cfg.redirect_uri,
        "redirect_uri_https": bool(cfg.redirect_uri and cfg.redirect_uri.startswith("https://")),
        "scopes": cfg.scopes,
        "groepen_claim": cfg.groepen_claim,
        "rolkoppelingen": cfg.rolkoppelingen or [],
        "sessie_minuten": cfg.sessie_minuten,
        "discovery": {
            "status": "ok" if cfg.discovery else "onbekend",
            "gemeten_op": iso(cfg.discovery_op),
            "endpoints": {k: v for k, v in (cfg.discovery or {}).items() if k.endswith(("endpoint", "uri"))},
            "algoritmen": (cfg.discovery or {}).get("id_token_algs"),
        },
        "jwks": {"sleutels": [k.get("kid") for k in (cfg.jwks or {}).get("keys", [])], "gemeten_op": iso(cfg.jwks_op)},
        "laatste_test": {**test, "op": iso(cfg.laatste_test_op), "actueel": test_actueel},
        "config_versie": cfg.config_versie,
        "bijgewerkt_door": cfg.bijgewerkt_door,
        "bijgewerkt_op": iso(cfg.bijgewerkt_op),
        "versie": cfg.version,
    }


# ------------------------------------------------------------------ sessies intrekken
def revoke_sessions(db: Session, *, user_ids: list[uuid.UUID] | None = None, only_oidc: bool = True) -> int:
    q = update(WebSession).where(WebSession.revoked_at.is_(None))
    if only_oidc:
        q = q.where(WebSession.auth_bron == "oidc")
    if user_ids is not None:
        if not user_ids:
            return 0
        q = q.where(WebSession.user_id.in_(user_ids))
    res = db.execute(q.values(revoked_at=utcnow()))
    return int(getattr(res, "rowcount", 0) or 0)


def handle_event(db: Session, settings: Settings, ev: EventIn, now: datetime) -> None:
    """Haak uit de incidentenmotor: ``sso.access.revoked`` van home-control-hub → SSO-sessies van die gebruiker in de
    Hub intrekken (alleen intrekken; een event kan nooit rechten geven)."""
    if ev.stroom != "inbox" or ev.source_app != HCH or ev.event_type != "sso.access.revoked":
        return
    name = ev.entity_id.strip()
    if not name:
        return
    idents = list(db.scalars(select(OidcIdentity).where(OidcIdentity.gebruikersnaam == name)))
    n = revoke_sessions(db, user_ids=[i.user_id for i in idents])
    for i in idents:
        i.ingetrokken_op = now
    audit.record(
        db,
        actor_type="service",
        actor_id=HCH,
        action="auth.oidc.sessions_revoked",
        target_type="oidc_identity",
        target_id=name[:128],
        details={"reden": "sso.access.revoked", "sessies": n, "accounts": len(idents), "event": ev.ref},
    )


# ------------------------------------------------------------------ aanmelden
def start(
    db: Session, cfg: OidcConfig, settings: Settings, *, doel: str, terug: str, actor: str | None, ip: str
) -> tuple[str, str]:
    """Nieuwe transactie; geeft (autorisatie-URL, browsergeheim voor het cookie)."""
    meta = cfg.discovery or {}
    if not meta or not cfg.client_id or not cfg.redirect_uri:
        raise client.OidcError("oidc_niet_ingericht", "SSO is nog niet volledig ingesteld (issuer, client, redirect).")
    state, nonce, browser = secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    verifier, challenge = client.new_pkce()
    now = utcnow()
    db.add(
        OidcTransaction(
            state_hash=sha256_hex(state),
            browser_hash=sha256_hex(browser),
            nonce_hash=hashlib.sha256(nonce.encode()).hexdigest(),
            code_verifier=verifier,
            doel=doel,
            gestart_door=actor,
            terug=safe_return(terug),
            config_versie=cfg.config_versie,
            bron_ip=ip[:64],
            aangemaakt_op=now,
            verloopt_op=now + TX_TTL,
        )
    )
    url = client.authorization_url(
        meta,
        client_id=cfg.client_id,
        redirect_uri=cfg.redirect_uri,
        scopes=cfg.scopes,
        state=state,
        nonce=nonce,
        challenge=challenge,
    )
    return url, browser


def claim_transaction(db: Session, state: str, browser: str | None) -> OidcTransaction:
    """Eenmalig: een tweede callback met dezelfde state (replay) faalt altijd."""
    tx = db.scalars(
        select(OidcTransaction).where(OidcTransaction.state_hash == sha256_hex(state)).with_for_update()
    ).first()
    if tx is None:
        raise client.OidcError("state_onbekend", "Onbekende aanmelding (state).")
    if tx.gebruikt_op is not None:
        raise client.OidcError("state_al_gebruikt", "Deze aanmelding is al gebruikt (replay geweigerd).")
    tx.gebruikt_op = utcnow()
    if tx.verloopt_op <= utcnow():
        raise client.OidcError("state_verlopen", "De aanmelding is verlopen; probeer opnieuw.")
    if not browser or not secrets.compare_digest(sha256_hex(browser), tx.browser_hash):
        raise client.OidcError("browser_onjuist", "Deze aanmelding is in een andere browser gestart.")
    return tx


def _jwks_for(db: Session, cfg: OidcConfig, settings: Settings, kid: str | None) -> dict[str, Any]:
    keys = (cfg.jwks or {}).get("keys") or []
    known = any(k.get("kid") == kid for k in keys) if kid else bool(keys)
    recent = cfg.jwks_op is not None and utcnow() - cfg.jwks_op < timedelta(seconds=60)
    if (not known and not recent) or not keys:
        cfg.jwks = client.fetch_jwks(cfg.discovery, settings.outbound_policy())
        cfg.jwks_op = utcnow()
    return cfg.jwks


def finish(
    db: Session, cfg: OidcConfig, settings: Settings, vault: Vault, tx: OidcTransaction, code: str
) -> dict[str, Any]:
    """Code inwisselen, ID-token valideren en groepen/rol bepalen. Geeft een samenvatting zonder tokens."""
    if tx.config_versie != cfg.config_versie:
        raise client.OidcError("config_gewijzigd", "De SSO-instellingen zijn intussen gewijzigd; probeer opnieuw.")
    assert cfg.client_id and cfg.redirect_uri and cfg.issuer
    secret = vault.get(db, cfg.client_secret_ref) if cfg.client_secret_ref else None
    policy = settings.outbound_policy()
    tokens = client.exchange_code(
        cfg.discovery,
        client_id=cfg.client_id,
        client_secret=secret,
        redirect_uri=cfg.redirect_uri,
        code=code,
        verifier=tx.code_verifier,
        policy=policy,
    )
    id_token = str(tokens["id_token"])
    try:
        import jwt as _jwt

        kid = _jwt.get_unverified_header(id_token).get("kid")
    except Exception:
        kid = None
    jwks = _jwks_for(db, cfg, settings, str(kid) if kid else None)
    v = client.validate_id_token(
        id_token,
        jwks=jwks,
        issuer=cfg.issuer,
        client_id=cfg.client_id,
        nonce_hash=tx.nonce_hash,
        allowed_algs=list((cfg.discovery or {}).get("id_token_algs") or client.ALLOWED_ALGS),
        now=utcnow(),
    )
    claims = v.claims
    groups = claims.get(cfg.groepen_claim)
    groepen_bron = "id_token"
    if not isinstance(groups, list):
        info = client.userinfo(cfg.discovery, str(tokens.get("access_token") or ""), policy)
        if info is not None and info.get("sub") == claims["sub"] and isinstance(info.get(cfg.groepen_claim), list):
            groups, groepen_bron = info.get(cfg.groepen_claim), "userinfo"
        else:
            groups, groepen_bron = [], "geen"
    groups = [str(g)[:128] for g in groups or []][:100]
    role = map_role(groups, cfg.rolkoppelingen or [])
    return {
        "sub": str(claims["sub"])[:255],
        "gebruikersnaam": str(claims.get("preferred_username") or claims.get("nickname") or "")[:255],
        "naam": str(claims.get("name") or "")[:128],
        "groepen": groups,
        "groepen_bron": groepen_bron,
        "rol": role.value if role else None,
        "alg": v.alg,
        "kid": v.kid,
    }


def _username(db: Session, wanted: str, sub: str) -> str:
    base = re.sub(r"[^a-z0-9._-]+", "-", (wanted or "").lower()).strip("-._")
    if not USERNAME_OK.match(base):
        base = "sso-" + hashlib.sha256(sub.encode()).hexdigest()[:10]
    base = base[:56]
    for cand in (base, f"{base}-sso", *[f"{base}-sso{i}" for i in range(2, 50)]):
        if db.scalars(select(User.id).where(User.username == cand)).first() is None:
            return cand
    return "sso-" + uuid.uuid4().hex[:12]


def upsert_user(db: Session, cfg: OidcConfig, info: dict[str, Any], role: Role) -> tuple[User, bool]:
    """Bestaande koppeling op (issuer, sub) of een nieuw SSO-account; nooit een lokaal account overnemen."""
    assert cfg.issuer
    ident = db.scalars(
        select(OidcIdentity).where(OidcIdentity.issuer == cfg.issuer, OidcIdentity.sub == info["sub"])
    ).first()
    now = utcnow()
    if ident is None:
        user = User(
            username=_username(db, info["gebruikersnaam"], info["sub"]),
            display_name=info["naam"] or info["gebruikersnaam"][:128],
            password_hash=UNUSABLE_PASSWORD,
            role=role.value,
            auth_bron="oidc",
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()
        ident = OidcIdentity(issuer=cfg.issuer, sub=info["sub"], user_id=user.id, aangemaakt_op=now)
        db.add(ident)
        created = True
    else:
        found = db.get(User, ident.user_id)
        assert found is not None
        user, created = found, False
    ident.gebruikersnaam = info["gebruikersnaam"]
    ident.groepen = info["groepen"]
    ident.laatste_login_op, ident.ingetrokken_op = now, None
    if user.role != role.value:
        revoke_sessions(db, user_ids=[user.id])  # rolwijziging: oude SSO-sessies vervallen
        user.role, user.updated_at, user.version = role.value, now, user.version + 1
    db.flush()
    return user, created
