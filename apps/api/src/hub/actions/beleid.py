"""Het risicobeleid in de Hub: één keer laden (in het image read-only ingebakken) en tonen via ``GET /api/v1/policy``.

Onleesbaar of ongeldig beleid → ``policy_niet_beschikbaar`` (503): de Hub stelt dan niets voor en voert niets uit.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from asm_policy import Policy, PolicyError, load_policy
from asm_policy.loader import default_policy_dir, is_read_only

from hub.errors import HubError


@lru_cache(maxsize=1)
def _geladen() -> Policy:
    return load_policy(default_policy_dir())


def get_policy() -> Policy:
    try:
        return _geladen()
    except PolicyError as exc:
        raise HubError(
            503,
            "policy_niet_beschikbaar",
            "Het risicobeleid is onleesbaar; de Hub stelt geen acties voor en voert niets uit.",
            {"fout": type(exc).__name__},
        ) from None


def weergave(policy: Policy) -> dict[str, Any]:
    """Het beleid zoals de UI het toont: wat mag, in welke klasse, en wat nooit mag (geen geheimen)."""
    return {
        "policy_hash": policy.hash,
        "read_only": is_read_only(policy.bron),
        "bestanden": list(policy.files),
        "acties": [
            {
                "action_id": a.action_id,
                "omschrijving": a.omschrijving,
                "uitvoerder": a.uitvoerder,
                "doel": a.doel,
                "risk_class": a.klasse,
                "risk_class_kritiek": a.klasse_kritiek,
                "goedkeuring_nodig": a.klasse in ("R2", "R3"),
                "requires_backup": a.requires_backup,
                "ai_mag_voorstellen": a.ai_mag_voorstellen,
                "opslagmutatie": a.opslagmutatie,
                "cooldown_seconden": a.cooldown_seconden,
                "max_per_uur": a.max_per_uur,
            }
            for a in sorted(policy.acties.values(), key=lambda x: x.action_id)
        ],
        "verboden": [{"id": v.id, "code": v.code, "reden": v.reden_nl} for v in policy.verboden]
        + [{"id": policy.boiler_id, "code": policy.boiler_code, "reden": policy.boiler_reden}],
        "gereserveerd": [{"id": g.id, "code": g.code, "reden": g.reden_nl} for g in policy.gereserveerd],
        "dynamisch": [{"id": r.id, "code": r.code, "reden": r.reden_nl} for r in policy.dynamisch.values()],
        "kritieke_apps": sorted(policy.kritiek),
        "beschermd": [
            {"id": b.id, "app": b.app, "acties": list(b.acties) if b.acties is not None else None, "reden": b.reden_nl}
            for b in policy.beschermd
        ],
    }
