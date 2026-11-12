"""Canonieke JSON en hashes (contract 1.3 §8: "Ed25519 over canonieke JSON, sleutels gesorteerd, UTF-8, geen spaties").

Precies: ``json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`` als UTF-8. Toegestane waarden:
``dict`` met tekstsleutels, ``list``, ``str``, ``int``, ``bool`` en ``None``. **Geen kommagetallen** (``float``): die
hebben per taal een andere tekstvorm en zouden een handtekening onvoorspelbaar maken; ze worden geweigerd. Een tekst
wordt niet genormaliseerd (geen NFC): wat ondertekend is, is precies wat verstuurd wordt. Een tekst die geen geldige
UTF-8 is (een losse surrogaat, bv. ``"\\ud800"`` uit JSON) en een waarde dieper dan :data:`MAX_DIEPTE` geven ook een
:class:`CanonicalError` (S-P2-010, R-VEILIG-6 en R-VEILIG-1): een nette weigering, nooit een onverwachte fout.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Hooguit zoveel objecten of lijsten diep (het buitenste object is diepte 0). Dezelfde grens geldt voor de doorzoekers
# van het beleid (boiler, EX47, kluisverwijzingen): die kijken tot hier en weigeren dieper (dicht bij twijfel).
MAX_DIEPTE = 32


class CanonicalError(ValueError):
    """De waarde kan niet canoniek worden weergegeven (bv. een kommagetal of een niet-tekstsleutel)."""


class TeDiepGenest(CanonicalError):
    """De waarde is dieper genest dan :data:`MAX_DIEPTE`; een doorzoeker weigert dan in plaats van stil te stoppen."""


def _utf8(text: str) -> None:
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        raise CanonicalError("tekst is geen geldige UTF-8 (losse surrogaat)") from None


def _check(value: Any, depth: int = 0) -> None:
    if depth > MAX_DIEPTE:
        raise TeDiepGenest("te diep genest")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        _utf8(value)
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
            _utf8(key)
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
