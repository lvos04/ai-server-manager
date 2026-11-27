"""Leesroute voor Kosten en de door een beheerder ingestelde budgetwaarschuwing."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import JSONResponse

from hub import audit
from hub.deps import DB, Admin, Idem, SettingsDep, Viewer, get_keyring
from hub.errors import HubError
from hub.keys import KeyRing
from hub.kosten import bronnen, budget
from hub.kosten.overzicht import (
    METEROMSCHRIJVING,
    Energierapport,
    Kostencijfer,
    Meterrol,
    Periode,
    Richting,
    unieke_posten,
)
from hub.models import Decision
from hub.timeutil import utcnow

router = APIRouter(prefix="/api/v1/kosten", tags=["energie en kosten"])


class Kostenoverzicht(Energierapport):
    periode: Periode
    meterrol: Meterrol
    meteromschrijving: str
    richting: Richting
    externe_diensten: Kostencijfer
    cloudbudget: Kostencijfer
    budgetstatus: budget.Budgetstatus


@router.get("", summary="Energie en variabele stroomkosten per woningdag, week of maand met bron en meetdekking")
def lees(
    db: DB,
    settings: SettingsDep,
    gebruiker: Viewer,
    sleutels: Annotated[KeyRing, Depends(get_keyring)],
    datum: Annotated[date, Query(ge=date(2, 1, 1), le=date(9998, 12, 31), description="Een kalenderdag in de woning.")],
    periode: Periode = "dag",
    meterrol: Meterrol = "p1_net",
    richting: Richting = "import",
) -> Kostenoverzicht:
    if richting == "export" and meterrol != "p1_net":
        raise HubError(422, "validation_error", "Alleen de netmeter heeft een terugleverreeks.")
    nu = utcnow()
    rapport = bronnen.energie(db, settings, sleutels, gebruiker.id, periode, datum, meterrol, richting, nu)
    vak = rapport.gevraagd
    posten = unieke_posten(
        vak,
        {
            "home-control-hub": {"stroomkosten": rapport.totaal.stroomkosten},
            "media-source-optimizer": bronnen.mso_posten(vak),
            "hub.D09": {
                "cloudbudget": bronnen.cloudbudget(db.get(Decision, "D09"), datum, nu, actief=settings.ai_enabled)
            },
        },
    )

    grens = budget.ingesteld(db)
    stand: budget.Budgetstatus = "uit"
    if grens and grens.grens is not None:
        stand = "onbekend"
        zelfde_periode = (
            meterrol == "p1_net"
            and richting == "import"
            and grens.periode == periode
            and vak.van_utc is not None
            and vak.tot_utc is not None
            and vak.van_utc <= nu < vak.tot_utc
        )
        meting = rapport
        if not zelfde_periode and rapport.totaal.verbruik.reden != "leesrecht_geweigerd":
            # Zonder datum kiest B14 zelf de actuele woningdag, ook wanneer de schermreeks geen tijdzone leverde.
            meting = bronnen.energie(db, settings, sleutels, gebruiker.id, grens.periode, None, "p1_net", "import", nu)
        if budget.ingesteld(db, vergrendel=True) == grens:
            stand = budget.waarschuw(db, grens, meting.totaal.stroomkosten, meting.gevraagd, nu)
            if stand == "overschreden":
                db.commit()
    return Kostenoverzicht(
        gevraagd=vak,
        totaal=rapport.totaal.model_copy(update={"stroomkosten": posten["stroomkosten"]}),
        reeks=rapport.reeks,
        periode=periode,
        meterrol=meterrol,
        meteromschrijving=METEROMSCHRIJVING[meterrol],
        richting=richting,
        externe_diensten=posten["externe_diensten"],
        cloudbudget=posten["cloudbudget"],
        budgetstatus=stand,
    )


@router.get("/budget", summary="Ingestelde grens voor de variabele kosten van netafname")
def lees_budget(db: DB, _: Viewer, response: Response) -> budget.Stroombudget | None:
    huidig = budget.ingesteld(db)
    if huidig:
        response.headers["ETag"] = budget.etag(huidig)
    return huidig


@router.put("/budget", response_model=budget.Stroombudget, summary="Stroombudget instellen of uitschakelen")
def stel_budget_in(
    body: budget.Stroombudget,
    db: DB,
    beheerder: Admin,
    idem: Idem,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> JSONResponse:
    if (replay := idem.replay()) is not None:
        replay.headers["ETag"] = budget.etag(body)
        return replay
    budget.opslaan(db, body, beheerder.name, utcnow(), if_match)
    waarde = body.model_dump(mode="json")
    audit.record(
        db,
        actor_type="user",
        actor_id=beheerder.name,
        action="kosten.budget_opgeslagen",
        target_type="hub_setting",
        target_id=budget.INSTELLING,
        details=waarde,
    )
    response = idem.save(200, waarde)
    response.headers["ETag"] = budget.etag(body)
    return response
