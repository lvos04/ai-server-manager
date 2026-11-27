"""Uitsluitend B14 via het gemeten registeradres en het bestaande maandbudget uit D09."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import Decimal
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from hub import servicecalls
from hub.config import Settings
from hub.keys import KeyRing
from hub.kosten.overzicht import (
    PERIODEN,
    Energierapport,
    Kostencijfer,
    Meterrol,
    Periode,
    Post,
    Richting,
    Tijdvak,
    kalender,
    onbekend,
    projecteer,
)
from hub.models import Decision, Service
from hub.onboarding.catalog import D09Waarde
from hub.registry import service_base_url

B14 = "home-control-hub"
BEDRAG = r"(?:0|[1-9][0-9]{0,9})(?:[.,][0-9]{1,2})?"
# Bij vrije D09-tekst kunnen drie hoofdletters ook een eenheid zoals API-tegoed aanduiden.
VALUTA = r"(?:EUR|USD|GBP|CHF|CAD|AUD|NZD|JPY|DKK|NOK|SEK|PLN|€)"


def energie(
    db: Session,
    settings: Settings,
    sleutels: KeyRing,
    gebruiker: str,
    periode: Periode,
    dag: date | None,
    rol: Meterrol,
    richting: Richting,
    nu: datetime,
) -> Energierapport:
    vak = kalender(periode, dag or nu.date())
    if rol == "nas_host":
        return onbekend(vak, "geen_afzonderlijke_nas_meterreeks")
    besluit = db.get(Decision, "D14")
    veld = {
        "p1_net": "p1_meter",
        "airco_outdoor": "airco_1fase_meter",
        "boiler_socket": "energy_socket_boiler_alleen_meten",
    }
    meter = (besluit.waarde or {}).get(veld[rol]) if besluit else None
    bevestigd = besluit is not None and besluit.status == "Getest"
    if bevestigd and meter is False:
        return onbekend(vak, "meterrol_afwezig")
    dienst = db.scalar(select(Service).where(Service.app_id == B14, Service.status == "active"))
    if dienst is None:
        return onbekend(vak, "bron_niet_gekoppeld")
    basis, reden = service_base_url(db, settings, dienst)
    if basis is None:
        return onbekend(vak, reden or "bron_niet_beschikbaar")
    parameters = {"period": PERIODEN[periode], "role": rol, "direction": richting}
    if dag is not None:
        parameters["date"] = dag.isoformat()
    query = urlencode(parameters)
    token, _ = sleutels.issue_user_jwt(
        subject=gebruiker,
        audience=B14,
        roles=["viewer"],
        ttl_seconds=settings.jwt_ttl_seconds,
    )
    try:
        resultaat = servicecalls.call(
            basis,
            "GET",
            f"/integrations/v1/energy/usage?{query}",
            bearer=token,
            connect_timeout=settings.service_call_connect_timeout,
            read_timeout=settings.service_call_read_timeout,
        )
    except (servicecalls.ServiceCallError, RecursionError):
        return onbekend(vak, "bron_niet_beschikbaar")
    if resultaat.status in (401, 403):
        return onbekend(vak, "leesrecht_geweigerd")
    if resultaat.status != 200:
        return onbekend(vak, "bron_niet_beschikbaar")
    return projecteer(resultaat.body, periode, dag, rol, richting, nu, exact_bevestigd=bevestigd and meter is True)


def cloudbudget(besluit: Decision | None, dag: date, nu: datetime, *, actief: bool) -> Kostencijfer:
    """Lees alleen het toegewezen maandplafond uit D09. Reserveringen en vrije consoletekst blijven bij de bron."""
    maand = kalender("maand", dag, ZoneInfo("UTC"))
    basis = Kostencijfer(bron="hub.D09", tijdvak=maand, reden="maandbudget_onbekend")
    utc = nu.astimezone(UTC)
    if not actief or not maand.eerste_dag <= utc.date() < maand.na_laatste_dag:
        return basis
    if besluit is None or besluit.status != "Getest" or besluit.getest_op is None or besluit.getest_op > utc:
        return basis
    try:
        config = D09Waarde.model_validate(besluit.waarde, strict=True)
    except ValidationError:
        return basis
    if not config.account_gekoppeld:
        return basis
    if config.tegoedmaand is not None or config.inbegrepen_eenheden is not None:
        if config.tegoedmaand != utc.strftime("%Y-%m") or config.inbegrepen_eenheden is None:
            return basis
        return Kostencijfer(
            bron="hub.D09",
            tijdvak=maand,
            eenheid="kredieteenheden",
            waarde=Decimal(config.inbegrepen_eenheden),
            measurement_quality="estimated",
            observed_at=besluit.getest_op,
            aanname="De in D09 bevestigde toewijzing geldt voor deze UTC-maand. Het cijfer is het maandplafond.",
        )
    # Oudere besluiten missen een kredietmaand. Gebruik alleen een deze maand bevestigd valutabedrag.
    if besluit.getest_op.astimezone(UTC).date() < maand.eerste_dag:
        return basis
    tekst = (config.inbegrepen_maandbudget or "").strip()
    if voor := re.fullmatch(rf"({VALUTA})\s*({BEDRAG})", tekst):
        valuta, bedrag = voor.groups()
    elif na := re.fullmatch(rf"({BEDRAG})\s*({VALUTA})", tekst):
        bedrag, valuta = na.groups()
    else:
        return basis
    return Kostencijfer(
        bron="hub.D09",
        tijdvak=maand,
        eenheid="EUR" if valuta == "€" else valuta,
        waarde=Decimal(bedrag.replace(",", ".")),
        measurement_quality="estimated",
        observed_at=besluit.getest_op,
        aanname="Het in D09 bevestigde inbegrepen maandbudget geldt nog voor deze maand. Dit is een limiet.",
    )


def mso_posten(vak: Tijdvak) -> dict[Post, Kostencijfer]:
    # ADR-0034: /api/v1/costs/summary valt buiten de leesrechten van de MSO-machinesleutel.
    return {
        "externe_diensten": Kostencijfer(bron="media-source-optimizer", tijdvak=vak, reden="leesroute_niet_vrijgegeven")
    }
