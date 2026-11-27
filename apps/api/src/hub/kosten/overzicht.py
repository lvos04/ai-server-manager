"""Perioden van de woning en de projectie van de B14-uurreeks naar de Hub."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, Field, FiniteFloat, Strict, ValidationError

from hub.timeutil import UtcDateTime

Periode = Literal["dag", "week", "maand"]
Meterrol = Literal["p1_net", "boiler_socket", "airco_outdoor", "nas_host"]
Richting = Literal["import", "export"]
Kwaliteit = Literal["measured", "estimated", "unknown"]
Bron = Literal["home-control-hub", "media-source-optimizer", "hub.D09"]
Post = Literal["stroomkosten", "externe_diensten", "cloudbudget"]
Valuta = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
EIGENAAR: dict[Post, Bron] = {
    "stroomkosten": "home-control-hub",
    "externe_diensten": "media-source-optimizer",
    "cloudbudget": "hub.D09",
}
METEROMSCHRIJVING = {
    "p1_net": "Netaansluiting",
    "boiler_socket": "Boilermeter",
    "airco_outdoor": "Airco (gedeelde buitenunit)",
    "nas_host": "Afzonderlijke NAS-meter",
}
PERIODEN = {"dag": "day", "week": "week", "maand": "month"}
UUR = timedelta(hours=1)
DAG = timedelta(days=1)
# B14 levert afgesloten uren. Een ouder uur vult nooit het laatste ontbrekende uur van een lopend tijdvak.
MAX_AGE = UUR
SCHATTING = "De door B14 geschatte bronwaarde is representatief verondersteld voor het volledige bijbehorende uur."
log = logging.getLogger(__name__)


class Tijdvak(BaseModel):
    """Lokale kalendergrenzen zijn exclusief aan de rechterkant, ook als de brontijdzone nog ontbreekt."""

    eerste_dag: date
    na_laatste_dag: date
    tijdzone: str | None = None
    van_utc: UtcDateTime | None = None
    tot_utc: UtcDateTime | None = None


def kalender(periode: Periode, dag: date, zone: ZoneInfo | None = None) -> Tijdvak:
    if periode == "week":
        begin = dag - timedelta(days=dag.weekday())
        einde = begin + 7 * DAG
    elif periode == "maand":
        begin = dag.replace(day=1)
        einde = (begin + 32 * DAG).replace(day=1)
    else:
        begin, einde = dag, dag + DAG
    return Tijdvak(
        eerste_dag=begin,
        na_laatste_dag=einde,
        tijdzone=zone.key if zone else None,
        van_utc=datetime.combine(begin, time.min, zone).astimezone(UTC) if zone else None,
        tot_utc=datetime.combine(einde, time.min, zone).astimezone(UTC) if zone else None,
    )


class Kostencijfer(BaseModel):
    bron: Bron
    tijdvak: Tijdvak
    eenheid: str | None = None
    waarde: Decimal | None = None
    measurement_quality: Kwaliteit = "unknown"
    aanname: str | None = None
    reden: str | None = None
    observed_at: UtcDateTime | None = None


class Meetdekking(BaseModel):
    """De telling van bronintervallen is ook bij deels geschat verbruik rechtstreeks controleerbaar."""

    bron: Literal["home-control-hub"] = "home-control-hub"
    tijdvak: Tijdvak
    measurement_quality: Literal["measured", "unknown"] = "unknown"
    verwachte_intervallen: int | None = None
    gemeten_intervallen: int | None = None
    geschatte_intervallen: int | None = None


class Stroom(BaseModel):
    verbruik: Kostencijfer
    stroomkosten: Kostencijfer
    meetdekking: Meetdekking


class Energierapport(BaseModel):
    gevraagd: Tijdvak
    totaal: Stroom
    reeks: list[Stroom]


def onbekend(vak: Tijdvak, reden: str) -> Energierapport:
    verbruik = Kostencijfer(bron="home-control-hub", tijdvak=vak, eenheid="kWh", reden=reden)
    kosten = Kostencijfer(bron="home-control-hub", tijdvak=vak, reden=reden)
    return Energierapport(
        gevraagd=vak,
        totaal=Stroom(verbruik=verbruik, stroomkosten=kosten, meetdekking=Meetdekking(tijdvak=vak)),
        reeks=[],
    )


class Hoeveelheid(BaseModel):
    value: Annotated[FiniteFloat, Strict()] | None
    quality: Literal["gemeten", "geschat", "onbekend"]
    source: str


class Uur(BaseModel):
    start_utc: AwareDatetime
    end_utc: AwareDatetime
    meter_id: UUID | None
    counter_reset: Annotated[bool, Strict()]
    usage: Hoeveelheid
    cost: Hoeveelheid


class Brondag(BaseModel):
    date: date
    hours: list[Uur] = Field(max_length=26)


class B14Rapport(BaseModel):
    period: Literal["day", "week", "month"]
    timezone: str
    role: str
    direction: Richting
    unit: Literal["kWh"]
    currency: Valuta | None
    days: list[Brondag] = Field(max_length=31)


def _uurwaarde(q: Hoeveelheid, bronpad: str, eenheid: str | None, vak: Tijdvak) -> Kostencijfer:
    cijfer = Kostencijfer(bron="home-control-hub", tijdvak=vak, eenheid=eenheid)
    if q.source != bronpad or not eenheid or q.value is None or q.quality == "onbekend":
        return cijfer.model_copy(update={"reden": "bronwaarde_onbekend"})
    kwaliteit: Kwaliteit = "estimated" if q.quality == "geschat" else "measured"
    return Kostencijfer(
        bron="home-control-hub",
        tijdvak=vak,
        eenheid=eenheid,
        waarde=Decimal(str(q.value)),
        measurement_quality=kwaliteit,
        aanname=SCHATTING if kwaliteit == "estimated" else None,
        observed_at=vak.tot_utc,
    )


def _uur(rij: Uur, vak: Tijdvak, valuta: str | None, exact_bevestigd: bool) -> Stroom:
    verbruik = _uurwaarde(rij.usage, "my_house:energy/export", "kWh", vak)
    kosten = _uurwaarde(rij.cost, "my_house:energy/export+tariffs", valuta, vak)
    if (
        rij.meter_id is None
        or verbruik.waarde is None
        or verbruik.waarde < 0
        or (rij.counter_reset and verbruik.waarde == 0)
    ):
        punt = onbekend(vak, "geen_meterwaarde").totaal
        verbruik, kosten = punt.verbruik, punt.stroomkosten
    elif not exact_bevestigd and verbruik.measurement_quality == "measured":
        punt = onbekend(vak, "meterrol_niet_bevestigd").totaal
        verbruik, kosten = punt.verbruik, punt.stroomkosten
    elif verbruik.measurement_quality == "estimated" and kosten.waarde is not None:
        kosten = kosten.model_copy(update={"measurement_quality": "estimated", "aanname": SCHATTING})
    return Stroom(
        verbruik=verbruik,
        stroomkosten=kosten,
        meetdekking=Meetdekking(
            tijdvak=vak,
            measurement_quality="measured",
            verwachte_intervallen=1,
            gemeten_intervallen=int(verbruik.measurement_quality == "measured"),
            geschatte_intervallen=int(verbruik.measurement_quality == "estimated"),
        ),
    )


def _som(cijfers: list[Kostencijfer], vak: Tijdvak, eenheid: str | None, nu: datetime, lopend: bool) -> Kostencijfer:
    waarden = [c.waarde for c in cijfers if c.waarde is not None]
    laatste = max((c.observed_at for c in cijfers if c.observed_at is not None), default=None)
    basis = Kostencijfer(bron="home-control-hub", tijdvak=vak, eenheid=eenheid, observed_at=laatste)
    if lopend and laatste is not None and nu - laatste > MAX_AGE:
        return basis.model_copy(update={"reden": "meting_verouderd"})
    if not waarden or len(waarden) != len(cijfers):
        reden = (
            "meterrol_niet_bevestigd"
            if any(c.reden == "meterrol_niet_bevestigd" for c in cijfers)
            else "onvolledige_dekking"
        )
        return basis.model_copy(update={"reden": reden})
    geschat = any(c.measurement_quality == "estimated" for c in cijfers)
    return basis.model_copy(
        update={
            "waarde": sum(waarden, Decimal(0)),
            "measurement_quality": "estimated" if geschat else "measured",
            "aanname": SCHATTING if geschat else None,
        }
    )


def _totaal(uren: list[Stroom], vak: Tijdvak, valuta: str | None, nu: datetime) -> Stroom:
    lopend = vak.van_utc is not None and vak.tot_utc is not None and vak.van_utc <= nu < vak.tot_utc
    # De lopende periode loopt in het cijfer zelf slechts tot het einde van het laatste afgesloten broninterval.
    meetvak = vak.model_copy(update={"tot_utc": uren[-1].verbruik.tijdvak.tot_utc}) if lopend and uren else vak
    return Stroom(
        verbruik=_som([u.verbruik for u in uren], meetvak, "kWh", nu, lopend),
        stroomkosten=_som([u.stroomkosten for u in uren], meetvak, valuta, nu, lopend),
        meetdekking=Meetdekking(
            tijdvak=meetvak,
            measurement_quality="measured",
            verwachte_intervallen=len(uren),
            gemeten_intervallen=sum(u.verbruik.measurement_quality == "measured" for u in uren),
            geschatte_intervallen=sum(u.verbruik.measurement_quality == "estimated" for u in uren),
        ),
    )


def projecteer(
    data: object,
    periode: Periode,
    dag: date | None,
    rol: Meterrol,
    richting: Richting,
    nu: datetime,
    *,
    exact_bevestigd: bool,
) -> Energierapport:
    """De tijdstempels en meter in elk uur zijn het bewijs, een meegeleverd totaal kan geen gat opvullen."""
    vak = kalender(periode, dag or nu.date())
    try:
        rapport = B14Rapport.model_validate(data)
        zone = ZoneInfo(rapport.timezone)
        if (rapport.role, rapport.direction, rapport.period) != (rol, richting, PERIODEN[periode]):
            return onbekend(vak, "ander_tijdvak_of_meter")
        vak = kalender(periode, dag or nu.astimezone(zone).date(), zone)
        if len(rapport.days) != (vak.na_laatste_dag - vak.eerste_dag).days:
            return onbekend(vak, "ongeldige_uurreeks")
        uren, dagen = [], []
        for i, brondag in enumerate(rapport.days):
            dagvak = kalender("dag", vak.eerste_dag + i * DAG, zone)
            begin, einde = dagvak.van_utc, dagvak.tot_utc
            if begin is None or einde is None or brondag.date != dagvak.eerste_dag:
                return onbekend(vak, "ongeldige_uurreeks")
            daguren = []
            for rij in brondag.hours:
                volgend = min(begin + UUR, einde)
                if begin >= einde or rij.start_utc != begin or rij.end_utc != volgend:
                    return onbekend(vak, "ongeldige_uurreeks")
                if volgend <= nu:
                    uurvak = dagvak.model_copy(update={"van_utc": begin, "tot_utc": volgend})
                    daguren.append(_uur(rij, uurvak, rapport.currency, exact_bevestigd))
                begin = volgend
            if begin != einde:
                return onbekend(vak, "ongeldige_uurreeks")
            uren.extend(daguren)
            if daguren:
                dagen.append(_totaal(daguren, dagvak, rapport.currency, nu))
        return Energierapport(
            gevraagd=vak,
            totaal=_totaal(uren, vak, rapport.currency, nu),
            reeks=uren if periode == "dag" else dagen,
        )
    except (ValidationError, ValueError, ZoneInfoNotFoundError, OverflowError):
        return onbekend(vak, "antwoord_ongeldig")


def unieke_posten(vak: Tijdvak, bijdragen: dict[Bron, dict[Post, Kostencijfer]]) -> dict[Post, Kostencijfer]:
    """Kies op herkomst van de aanroep, nooit op een door een andere dienst opgegeven eigenaar."""
    posten = {
        post: Kostencijfer(bron=bron, tijdvak=vak, reden="bron_niet_beschikbaar") for post, bron in EIGENAAR.items()
    }
    for bron, cijfers in bijdragen.items():
        for post, cijfer in cijfers.items():
            if bron != EIGENAAR[post]:
                log.info("dubbele_kostenbron_genegeerd")
                continue
            posten[post] = cijfer.model_copy(update={"bron": bron})
    return posten
