"""Gezondheidsmodel per app (B09-002, ADR-0016): componenten → ``healthy|degraded|down|unknown`` met ``observed_at``.

Componentsoorten:
- ``truenas``: staat uit ``app.query`` (alleen bij een verse inventaris). ``STOPPED``/``CRASHED`` → down,
  ``DEPLOYING``/``STOPPING`` → degraded, ``RUNNING`` telt **niet** als bewijs van gezond (alleen "draait").
- ``buitenkant``: bereikbaarheid van buitenaf (Uptime Kuma-monitors die aan de app gekoppeld zijn).
- ``binnenkant``: de app zelf meldt of haar werk doorgaat (heartbeat, connector-health §6, worker van de Hub).

Regels:
1. Een component ouder dan zijn TTL is ``unknown`` (``verouderd``), nooit de laatst bekende status.
2. ``down`` wint, dan ``degraded``.
3. ``healthy`` vraagt een verse gezonde buiten- óf binnenkant-controle; heeft het profiel ``binnenkant_vereist``, dan
   bovendien een verse gezonde binnenkant (anders ``unknown``: een app die 200 geeft maar geen jobs uitvoert mag
   nooit groen worden).
4. Een app die niet meer in een verse inventaris staat, is ``unknown`` (``niet_meer_in_inventaris``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from hub.timeutil import iso, utcnow

STATUSES: tuple[str, ...] = ("healthy", "degraded", "down", "unknown")
_SEVERITY = {"down": 3, "degraded": 2, "healthy": 1, "unknown": 0}

TRUENAS_STATE = {
    "RUNNING": ("healthy", None),
    "STOPPED": ("down", "app_gestopt"),
    "CRASHED": ("down", "app_gecrasht"),
    "DEPLOYING": ("degraded", "app_start_op"),
    "STOPPING": ("degraded", "app_stopt"),
}

MELDINGEN: dict[str, str] = {
    "app_gestopt": "De app is gestopt in TrueNAS.",
    "app_gecrasht": "De app is gecrasht in TrueNAS.",
    "app_start_op": "De app wordt gestart.",
    "app_stopt": "De app wordt gestopt.",
    "inventaris_verouderd": "De TrueNAS-inventaris is verouderd of onbekend; de staat van de app is niet bekend.",
    "niet_meer_in_inventaris": "De app staat niet meer in de laatste TrueNAS-inventaris.",
    "geen_gezondheidsbron": "Er is geen verse controle van buitenaf of van binnenuit gekoppeld.",
    "binnenkant_ontbreekt": "De app voert zelf taken uit; zonder verse binnenkant-controle (heartbeat of "
    "connector-health) is gezond niet vast te stellen.",
    "binnenkant_niet_gebouwd": "De Hub-adapter voor de binnenkant van deze bestaande app (read-model met gescopete "
    "sleutel) volgt in fase P3; gezond is daarom nog niet vast te stellen.",
    "verouderd": "De laatste meting is ouder dan toegestaan en geldt daarom als onbekend.",
    "status_onbekend": "TrueNAS meldt een onbekende staat voor deze app.",
    "worker_staat_stil": "De worker van de app meldt zich niet meer.",
    "jobs_staan_stil": "Er staan taken klaar, maar er wordt al te lang niets afgerond.",
    "bron_onbereikbaar": "De monitoringbron is niet bereikbaar.",
    "onderhoud": "De monitor staat in onderhoud.",
    "monitor_wacht": "De monitor wacht op bevestiging (pending).",
    "monitor_down": "De monitor meldt dat de app niet bereikbaar is.",
    "dienst_onbereikbaar": "De dienst is niet bereikbaar voor de Hub.",
    "dienst_weigerde": "De dienst weigerde de Hub (aanmelding of koppeling); gezond is niet vast te stellen.",
    "antwoord_ongeldig": "De dienst gaf een ongeldig gezondheidsantwoord.",
    "eerste_fout_grace": "Eén mislukte controle: nog binnen de marge; bij de volgende fout telt de app als down.",
    "dienst_meldt_down": "De dienst meldt zelf dat hij niet werkt.",
    "dienst_meldt_degraded": "De dienst meldt zelf dat hij verminderd werkt.",
    "controle_faalt": "Een controle van de dienst zelf faalt.",
    "capability_unavailable": "De dienst biedt (nog) geen gezondheidsroute aan; gezond is niet vast te stellen.",
    "dienst_adres_onbekend": "Het adres van de dienst is niet gemeten (NAS-adres uit D03 + hostpoort uit de "
    "inventaris).",
    "bron_credential_geweigerd": "De monitoringbron weigerde de API-key of het wachtwoord; de monitors gelden als "
    "onbekend tot er geldige gegevens zijn (nooit open of 'nog gezond').",
}


@dataclass
class Component:
    soort: str  # truenas | buitenkant | binnenkant
    bron: str
    status: str
    reason_code: str | None
    observed_at: datetime | None
    detail: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "soort": self.soort,
            "bron": self.bron,
            "status": self.status,
            "reason_code": self.reason_code,
            "melding": MELDINGEN.get(self.reason_code or "", "") if self.reason_code else "",
            "observed_at": iso(self.observed_at),
            "detail": self.detail,
            **self.extra,
        }


def freshen(c: Component, ttl_seconds: float, now: datetime | None = None) -> Component:
    """Een component ouder dan zijn TTL wordt ``unknown`` (``verouderd``); de laatste status blijft zichtbaar. Was hij
    al ``unknown`` met een eigen reden (bv. een geweigerde key), dan blijft die reden staan."""
    now = now or utcnow()
    stale = c.observed_at is None or (now - c.observed_at).total_seconds() > ttl_seconds
    if not stale:
        return c
    if c.status == "unknown":
        return Component(
            c.soort,
            c.bron,
            "unknown",
            c.reason_code or "verouderd",
            c.observed_at,
            c.detail,
            {**c.extra, "verouderd": True},
        )
    return Component(
        c.soort,
        c.bron,
        "unknown",
        "verouderd",
        c.observed_at,
        c.detail,
        {**c.extra, "laatste_status": c.status, "verouderd": True},
    )


def _aggregate(components: list[Component]) -> Component | None:
    """Binnen één soort: down > degraded > healthy > unknown (unknown alleen als niets anders bekend is)."""
    if not components:
        return None
    return max(components, key=lambda c: (_SEVERITY[c.status], c.observed_at or datetime.min.replace(tzinfo=UTC)))


def evaluate(
    components: list[Component],
    *,
    aanwezig: bool,
    binnenkant_vereist: bool,
    binnenkant_bron: str | None,
) -> dict[str, Any]:
    by_kind: dict[str, list[Component]] = {}
    for c in components:
        by_kind.setdefault(c.soort, []).append(c)
    t = _aggregate(by_kind.get("truenas", []))
    b = _aggregate(by_kind.get("buitenkant", []))
    i = _aggregate(by_kind.get("binnenkant", []))
    checked = [c for c in (b, i) if c is not None and c.observed_at is not None]
    laatst_getest = max((c.observed_at for c in checked if c.observed_at), default=None)

    def result(status: str, reason: str | None, cause: Component | None = None) -> dict[str, Any]:
        observed = max((c.observed_at for c in (t, b, i) if c is not None and c.observed_at), default=None)
        return {
            "status": status,
            "reason_code": reason,
            "melding": MELDINGEN.get(reason or "", "") if reason else "",
            "observed_at": iso(observed),
            "laatst_getest": iso(laatst_getest),
            "oorzaak": cause.bron if cause is not None else None,
            "binnenkant_vereist": binnenkant_vereist,
            "componenten": [c.as_dict() for c in components],
        }

    if not aanwezig:
        return result("unknown", "niet_meer_in_inventaris")
    for wanted in ("down", "degraded"):
        for comp in (t, b, i):
            if comp is not None and comp.status == wanted:
                return result(wanted, comp.reason_code, comp)
    healthy_b = b is not None and b.status == "healthy"
    healthy_i = i is not None and i.status == "healthy"
    if binnenkant_vereist and not healthy_i:
        if binnenkant_bron == "adapter_p3":
            return result("unknown", "binnenkant_niet_gebouwd")
        if i is None:
            return result("unknown", "binnenkant_ontbreekt")
        return result("unknown", i.reason_code or "verouderd", i)
    if not (healthy_b or healthy_i):
        stale = next((c for c in (b, i) if c is not None), None)
        if stale is not None:
            return result("unknown", stale.reason_code or "verouderd", stale)
        if t is not None and t.status == "unknown":
            return result("unknown", t.reason_code or "inventaris_verouderd", t)
        return result("unknown", "geen_gezondheidsbron")
    return result("healthy", None)


def status_value(status: str) -> float | None:
    """Voor tijdreeksen: healthy 1, degraded 0.5, down 0; unknown → geen meting (gat in de reeks)."""
    return {"healthy": 1.0, "degraded": 0.5, "down": 0.0}.get(status)
