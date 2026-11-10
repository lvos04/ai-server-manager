"""Weergave van incidenten en hun gebeurtenissen (API, supportbundel). Gevoelige details alleen voor admin."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from hub.incidents.hypothesis import unknown
from hub.incidents.rules import ernst_label
from hub.models import Incident, IncidentEvent
from hub.security import ROLE_RANK, Role
from hub.timeutil import iso

ROL_ACTIES: tuple[tuple[str, Role], ...] = (
    ("bekijken", Role.viewer),
    ("bewijs", Role.viewer),
    ("erkennen", Role.operator),
    ("snoozen", Role.operator),
    ("oplossen", Role.operator),
    ("notitie", Role.operator),
    ("supportbundel", Role.operator),
    ("onderzoek", Role.operator),
    ("herstel_voorstellen", Role.operator),
)


def acties(role: Role | None) -> list[str]:
    if role is None:
        return []
    return [a for a, need in ROL_ACTIES if ROLE_RANK[role] >= ROLE_RANK[need]]


def etag(inc: Incident) -> str:
    return f'"{inc.version}"'


def incident_dict(
    inc: Incident,
    *,
    show_sensitive: bool,
    now: datetime,
    role: Role | None = None,
    readback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hidden = inc.classificatie == "sensitive" and not show_sensitive
    actief = inc.status != "opgelost"
    return {
        "id": str(inc.id),
        "titel": inc.titel,
        "soort": inc.soort,
        "ernst": inc.ernst,
        # Contract 1.3 §7: de bronwaarde (Peil-woord) als die er is; het label volgt de vaste afbeelding.
        "ernst_bron": inc.ernst_bron,
        "ernst_label": ernst_label(inc.ernst, inc.ernst_bron),
        "status": inc.status,
        "actief": actief,
        "bron": inc.bron,
        "onderwerp": {"type": inc.onderwerp_type, "id": inc.onderwerp_id, "naam": inc.onderwerp_naam},
        "eerste_gebeurtenis": iso(inc.eerste_op),
        "laatste_gebeurtenis": iso(inc.laatste_op),
        "geopend_op": iso(inc.geopend_op),
        "aantal_gebeurtenissen": inc.aantal,
        "heropend": inc.heropend,
        "erkend": None
        if inc.erkend_op is None
        else {"door": inc.erkend_door, "op": iso(inc.erkend_op), "tot": iso(inc.erkend_tot)},
        "gesnoozed": None
        if inc.gesnoozed_tot is None or inc.gesnoozed_tot <= now
        else {"door": inc.gesnoozed_door, "tot": iso(inc.gesnoozed_tot)},
        "opgelost": None
        if inc.opgelost_op is None
        else {"door": inc.opgelost_door, "op": iso(inc.opgelost_op), "reden": inc.oplos_reden},
        "hypothese": inc.hypothese or unknown(now),
        "oorzaak_sleutel": inc.oorzaak_sleutel,
        "veilige_modus": {"actief": inc.veilige_modus, "sinds": iso(inc.veilige_modus_sinds)},
        "runbook_id": inc.runbook_id,
        "trace_ids": list(inc.trace_ids or []),
        "correlatie_ids": list(inc.correlatie_ids or []),
        "details": None if hidden else (inc.details or {}),
        "details_verborgen": hidden,
        "meldingen": inc.melding_teller,
        "laatst_gemeld_op": iso(inc.laatst_gemeld_op),
        "readback": readback,
        "acties": acties(role) if actief else [a for a in acties(role) if a in ("bekijken", "bewijs", "supportbundel")],
        "versie": inc.version,
        "bijgewerkt_op": iso(inc.bijgewerkt_op),
    }


def event_dict(e: IncidentEvent, *, show_sensitive: bool) -> dict[str, Any]:
    hidden = e.classificatie == "sensitive" and not show_sensitive
    return {
        "id": e.id,
        "soort": e.soort,
        "op": iso(e.op),
        "ontvangen_op": iso(e.ontvangen_op),
        "event_type": e.event_type,
        "bron": e.bron,
        "bron_ref": e.bron_ref,
        "samenvatting": e.samenvatting,
        "details": None if hidden else (e.details or {}),
        "details_verborgen": hidden,
        "trace_id": e.trace_id,
        "actor": e.actor,
    }
