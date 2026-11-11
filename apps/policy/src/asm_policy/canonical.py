"""Canonieke JSON en hashes (contract 1.3 §8: "Ed25519 over canonieke JSON, sleutels gesorteerd, UTF-8, geen spaties").

Precies: ``json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`` als UTF-8. Toegestane waarden:
``dict`` met tekstsleutels, ``list``, ``str``, ``int``, ``bool`` en ``None``. **Geen kommagetallen** (``float``): die
hebben per taal een andere tekstvorm en zouden een handtekening onvoorspelbaar maken; ze worden geweigerd. Een tekst
wordt niet genormaliseerd (geen NFC): wat ondertekend is, is precies wat verstuurd wordt.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


class CanonicalError(ValueError):
    """De waarde kan niet canoniek worden weergegeven (bv. een kommagetal of een niet-tekstsleutel)."""


def _check(value: Any, depth: int = 0) -> None:
    if depth > 32:
        raise CanonicalError("te diep genest")
    if value is None or isinstance(value, bool | str):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        raise CanonicalError("kommagetallen zijn niet toegestaan in ondertekende gegevens")
    if isinstance(value, list | tuple):
        for item in value:
            _check(item, depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalError("alleen tekstsleutels")
            _check(item, depth + 1)
        return
    raise CanonicalError(f"type {type(value).__name__} is niet toegestaan")


def canonical_json(value: Any) -> bytes:
    """Canonieke UTF-8-bytes van ``value`` (zie de moduletekst)."""
    _check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    """``"sha256:<64 hex>"`` over de canonieke JSON van ``value``."""
    return "sha256:" + sha256_hex(canonical_json(value))
