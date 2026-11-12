"""Het risicobeleid in de Hub: één keer laden (in het image read-only ingebakken) en tonen via ``GET /api/v1/policy``.

Onleesbaar of ongeldig beleid → ``policy_niet_beschikbaar`` (503): de Hub stelt dan niets voor en voert niets uit.
De weergave toont naast de yaml ook de twee vaste regels van de engine (``STOP-EENRICHTING`` en
``DOEL-ONHERKENBAAR``) en per app-actie de klasse voor een Custom App, uitgerekend met de engine zelf (S-P2-010).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from asm_policy import Policy, PolicyError, load_policy
from asm_policy.engine import DOEL_ONHERKENBAAR, STOP_EENRICHTING, STOP_EENRICHTING_REDEN, Herkenning, classify
from asm_policy.loader import ActieDef, default_policy_dir, is_read_only

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


# Een draaiende Custom App (ix-app of compose): wat erin draait is te zien, maar na een stop niet meer.
CUSTOM_APP = Herkenning((), True, False)


def _klasse_custom_app(policy: Policy, a: ActieDef) -> str | None:
    """De klasse van deze actie op een draaiende Custom App volgens de engine; ``None`` als het doel geen app is."""
    if a.doel != "app":
        return None
    c = classify(policy, action_id=a.action_id, target={}, parameters={}, actor_type="user", herkend_als=CUSTOM_APP)
    return c.risk_class


def _engine_regels(policy: Policy, custom: dict[str, str | None]) -> list[dict[str, Any]]:
    app_acties = sorted(a.action_id for a in policy.acties.values() if a.doel == "app")
    hoger = sorted(aid for aid, k in custom.items() if k is not None and k != policy.acties[aid].klasse)
    klassen = {custom[aid] for aid in hoger}
    klasse = klassen.pop() if len(klassen) == 1 else None
    return [
        {
            "id": STOP_EENRICHTING,
            "acties": hoger,
            "geldt_voor": "custom_app",
            "risk_class": klasse,
            "goedkeuring_nodig": klasse in ("R2", "R3"),
            "reden": STOP_EENRICHTING_REDEN,
        },
        {
            "id": DOEL_ONHERKENBAAR.id,
            "code": DOEL_ONHERKENBAAR.code,
            "acties": app_acties,
            "geldt_voor": "bestaande_app_niet_herkenbaar",
            "reden": DOEL_ONHERKENBAAR.reden_nl,
        },
    ]


def weergave(policy: Policy) -> dict[str, Any]:
    """Het beleid zoals de UI het toont: wat mag, in welke klasse, en wat nooit mag (geen geheimen). Naast de yaml ook
    de vaste engine-regels en per app-actie de klasse voor een Custom App (``risk_class_custom_app``)."""
    custom = {a.action_id: _klasse_custom_app(policy, a) for a in policy.acties.values()}
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
                "risk_class_custom_app": custom[a.action_id],
                "goedkeuring_nodig_custom_app": (
                    custom[a.action_id] in ("R2", "R3") if custom[a.action_id] is not None else None
                ),
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
        "engine_regels": _engine_regels(policy, custom),
        "kritieke_apps": sorted(policy.kritiek),
        "beschermd": [
            {"id": b.id, "app": b.app, "acties": list(b.acties) if b.acties is not None else None, "reden": b.reden_nl}
            for b in policy.beschermd
        ],
    }
