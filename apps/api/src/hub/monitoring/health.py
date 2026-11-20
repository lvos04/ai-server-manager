"""Gezondheidsmodel per app (B09-002, ADR-0016): componenten → ``healthy|degraded|down|unknown`` met ``observed_at``.

Componentsoorten:
- ``truenas``: staat uit ``app.query`` (alleen bij een verse inventaris). ``STOPPED``/``CRASHED`` → down,
  ``DEPLOYING``/``STOPPING`` → degraded, ``RUNNING`` telt **niet** als bewijs van gezond (alleen "draait").
- ``buitenkant``: bereikbaarheid van buitenaf (Uptime Kuma-monitors die aan de app gekoppeld zijn).
- ``binnenkant``: de app zelf meldt of haar werk doorgaat (heartbeat, connector-health §6, worker van de Hub).

Regels:
1. Een component ouder dan zijn TTL is ``unknown`` (``verouderd``), nooit de laatst bekende status.
2. ``down`` wint, dan ``degraded``.
3. Voor ``healthy`` zijn de inventaris en alle gekoppelde controles gezond, vers en aan de huidige instantie
   gebonden. Er is ten minste één controle en bij ``binnenkant_vereist`` ook de voorgeschreven binnenkant.
4. Een app die niet meer in een verse inventaris staat, is ``unknown`` (``niet_meer_in_inventaris``).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from hub.catalog.profiles import BINNENKANT_P3
from hub.timeutil import iso, utcnow

STATUSES: tuple[str, ...] = ("healthy", "degraded", "down", "unknown")
_SEVERITY = {"down": 3, "degraded": 2, "unknown": 1, "healthy": 0}

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
    "adapter_niet_gekoppeld": "Deze app is nog niet gekoppeld. Ga naar Instellingen → Diensten.",
    "geen_alleen_lezen_bron": "Deze app biedt nog geen bewezen alleen-lezen gezondheidsbron.",
    "meting_onbekend": "De adapter heeft nog geen gezondheidsmeting.",
    "meettijd_onbekend": "De meettijd ontbreekt of is ongeldig.",
    "doelbinding": "De Hub kan de gekoppelde app niet bevestigen.",
    "bron_token_verlopen": "De leesverbinding is verlopen. Ga naar Instellingen → Diensten.",
    "bron_token_ingetrokken": "De leesverbinding is ingetrokken. Ga naar Instellingen → Diensten.",
    # Contract 1.3 §6.2: een meting ouder dan haar max_age is unknown met reason_code meting_verouderd.
    "meting_verouderd": "De laatste meting is ouder dan toegestaan en geldt daarom als onbekend.",
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
    geldig_tot: datetime | None = None
    bevestigd_op: datetime | None = None

    def last_known(self, reason: str) -> Component:
        extra = {**self.extra, "verouderd": True}
        if self.status != "unknown":
            extra["laatste_status"] = self.status
        return replace(self, status="unknown", reason_code=reason, extra=extra, geldig_tot=None)

    def as_dict(self) -> dict[str, Any]:
        return {
            "soort": self.soort,
            "bron": self.bron,
            "status": self.status,
            "reason_code": self.reason_code,
            "melding": MELDINGEN.get(self.reason_code or "", "") if self.reason_code else "",
            "observed_at": iso(self.observed_at),
            "geldig_tot": iso(self.geldig_tot),
            "detail": self.detail,
            **self.extra,
        }


def freshen(c: Component, ttl_seconds: float, now: datetime | None = None) -> Component:
    """Een component ouder dan zijn TTL wordt ``unknown`` (``meting_verouderd``, contract 1.3 §6.2); de laatste status
    blijft zichtbaar als "laatst bekend". Was hij
    al ``unknown`` met een eigen reden (bv. een geweigerde key), dan blijft die reden staan."""
    now = now or utcnow()
    if c.observed_at is None or c.observed_at.tzinfo is None or c.observed_at > now:
        return replace(c, status="unknown", reason_code=c.reason_code or "meettijd_onbekend", observed_at=None)
    deadline = c.observed_at + timedelta(seconds=ttl_seconds)
    if now > deadline:
        return c.last_known((c.reason_code if c.status == "unknown" else None) or "meting_verouderd")
    return replace(c, geldig_tot=deadline)


def evaluate(
    components: list[Component],
    *,
    aanwezig: bool,
    binnenkant_vereist: bool,
    binnenkant_bron: str | None,
    now: datetime,
    identiteit_gevolgd: bool = True,
    identiteit_sinds: datetime | None = None,
) -> dict[str, Any]:
    """Beslis voor lijst, detail en componenten op de laatste poging, de brongrens en de bevestigde instantie."""

    def bevestigd(c: Component) -> bool:
        return (
            identiteit_gevolgd
            and c.bevestigd_op is not None
            and c.bevestigd_op.tzinfo is not None
            and c.bevestigd_op <= now
            and (identiteit_sinds is None or c.bevestigd_op > identiteit_sinds)
        )

    def current(c: Component) -> Component:
        if c.status not in STATUSES:
            return replace(c, status="unknown", reason_code="status_onbekend", geldig_tot=None)
        if c.status != "healthy":
            return c
        if c.observed_at is None or c.observed_at.tzinfo is None or c.observed_at > now:
            return replace(c.last_known("meettijd_onbekend"), observed_at=None)
        if c.geldig_tot is None or c.geldig_tot.tzinfo is None or c.geldig_tot < now:
            return c.last_known("meting_verouderd")
        return c

    runtime = next((current(c) for c in components if c.soort == "truenas"), None)
    checks = [current(c) for c in components if c.soort != "truenas"]
    if (
        runtime is not None
        and runtime.status != "unknown"
        and (not identiteit_gevolgd or (identiteit_sinds is not None and not any(bevestigd(c) for c in checks)))
    ):
        runtime = runtime.last_known("doelbinding")

    for index, c in enumerate(checks):
        if c.status == "unknown":
            continue
        if not aanwezig or runtime is None or runtime.status in ("down", "unknown"):
            checks[index] = c.last_known((runtime.reason_code if runtime else None) or "doelbinding")
        elif (c.status == "healthy" or identiteit_sinds is not None) and not bevestigd(c):
            checks[index] = c.last_known("doelbinding")
        elif c.geldig_tot is not None and runtime.geldig_tot is not None:
            checks[index] = replace(c, geldig_tot=min(c.geldig_tot, runtime.geldig_tot))

    components = ([runtime] if runtime is not None else []) + checks
    laatst_getest = max((c.observed_at for c in checks if c.observed_at is not None), default=None)

    def result(status: str, reason: str | None, cause: Component | None = None) -> dict[str, Any]:
        used = [cause] if cause is not None else [c for c in components if c.status == status]
        observed = min((c.observed_at for c in used if c.observed_at is not None), default=None)
        if (
            status == "unknown"
            and observed is None
            and runtime is not None
            and runtime.reason_code == "inventaris_verouderd"
        ):
            observed = runtime.observed_at
        deadline = min((c.geldig_tot for c in used if c.geldig_tot is not None), default=None)
        if deadline is not None and runtime is not None and runtime.geldig_tot is not None:
            deadline = min(deadline, runtime.geldig_tot)
        return {
            "status": status,
            "reason_code": reason,
            "melding": MELDINGEN.get(reason or "", "") if reason else "",
            "observed_at": iso(observed),
            "geldig_tot": iso(deadline),
            "laatste_status": cause.extra.get("laatste_status") if cause is not None else None,
            "laatst_getest": iso(laatst_getest),
            "oorzaak": cause.bron if cause is not None else None,
            "binnenkant_vereist": binnenkant_vereist,
            "componenten": [c.as_dict() for c in components],
        }

    if not aanwezig:
        return result("unknown", "niet_meer_in_inventaris")
    if runtime is None:
        return result("unknown", "inventaris_verouderd")
    if runtime.status == "down":
        return result("down", runtime.reason_code, runtime)

    # De adapter bepaalt de reden bij gelijke toestand. Een ontbrekende vereiste
    # controle doet mee als onbekend, ook als een andere bron wel gezond is.
    candidates = list(components)
    if binnenkant_bron == BINNENKANT_P3:
        adapter = next((c for c in checks if c.bron == BINNENKANT_P3), None)
        candidates.insert(
            0, adapter or Component("binnenkant", BINNENKANT_P3, "unknown", "adapter_niet_gekoppeld", None)
        )
    elif binnenkant_vereist and not any(c.soort == "binnenkant" for c in checks):
        candidates.append(
            Component("binnenkant", binnenkant_bron or "binnenkant", "unknown", "binnenkant_ontbreekt", None)
        )
    elif not checks and runtime.status == "healthy":
        return result("unknown", "geen_gezondheidsbron")

    cause = max(candidates, key=lambda c: _SEVERITY[c.status])
    if cause.status == "healthy":
        return result("healthy", None)
    return result(cause.status, cause.reason_code, cause)


def status_value(status: str) -> float | None:
    """Voor tijdreeksen: healthy 1, degraded 0.5, down 0; unknown → geen meting (gat in de reeks)."""
    return {"healthy": 1.0, "degraded": 0.5, "down": 0.0}.get(status)
