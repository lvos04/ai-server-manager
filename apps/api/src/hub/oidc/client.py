"""OIDC-client van de Hub (B01-006, Hub-kant van B13): Authorization Code + PKCE (S256) tegen een instelbare issuer.

Regels (ADR-0023):
- Issuer alleen ``https://`` (``http://`` uitsluitend naar loopback met de ontwikkelvlag, voor de in-repo fake); het
  ``issuer``-veld van de discovery moet **exact** gelijk zijn aan de ingestelde issuer (OIDC Discovery §4.3); alle
  endpoints op dezelfde oorsprong als de issuer; nooit redirects volgen, nooit proxy-omgevingsvariabelen.
- PKCE S256 is verplicht (staat het niet in ``code_challenge_methods_supported``, dan weigert de Hub).
- ID-token: alleen asymmetrische handtekeningen (RS/PS/ES/EdDSA; nooit ``none`` of HS*), ``kid`` uit de JWKS (onbekend →
  één keer opnieuw ophalen, hooguit eens per minuut), ``iss`` exact, ``aud`` bevat de client-id (meerdere ``aud`` →
  ``azp`` moet de client-id zijn), ``exp``/``iat``/``nbf`` met 30 s speling, ``iat`` niet ouder dan 10 min, ``nonce``
  gelijk aan die van de transactie, ``sub`` aanwezig. Hergebruik van een callback faalt op de eenmalige transactie.
- Geen token, code of geheim in logs of foutmeldingen; alleen vaste redencodes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

import jwt

from hub.outbound import OutboundError, OutboundPolicy, basic_auth, request, split_url, validate_base_url

ALLOWED_ALGS = ("RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "ES512", "EdDSA")
LEEWAY_S = 30
MAX_IAT_AGE_S = 600
DISCOVERY_PATH = "/.well-known/openid-configuration"


class OidcError(Exception):
    """Vaste ``reden`` (machine) + Nederlandse uitleg (mens); nooit een geheim."""

    def __init__(self, reden: str, uitleg: str) -> None:
        super().__init__(reden)
        self.reden, self.uitleg = reden, uitleg


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def new_pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)[:96]
    return verifier, b64url(hashlib.sha256(verifier.encode()).digest())


def _origin(url: str) -> tuple[str, str, int | None]:
    p = urlsplit(url)
    return p.scheme, (p.hostname or "").lower(), p.port


def validate_issuer(issuer: str, *, allow_loopback: bool) -> str:
    issuer = (issuer or "").strip()
    try:
        validate_base_url(issuer, allow_loopback=allow_loopback)
    except OutboundError as exc:
        raise OidcError("issuer_ongeldig", f"Ongeldig issuer-adres ({exc.reason}).") from exc
    p = urlsplit(issuer)
    if p.scheme != "https" and not (allow_loopback and p.hostname in ("127.0.0.1", "localhost", "::1")):
        raise OidcError("issuer_niet_https", "De issuer moet https:// gebruiken (OIDC over het netwerk vraagt TLS).")
    return issuer


def _get_json(url: str, policy: OutboundPolicy, headers: dict[str, str] | None = None) -> Any:
    try:
        base, path = split_url(url, allow_loopback=policy.allow_loopback)
        res = request(base, "GET", path, policy=policy, headers=headers, max_bytes=512 * 1024)
    except OutboundError as exc:
        raise OidcError("issuer_onbereikbaar", f"De identity provider is niet bereikbaar ({exc.reason}).") from exc
    if res.status != 200:
        raise OidcError("issuer_fout", f"De identity provider antwoordde met HTTP {res.status}.")
    data = res.json()
    if not isinstance(data, dict):
        raise OidcError("issuer_antwoord_ongeldig", "Het antwoord van de identity provider is geen JSON-object.")
    return data


def discover(issuer: str, policy: OutboundPolicy) -> dict[str, Any]:
    issuer = validate_issuer(issuer, allow_loopback=policy.allow_loopback)
    meta = _get_json(issuer.rstrip("/") + DISCOVERY_PATH, policy)
    if meta.get("issuer") != issuer:
        raise OidcError(
            "issuer_komt_niet_overeen",
            f"De discovery noemt een andere issuer ({str(meta.get('issuer'))[:200]}); gebruik exact die waarde.",
        )
    origin = _origin(issuer)
    out: dict[str, Any] = {"issuer": issuer}
    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        val = meta.get(key)
        if not isinstance(val, str) or not val:
            raise OidcError("discovery_onvolledig", f"De discovery mist '{key}'.")
        if _origin(val) != origin:
            raise OidcError("endpoint_andere_oorsprong", f"'{key}' staat op een andere oorsprong dan de issuer.")
        out[key] = val
    for key in ("userinfo_endpoint", "end_session_endpoint"):
        val = meta.get(key)
        if isinstance(val, str) and val and _origin(val) == origin:
            out[key] = val
    if "code" not in (meta.get("response_types_supported") or []):
        raise OidcError("code_flow_niet_ondersteund", "De identity provider ondersteunt geen Authorization Code.")
    if "S256" not in (meta.get("code_challenge_methods_supported") or []):
        raise OidcError("pkce_niet_ondersteund", "De identity provider meldt geen PKCE met S256.")
    algs = meta.get("id_token_signing_alg_values_supported") or []
    usable = [a for a in algs if a in ALLOWED_ALGS]
    if algs and not usable:
        raise OidcError(
            "alleen_symmetrisch",
            "De identity provider ondertekent ID-tokens niet asymmetrisch (bv. alleen HS256). Kies in Authentik een "
            "signing key (RS256) voor deze provider.",
        )
    out["id_token_algs"] = usable or list(ALLOWED_ALGS)
    out["token_auth_methods"] = list(meta.get("token_endpoint_auth_methods_supported") or ["client_secret_basic"])
    return out


def fetch_jwks(meta: dict[str, Any], policy: OutboundPolicy) -> dict[str, Any]:
    data = _get_json(str(meta["jwks_uri"]), policy)
    keys = [
        k
        for k in data.get("keys") or []
        if isinstance(k, dict) and k.get("kty") in ("RSA", "EC", "OKP") and k.get("use", "sig") == "sig"
    ]
    if not keys:
        raise OidcError("jwks_leeg", "De identity provider publiceert geen bruikbare ondertekensleutel.")
    for k in keys:
        if any(f in k for f in ("d", "p", "q", "dp", "dq", "qi", "k")):
            raise OidcError("jwks_ongeldig", "De JWKS bevat privé-sleutelmateriaal; geweigerd.")
    return {"keys": keys}


def authorization_url(
    meta: dict[str, Any], *, client_id: str, redirect_uri: str, scopes: str, state: str, nonce: str, challenge: str
) -> str:
    from urllib.parse import urlencode

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    sep = "&" if "?" in str(meta["authorization_endpoint"]) else "?"
    return f"{meta['authorization_endpoint']}{sep}{urlencode(params)}"


def exchange_code(
    meta: dict[str, Any],
    *,
    client_id: str,
    client_secret: str | None,
    redirect_uri: str,
    code: str,
    verifier: str,
    policy: OutboundPolicy,
) -> dict[str, Any]:
    form = {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri, "code_verifier": verifier}
    headers: dict[str, str] = {}
    methods = meta.get("token_auth_methods") or ["client_secret_basic"]
    if client_secret and "client_secret_basic" in methods:
        from urllib.parse import quote

        headers["Authorization"] = basic_auth(quote(client_id, safe=""), quote(client_secret, safe=""))
    elif client_secret:
        form.update({"client_id": client_id, "client_secret": client_secret})
    else:
        form["client_id"] = client_id
    try:
        base, path = split_url(str(meta["token_endpoint"]), allow_loopback=policy.allow_loopback)
        res = request(base, "POST", path, policy=policy, headers=headers, form_body=form, max_bytes=256 * 1024)
    except OutboundError as exc:
        raise OidcError("token_onbereikbaar", f"Token-endpoint niet bereikbaar ({exc.reason}).") from exc
    body = res.json()
    if res.status != 200 or not isinstance(body, dict):
        err = str(body.get("error"))[:64] if isinstance(body, dict) and body.get("error") else f"HTTP {res.status}"
        raise OidcError("token_geweigerd", f"De identity provider weigerde de code ({err}).")
    if str(body.get("token_type", "")).lower() != "bearer" or not isinstance(body.get("id_token"), str):
        raise OidcError("token_antwoord_ongeldig", "Het tokenantwoord mist een ID-token of is geen Bearer.")
    return body


@dataclass
class Validated:
    claims: dict[str, Any]
    kid: str | None
    alg: str


def _find_key(jwks: dict[str, Any], kid: str | None, alg: str) -> Any:
    keys = jwks.get("keys") or []
    if kid is None:
        if len(keys) != 1:
            raise OidcError("kid_ontbreekt", "Het ID-token noemt geen sleutel (kid) en de JWKS heeft er meerdere.")
        cand = keys[0]
    else:
        cand = next((k for k in keys if k.get("kid") == kid), None)
        if cand is None:
            raise OidcError("onbekende_sleutel", "Het ID-token is ondertekend met een onbekende sleutel (kid).")
    try:
        return jwt.PyJWK(cand, algorithm=alg).key
    except (jwt.PyJWKError, jwt.InvalidKeyError, ValueError) as exc:
        raise OidcError("sleutel_ongeldig", "De sleutel in de JWKS past niet bij het algoritme.") from exc


def validate_id_token(
    token: str,
    *,
    jwks: dict[str, Any],
    issuer: str,
    client_id: str,
    nonce_hash: str,
    allowed_algs: list[str],
    now: datetime,
) -> Validated:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise OidcError("id_token_ongeldig", "Het ID-token is geen geldige JWS.") from exc
    alg = str(header.get("alg") or "")
    if alg not in ALLOWED_ALGS or alg not in allowed_algs:
        raise OidcError("alg_niet_toegestaan", f"Algoritme '{alg[:16]}' is niet toegestaan (alleen asymmetrisch).")
    kid = header.get("kid")
    key = _find_key(jwks, str(kid) if kid is not None else None, alg)
    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=[alg],
            audience=client_id,
            issuer=issuer,
            leeway=LEEWAY_S,
            options={"require": ["iss", "sub", "aud", "exp", "iat"], "verify_iat": True},
        )
    except jwt.ExpiredSignatureError as exc:
        raise OidcError("id_token_verlopen", "Het ID-token is verlopen.") from exc
    except jwt.InvalidIssuerError as exc:
        raise OidcError("issuer_onjuist", "Het ID-token komt van een andere issuer.") from exc
    except jwt.InvalidAudienceError as exc:
        raise OidcError("audience_onjuist", "Het ID-token is niet voor deze Hub (aud).") from exc
    except jwt.InvalidSignatureError as exc:
        raise OidcError("handtekening_ongeldig", "De handtekening van het ID-token klopt niet.") from exc
    except jwt.PyJWTError as exc:
        raise OidcError("id_token_ongeldig", "Het ID-token is ongeldig (claims).") from exc
    aud = claims.get("aud")
    if isinstance(aud, list) and len(aud) > 1 and claims.get("azp") != client_id:
        raise OidcError("azp_onjuist", "Het ID-token heeft meerdere audiences maar azp is niet deze Hub.")
    iat = claims.get("iat")
    if not isinstance(iat, int | float) or now.timestamp() - float(iat) > MAX_IAT_AGE_S + LEEWAY_S:
        raise OidcError("id_token_te_oud", "Het ID-token is te oud (iat).")
    nonce = claims.get("nonce")
    if not isinstance(nonce, str) or not secrets.compare_digest(hashlib.sha256(nonce.encode()).hexdigest(), nonce_hash):
        raise OidcError("nonce_onjuist", "De nonce in het ID-token hoort niet bij deze aanmelding (replay?).")
    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise OidcError("sub_ontbreekt", "Het ID-token mist een gebruikers-id (sub).")
    return Validated(claims=claims, kid=str(kid) if kid is not None else None, alg=alg)


def userinfo(meta: dict[str, Any], access_token: str, policy: OutboundPolicy) -> dict[str, Any] | None:
    url = meta.get("userinfo_endpoint")
    if not url or not access_token:
        return None
    try:
        data = _get_json(str(url), policy, headers={"Authorization": f"Bearer {access_token}"})
    except OidcError:
        return None
    return data if isinstance(data, dict) else None


def safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)[:2000]
