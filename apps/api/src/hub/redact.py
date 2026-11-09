"""Redactie van geheimen in logs, events, evidence en API-uitvoer (contract §3)."""

from __future__ import annotations

import re
from typing import Any

SECRET_KEY_RE = re.compile(
    r"(pass(word|wd)?|secret|token|api[_-]?key|apikey|authorization|cookie|credential|private|client_secret|"
    r"refresh|access_key|session|signature|bearer|vault)",
    re.IGNORECASE,
)
REDACTED = "***"
_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}")
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
