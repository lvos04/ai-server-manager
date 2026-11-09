"""Redactie van geheimen in logs, events, evidence en API-uitvoer (contract §3, B09-004).

Twee niveaus:
- ``redact`` / ``redact_text``: voor gestructureerde gegevens (audit, events, evidence). Waarden onder
  geheim-achtige sleutels worden ``***``; in tekst: ``Bearer …`` en inloggegevens in URL's.
- ``redact_log_text``: strenger beleid voor de log-index, supportbundels en alles wat ooit naar AI-telemetrie zou
  kunnen gaan: daarnaast ``sleutel=waarde``-geheimen, JWT's, tokens met bekende voorvoegsels, PEM-blokken, lange
  hex-/base64-reeksen, e-mailadressen en **IP-adressen** (alleen de soort blijft: privé/publiek/lokaal), plus de
  exacte waarde van geheimen die de Hub zelf kent (via ``SecretMatcher``: alleen SHA-256-vingerafdrukken in het
  geheugen, nooit de waarden).
"""

from __future__ import annotations

import hashlib
import ipaddress
import math
import re
from collections.abc import Iterable
from typing import Any

SECRET_KEY_RE = re.compile(
    r"(pass(word|wd)?|secret|token|api[_-]?key|apikey|authorization|cookie|credential|private|client_secret|"
    r"refresh|access_key|session|signature|bearer|vault|totp|code_verifier)",
    re.IGNORECASE,
)
REDACTED = "***"
_BEARER_RE = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_URL_CRED_RE = re.compile(r"(?i)(\w+://)([^:/@\s]+):([^@\s]+)@")


def redact_text(text: str) -> str:
    text = _BEARER_RE.sub(r"\1 " + REDACTED, text)
    return _URL_CRED_RE.sub(r"\1\2:" + REDACTED + "@", text)


def redact(value: Any, *, depth: int = 0) -> Any:
    """Vervang waarden onder geheim-achtige sleutels door ``***``; recursief, met dieptegrens."""
    if depth > 12:
        return REDACTED
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if isinstance(k, str) and SECRET_KEY_RE.search(k) and not isinstance(v, bool):
                out[k] = REDACTED if v not in (None, "") else v
            else:
                out[k] = redact(v, depth=depth + 1)
        return out
    if isinstance(value, list):
        return [redact(v, depth=depth + 1) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


# ------------------------------------------------------------------ strenger beleid voor logs en supportbundels
_PEM_RE = re.compile(r"-----BEGIN [A-Z0-9 ]+-----.*?(-----END [A-Z0-9 ]+-----|$)", re.S)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{0,}")
_KV_RE = re.compile(
    r"(?i)(\b(?:pass(?:word|wd)?|secret|client_secret|token|access_token|refresh_token|id_token|api[_-]?key|apikey|"
    r"x-api-key|x-gotify-key|authorization|cookie|set-cookie|credential|session|signature|private[_-]?key|totp|"
    r"wachtwoord|geheim|sleutel|api-sleutel|pincode|herstelcode|"
    r"code_verifier)\b[\"']?\s*[:=]\s*[\"']?)([^\s\"',;&}]+)"
)
_QUERY_RE = re.compile(
    r"(?i)([?&](?:code|state|nonce|session_state|token|access_token|id_token|key|api_key|apikey|secret|password|"
    r"client_secret|sig|signature)=)([^&#\s\"']+)"
)
_PREFIX_RE = re.compile(
    r"\b(?:svc|enr|ses|csrf|ghp|gho|ghs|ghu|github_pat|xox[abprs]|sk|rk|pk|uk\d+)_[A-Za-z0-9_-]{8,}"
    r"|\bAKIA[0-9A-Z]{16}\b"
)
_HEX_RE = re.compile(r"(?<![A-Za-z0-9:])(?<!sha256:)[A-Fa-f0-9]{32,}(?![A-Za-z0-9])")
_B64_RE = re.compile(r"(?<![A-Za-z0-9+/_-])[A-Za-z0-9+/_-]{32,}={0,2}")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IPV4_RE = re.compile(
    r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?![\d.])"
)
_IPV6_RE = re.compile(
    r"(?<![\w:])(?:(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,6}:(?:[0-9A-Fa-f]{1,4})?"
    r"|::(?:[0-9A-Fa-f]{1,4}:){0,5}[0-9A-Fa-f]{1,4})(?![\w:])"
)
_TOKEN_SPLIT_RE = re.compile(r"[\s\"'=,;&?<>()\[\]{}]+")
MIN_SECRET_LEN = 8
# Strenger dan SECRET_KEY_RE: ook Nederlandse sleutelnamen (alleen voor de log-index en supportbundels).
LOG_SECRET_KEY_RE = re.compile(SECRET_KEY_RE.pattern + r"|wachtwoord|geheim|sleutel|pincode|herstelcode", re.IGNORECASE)


def _entropy(text: str) -> float:
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(text)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def _maybe_secret(m: re.Match[str]) -> str:
    """Lange reeks met cijfers, hoofd- en kleine letters, weinig scheidingstekens en hoge entropie → vermoedelijk geheim
    (een bestandsnaam of identifier met veel ``_``/``-`` blijft staan)."""
    s = m.group(0)
    core = s.rstrip("=")
    seps = sum(1 for ch in core if ch in "_-")
    mixed = any(c.isdigit() for c in core) and any(c.isupper() for c in core) and any(c.islower() for c in core)
    if mixed and seps <= len(core) // 8 and _entropy(core) >= 4.0:
        return "[geheim?]"
    return s


def ip_label(text: str) -> str:
    try:
        ip = ipaddress.ip_address(text)
    except ValueError:
        return "[adres]"
    if ip.is_loopback or ip.is_link_local or ip.is_unspecified:
        return "[ip-lokaal]"
    if ip.is_private or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10")):
        return "[ip-privé]"
    return "[ip-publiek]"


class SecretMatcher:
    """Herkent de exacte waarde van bekende geheimen aan hun SHA-256 (de waarden zelf worden nooit bewaard)."""

    def __init__(self, fingerprints: Iterable[str] = ()) -> None:
        self.fingerprints = {f for f in fingerprints if f}

    @staticmethod
    def fingerprint(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def redact(self, text: str) -> str:
        if not self.fingerprints:
            return text
        out = text
        for word in set(_TOKEN_SPLIT_RE.split(text)):
            if len(word) >= MIN_SECRET_LEN and self.fingerprint(word) in self.fingerprints:
                out = out.replace(word, REDACTED)
        return out


def redact_log_text(text: str, matcher: SecretMatcher | None = None, *, max_len: int = 2000) -> str:
    """Streng schonen voor de log-index; daarna inkorten tot ``max_len`` tekens."""
    if matcher is not None:
        text = matcher.redact(text)
    text = _PEM_RE.sub("[pem]", text)
    text = _JWT_RE.sub("[jwt]", text)
    text = redact_text(text)
    text = _KV_RE.sub(lambda m: m.group(1) + REDACTED, text)
    text = _QUERY_RE.sub(lambda m: m.group(1) + REDACTED, text)
    text = _PREFIX_RE.sub("[token]", text)
    text = _EMAIL_RE.sub("[e-mail]", text)
    text = _IPV4_RE.sub(lambda m: ip_label(m.group(0)), text)
    text = _IPV6_RE.sub(lambda m: ip_label(m.group(0)), text)
    text = _HEX_RE.sub("[hex]", text)
    text = _B64_RE.sub(_maybe_secret, text)
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def redact_log_value(
    value: Any, matcher: SecretMatcher | None = None, *, depth: int = 0, max_items: int = 50, max_str: int = 500
) -> Any:
    """Gestructureerde velden volgens hetzelfde strenge beleid (sleutels én waarden)."""
    if depth > 8:
        return REDACTED
    kw = {"depth": depth + 1, "max_items": max_items, "max_str": max_str}
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in list(value.items())[:max_items]:
            key = redact_log_text(str(k), matcher, max_len=64)
            if LOG_SECRET_KEY_RE.search(str(k)) and not isinstance(v, bool | dict | list):
                out[key] = REDACTED if v not in (None, "") else v
            else:
                out[key] = redact_log_value(v, matcher, **kw)
        return out
    if isinstance(value, list | tuple):
        return [redact_log_value(v, matcher, **kw) for v in list(value)[:max_items]]
    if isinstance(value, str):
        return redact_log_text(value, matcher, max_len=max_str)
    if isinstance(value, bool | int | float) or value is None:
        return value
    return redact_log_text(str(value), matcher, max_len=200)
