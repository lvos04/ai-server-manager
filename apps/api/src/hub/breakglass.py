"""Noodlogin (break-glass) van de Hub (contract 1.2 §4.1): TOTP (RFC 6238), privé-bereiken en accountstatus.

Werkt zonder Authentik/OIDC en zonder enige netwerkaanroep. Het TOTP-geheim staat versleuteld in de vault; de
database bevat alleen de vault-referentie. Een gebruikte code (tijdstap) wordt nooit een tweede keer geaccepteerd.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import secrets
import struct
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.config import Settings
from hub.errors import HubError
from hub.models import User
from hub.timeutil import iso, utcnow

TOTP_PERIOD = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1  # één tijdstap speling naar voren en naar achteren (klokverschil telefoon)
ISSUER = "TrueNAS Home Platform"  # productnaam (besluit gebruiker O-07)

PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "fc00::/7")
)
# Deterministische zelftest: een adres binnen een privé-bereik en een documentatie-adres (RFC 5737) erbuiten.
SELFTEST_INSIDE = "10.0.0.1"
SELFTEST_OUTSIDE = "192.0.2.10"
DOCKER_BRIDGE = ipaddress.ip_network("172.16.0.0/12")


# ------------------------------------------------------------------ TOTP (RFC 6238, HMAC-SHA1, 30 s)
def generate_secret() -> str:
    """160 bit, base32 zonder opvulling (zoals authenticator-apps verwachten)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _key(secret_b32: str) -> bytes:
    cleaned = secret_b32.strip().replace(" ", "").upper()
    return base64.b32decode(cleaned + "=" * (-len(cleaned) % 8))


def totp_at(secret_b32: str, step: int, digits: int = TOTP_DIGITS) -> str:
    mac = hmac.new(_key(secret_b32), struct.pack(">Q", step), hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    value = struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10**digits)).zfill(digits)


def time_step(now: datetime) -> int:
    return int(now.timestamp()) // TOTP_PERIOD


def verify_totp(secret_b32: str, code: str, now: datetime, last_step: int | None) -> int | None:
    """Geeft de gebruikte tijdstap terug als de code klopt en nieuwer is dan ``last_step``; anders ``None``."""
    code = "".join(ch for ch in code if not ch.isspace())
    if len(code) != TOTP_DIGITS or not code.isdigit():
        return None
    current = time_step(now)
    for step in range(current - TOTP_WINDOW, current + TOTP_WINDOW + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(totp_at(secret_b32, step), code):
            return step
    return None


def otpauth_uri(secret_b32: str, account: str) -> str:
    label = quote(f"{ISSUER}:{account}")
    return f"otpauth://totp/{label}?secret={secret_b32}&issuer={quote(ISSUER)}&algorithm=SHA1&digits=6&period=30"


# ------------------------------------------------------------------ bron-IP
def _address(ip: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return None
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        return addr.ipv4_mapped
    return addr


def is_private_source(ip: str) -> bool:
    """RFC 1918, 100.64.0.0/10 en fc00::/7; loopback, link-local en publieke adressen tellen niet."""
    addr = _address(ip)
    return addr is not None and any(addr.version == n.version and addr in n for n in PRIVATE_NETWORKS)


def looks_like_docker_gateway(ip: str) -> bool:
    """Heuristiek: ``172.16.0.0/12`` eindigend op ``.1`` is meestal de bridge-gateway van Docker (NIET GEVALIDEERD)."""
    addr = _address(ip)
    return isinstance(addr, ipaddress.IPv4Address) and addr in DOCKER_BRIDGE and addr.packed[-1] == 1


# ------------------------------------------------------------------ accountstatus
def account(db: Session) -> User | None:
    return db.scalars(select(User).where(User.break_glass.is_(True)).order_by(User.created_at)).first()


def is_working(user: User | None) -> bool:
    return (
        user is not None
        and user.break_glass
        and not user.disabled
        and user.role == "admin"
        and user.totp_secret_ref is not None
        and user.totp_confirmed_at is not None
    )


def session_minutes(user: User, settings: Settings) -> int:
    minutes = user.break_glass_session_minutes or settings.break_glass_session_minutes_default
    return max(5, min(240, minutes))


def status(db: Session, settings: Settings, now: datetime | None = None) -> dict[str, Any]:
    now = now or utcnow()
    user = account(db)
    working = is_working(user)
    reconfirm_after = timedelta(days=settings.break_glass_reconfirm_days)
    if user is None:
        acc = None
    else:
        last_confirm = user.break_glass_reconfirmed_at or user.totp_confirmed_at
        acc = {
            "id": str(user.id),
            "username": user.username,
            "uitgeschakeld": user.disabled,
            "totp_ingesteld": user.totp_confirmed_at is not None,
            "totp_wacht_op_bevestiging": user.totp_secret_ref is not None and user.totp_confirmed_at is None,
            "sessieduur_minuten": session_minutes(user, settings),
            "rotatie_vereist": user.break_glass_rotation_required,
            "laatst_gebruikt": iso(user.break_glass_last_used_at),
            "laatst_bevestigd": iso(last_confirm),
            # Herbevestiging elke 90 dagen is een melding, nooit een blokkade (geen lock-out precies bij nood).
            "herbevestiging_nodig": last_confirm is None or now - last_confirm > reconfirm_after,
        }
    return {
        "noodaccount": acc,
        "werkend": working,
        "oidc_verplicht_mogelijk": working,
        "toelichting": "Noodlogin: wachtwoord (≥ 20 tekens) plus TOTP, alleen vanaf privé-adressen, sessie hooguit "
        f"{settings.break_glass_session_minutes_default} minuten (instelbaar 5–240). Zonder werkend noodaccount kan "
        "'OIDC verplicht' niet aan.",
    }


def assert_oidc_required_allowed(db: Session) -> None:
    """Contract 1.2 §4.1: aanroepen voordat 'OIDC verplicht' aangaat (B13; OIDC bestaat nog niet)."""
    if not is_working(account(db)):
        raise HubError(
            409,
            "break_glass_required",
            "'OIDC verplicht' kan pas aan als er een werkend noodaccount is (wachtwoord + bevestigde TOTP).",
        )


def selftest(db: Session, source_ip: str, now: datetime | None = None) -> dict[str, Any]:
    """Deterministische controle zonder in te loggen en zonder mutatie (contract 1.2 §4.1)."""
    now = now or utcnow()
    user = account(db)
    checks: list[dict[str, Any]] = [
        {
            "naam": "noodaccount",
            "status": "ok" if user is not None and not user.disabled else "fout",
            "detail": "aanwezig" if user is not None else "geen noodaccount ingesteld",
        },
        {
            "naam": "totp",
            "status": "ok" if user is not None and user.totp_confirmed_at is not None else "fout",
            "detail": "ingesteld en bevestigd"
            if user is not None and user.totp_confirmed_at is not None
            else "TOTP niet ingesteld of nog niet bevestigd",
        },
        {
            "naam": "bereik_binnen",
            "adres": SELFTEST_INSIDE,
            "prive": is_private_source(SELFTEST_INSIDE),
            "status": "ok" if is_private_source(SELFTEST_INSIDE) else "fout",
        },
        {
            "naam": "bereik_buiten",
            "adres": SELFTEST_OUTSIDE,
            "prive": is_private_source(SELFTEST_OUTSIDE),
            "status": "ok" if not is_private_source(SELFTEST_OUTSIDE) else "fout",
        },
    ]
    private = is_private_source(source_ip)
    gateway = looks_like_docker_gateway(source_ip)
    checks.append(
        {
            "naam": "bron_ip",
            "adres": source_ip,
            "prive": private,
            "lijkt_docker_gateway": gateway,
            "status": "waarschuwing" if gateway or not private else "ok",
            "detail": "Dit adres lijkt de gateway van het Docker-netwerk; dan ziet de Hub niet het echte adres van "
            "je apparaat en is de privé-controle zwakker (NIET GEVALIDEERD op de NAS)."
            if gateway
            else ("Dit adres telt als privé." if private else "Dit adres telt niet als privé: noodlogin geweigerd."),
        }
    )
    hard = [c for c in checks if c["naam"] != "bron_ip"]
    return {
        "resultaat": "ok" if all(c["status"] == "ok" for c in hard) else "niet_ok",
        "controles": checks,
        "zonder_authenticator_en_netwerk": True,
        "gemeten_op": iso(now),
    }
