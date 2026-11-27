"""Een instelbare grens voor variabele stroomkosten op de hoofdmeter en de bestaande meldingenwachtrij."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from hub.errors import HubError
from hub.kosten.overzicht import MAX_AGE, Kostencijfer, Periode, Tijdvak, Valuta
from hub.models import HubSetting, Notification, NotificationChannel

INSTELLING = "kosten.stroombudget"
Budgetstatus = Literal["uit", "onbekend", "binnen_grens", "overschreden"]


class Stroombudget(BaseModel):
    """Een lege grens schakelt de waarschuwing uit."""

    model_config = ConfigDict(extra="forbid")
    grens: Decimal | None = Field(ge=0, max_digits=14, decimal_places=2)
    valuta: Valuta
    periode: Periode


def ingesteld(db: Session, *, vergrendel: bool = False) -> Stroombudget | None:
    row = db.get(HubSetting, INSTELLING, with_for_update=vergrendel, populate_existing=vergrendel)
    return Stroombudget.model_validate(row.waarde) if row else None


def etag(budget: Stroombudget) -> str:
    return '"' + sha256(budget.model_dump_json().encode()).hexdigest() + '"'


def opslaan(db: Session, budget: Stroombudget, actor: str, nu: datetime, if_match: str | None) -> None:
    if if_match is not None:
        bestaand = ingesteld(db, vergrendel=True)
        if bestaand is None or if_match.strip() not in ("*", etag(bestaand)):
            raise HubError(412, "precondition_failed", "Het stroombudget is intussen gewijzigd. Laad het opnieuw.")
    waarden = {"waarde": budget.model_dump(mode="json"), "gewijzigd_door": actor, "gewijzigd_op": nu}
    db.execute(
        insert(HubSetting)
        .values(sleutel=INSTELLING, **waarden)
        .on_conflict_do_update(
            index_elements=[HubSetting.sleutel],
            set_=waarden,
        )
    )


def waarschuw(db: Session, grens: Stroombudget, kost: Kostencijfer, vak: Tijdvak, nu: datetime) -> Budgetstatus:
    if grens.grens is None:
        return "uit"
    if (
        kost.waarde is None
        or kost.measurement_quality == "unknown"
        or kost.observed_at is None
        or kost.observed_at > nu
        or nu - kost.observed_at > MAX_AGE
        or kost.bron != "home-control-hub"
        or kost.eenheid != grens.valuta
        or vak.van_utc is None
        or vak.tot_utc is None
        or not vak.van_utc <= nu < vak.tot_utc
    ):
        return "onbekend"
    if kost.waarde <= grens.grens:
        return "binnen_grens"
    # Eén waarschuwing per woningperiode, grens en kanaal, ook bij gelijktijdige schermverversingen.
    sleutel = f"kosten:{grens.periode}:{vak.van_utc.isoformat()}:{grens.valuta}:{grens.grens:.2f}"
    kanalen = db.scalars(
        select(NotificationChannel.id).where(
            NotificationChannel.ingeschakeld.is_(True),
            NotificationChannel.min_ernst.in_(("info", "waarschuwing")),
        )
    )
    kwaliteit = "geschat" if kost.measurement_quality == "estimated" else "gemeten"
    bericht = (
        f"B14 meldt {kost.waarde:f} {grens.valuta} ({kwaliteit}) voor netafname sinds "
        f"{vak.eerste_dag.isoformat()}. De ingestelde grens is {grens.grens:.2f} {grens.valuta}."
    )
    if kost.aanname:
        bericht += f" {kost.aanname}"
    for kanaal in kanalen:
        db.execute(
            insert(Notification)
            .values(
                kanaal_id=kanaal,
                dedupe_sleutel=sleutel,
                bron="kosten",
                soort="bericht",
                ernst="waarschuwing",
                titel="Stroombudget overschreden",
                bericht=bericht,
                status="wachtrij",
                volgende_poging_op=nu,
                aangemaakt_op=nu,
            )
            .on_conflict_do_nothing(constraint="uq_notification_dedupe")
        )
    return "overschreden"
