"""Noodlogin (break-glass) van de Hub (contract 1.3 §4.1): TOTP (RFC 6238), privé-bereiken en accountstatus.

Privé = RFC 1918 en ``fc00::/7``. ``100.64.0.0/10`` (CGNAT, ook Tailscale) telt standaard **niet** als privé: met
Tailscale-delen kunnen gasten in dat bereik zitten. Een beheerder kan het in de Hub-UI toestaan (``hub_setting``
``noodlogin.cgnat_toestaan``; audit + waarschuwing); dat is geen ``action_id`` en de AI kan het niet voorstellen.

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
from hub.models import HubSetting, User
from hub.timeutil import iso, utcnow

TOTP_PERIOD = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1  # één tijdstap speling naar voren en naar achteren (klokverschil telefoon)
ISSUER = "TrueNAS Home Platform"  # productnaam (besluit gebruiker O-07)

PRIVATE_NETWORKS = tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7"))
CGNAT = ipaddress.ip_network("100.64.0.0/10")
SETTING_CGNAT = "noodlogin.cgnat_toestaan"
CGNAT_WAARSCHUWING = (
    "Sta 100.64.0.0/10 alleen toe als je Tailscale niet met anderen deelt: met Tailscale-delen kunnen gasten in dit "
    "bereik zitten en dan de noodlogin bereiken."
)
# Deterministische zelftest: een adres binnen een privé-bereik, een documentatie-adres (RFC 5737) erbuiten en een
# adres in 100.64.0.0/10 (privé alleen als een beheerder dat heeft toegestaan).
SELFTEST_INSIDE = "10.0.0.1"
SELFTEST_OUTSIDE = "192.0.2.10"
SELFTEST_CGNAT = "100.64.0.1"
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


def is_private_source(ip: str, *, allow_cgnat: bool = False) -> bool:
    """RFC 1918 en fc00::/7; ``100.64.0.0/10`` alleen als een beheerder dat toestaat (contract 1.3 §4.1). Loopback,
    link-local en publieke adressen tellen nooit."""
    addr = _address(ip)
    if addr is None:
        return False
    if allow_cgnat and isinstance(addr, ipaddress.IPv4Address) and addr in CGNAT:
        return True
    return any(addr.version == n.version and addr in n for n in PRIVATE_NETWORKS)


def cgnat_setting(db: Session) -> dict[str, Any]:
    """Huidige stand van ``noodlogin.cgnat_toestaan`` (standaard uit)."""
    row = db.get(HubSetting, SETTING_CGNAT)
    aan = bool(row is not None and (row.waarde or {}).get("toestaan") is True)
    return {
        "toegestaan": aan,
        "gewijzigd_door": row.gewijzigd_door if row is not None else None,
        "gewijzigd_op": iso(row.gewijzigd_op) if row is not None else None,
        "waarschuwing": CGNAT_WAARSCHUWING,
    }


def cgnat_allowed(db: Session) -> bool:
    return bool(cgnat_setting(db)["toegestaan"])


def set_cgnat(db: Session, *, toestaan: bool, door: str) -> None:
    row = db.get(HubSetting, SETTING_CGNAT)
    if row is None:
        row = HubSetting(sleutel=SETTING_CGNAT, waarde={}, gewijzigd_door=door[:80])
        db.add(row)
    row.waarde = {"toestaan": toestaan}
    row.gewijzigd_op, row.gewijzigd_door = utcnow(), door[:80]


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
        "cgnat": cgnat_setting(db),
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
    cgnat = cgnat_allowed(db)
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
            "prive": is_private_source(SELFTEST_INSIDE, allow_cgnat=cgnat),
            "status": "ok" if is_private_source(SELFTEST_INSIDE, allow_cgnat=cgnat) else "fout",
        },
        {
            "naam": "bereik_buiten",
            "adres": SELFTEST_OUTSIDE,
            "prive": is_private_source(SELFTEST_OUTSIDE, allow_cgnat=cgnat),
            "status": "ok" if not is_private_source(SELFTEST_OUTSIDE, allow_cgnat=cgnat) else "fout",
        },
        {
            # Contract 1.3 §4.1: de zelftest toont of 100.64.0.0/10 meetelt (standaard niet).
            "naam": "bereik_cgnat",
            "adres": SELFTEST_CGNAT,
            "prive": is_private_source(SELFTEST_CGNAT, allow_cgnat=cgnat),
            "toegestaan_door_beheerder": cgnat,
            "status": "ok" if is_private_source(SELFTEST_CGNAT, allow_cgnat=cgnat) is cgnat else "fout",
            "detail": "100.64.0.0/10 telt als privé: toegestaan door een beheerder. " + CGNAT_WAARSCHUWING
            if cgnat
            else "100.64.0.0/10 (CGNAT, ook Tailscale) telt niet als privé (standaard).",
        },
    ]
    private = is_private_source(source_ip, allow_cgnat=cgnat)
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
