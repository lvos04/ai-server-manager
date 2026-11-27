"""B01-011, B14-001/002 en B05-008: toets bronkeuze, dekking, kalender en onbekende cijfers."""

from datetime import UTC, date, datetime
from decimal import Decimal
from logging import INFO
from typing import Any

import pytest
from fakes.b14_uurreeks import uurreeks

from hub.kosten.bronnen import cloudbudget
from hub.kosten.overzicht import Kostencijfer, Periode, kalender, projecteer, unieke_posten
from hub.models import Decision

DAG = date(2026, 10, 25)
LATER = datetime(2026, 11, 15, 15, tzinfo=UTC)


@pytest.mark.parametrize(
    ("dag", "periode", "bronperiode", "uren", "punten"),
    [
        (date(2026, 3, 29), "dag", "day", 23, 23),
        (DAG, "dag", "day", 25, 25),
        (DAG, "week", "week", 169, 7),
        (date(2026, 3, 10), "maand", "month", 743, 31),
    ],
)
def test_kalender_telt_elk_utc_interval_een_keer(
    dag: date, periode: Periode, bronperiode: str, uren: int, punten: int
) -> None:
    rapport = projecteer(uurreeks(dag, bronperiode), periode, dag, "p1_net", "import", LATER, exact_bevestigd=True)
    totaal = rapport.totaal
    assert len(rapport.reeks) == punten
    assert totaal.verbruik.waarde == uren
    assert totaal.stroomkosten.waarde == Decimal("0.25") * uren
    assert totaal.meetdekking.gemeten_intervallen == totaal.meetdekking.verwachte_intervallen == uren
    assert totaal.verbruik.observed_at == totaal.verbruik.tijdvak.tot_utc
    assert all(p.verbruik.bron == "home-control-hub" for p in rapport.reeks)


@pytest.mark.parametrize(
    "fout", ["geen_meter", "ander_uur", "dubbel_uur", "andere_rol", "binnenunit", "bool", "tellerreset", "eenheid"]
)
def test_ongeldig_bronbewijs_levert_geen_bedrag(fout: str) -> None:
    bron = uurreeks(DAG)
    uren = bron["days"][0]["hours"]
    if fout == "geen_meter":
        for uur in uren:
            uur["meter_id"] = None
    elif fout == "ander_uur":
        uren[2]["start_utc"] = uren[0]["start_utc"]
    elif fout == "dubbel_uur":
        uren.append(uren[-1])
    elif fout == "andere_rol":
        bron["role"] = "airco_outdoor"
    elif fout == "binnenunit":
        bron["role"] = "airco_binnen"
    elif fout == "tellerreset":
        uren[3]["counter_reset"] = True
        uren[3]["usage"]["value"] = 0
    elif fout == "bool":
        uren[0]["usage"]["value"] = True
    else:
        bron["unit"] = "W"
    # Samenvattingen van de bron vullen een ontbrekend of tegenstrijdig bronuur nooit aan.
    bron.update({"cost": {"value": 200}, "usage": {"value": 500}, "besparing": 30})
    rapport = projecteer(bron, "dag", DAG, "p1_net", "import", LATER, exact_bevestigd=True)
    assert rapport.totaal.verbruik.waarde is None
    assert rapport.totaal.stroomkosten.waarde is None
    assert rapport.totaal.stroomkosten.measurement_quality == "unknown"
    assert "besparing" not in rapport.model_dump_json()


def test_echte_nul_ontbrekend_tarief_en_schatting() -> None:
    bron = uurreeks(DAG, rol="airco_outdoor")
    for uur in bron["days"][0]["hours"]:
        uur["usage"].update(value=0, quality="geschat")
        uur["cost"]["value"] = 0
    rapport = projecteer(bron, "dag", DAG, "airco_outdoor", "import", LATER, exact_bevestigd=True)
    assert rapport.totaal.verbruik.waarde == rapport.totaal.stroomkosten.waarde == 0
    assert rapport.totaal.stroomkosten.measurement_quality == "estimated"
    assert rapport.totaal.stroomkosten.aanname and rapport.totaal.verbruik.aanname
    assert rapport.totaal.meetdekking.geschatte_intervallen == 25
    bron["days"][0]["hours"][0]["cost"]["quality"] = "onbekend"
    assert (
        projecteer(bron, "dag", DAG, "airco_outdoor", "import", LATER, exact_bevestigd=True).totaal.stroomkosten.waarde
        is None
    )


def test_verlopen_uur_wordt_onbekend_op_broneindtijd() -> None:
    bron = uurreeks(DAG)
    nu = datetime(2026, 10, 25, 14, 30, tzinfo=UTC)
    uren = bron["days"][0]["hours"]
    for uur in uren:
        if uur["end_utc"] > "2026-10-25T13:00:00+00:00":
            uur["meter_id"] = None
    rapport = projecteer(bron, "dag", DAG, "p1_net", "import", nu, exact_bevestigd=True)
    kost = rapport.totaal.stroomkosten
    assert kost.waarde is None and kost.reden == "meting_verouderd"
    assert kost.observed_at == datetime(2026, 10, 25, 13, tzinfo=UTC)
    assert (
        rapport.totaal.meetdekking.gemeten_intervallen == 15 and rapport.totaal.meetdekking.verwachte_intervallen == 16
    )


def test_bron_van_de_aanroep_wint_onafhankelijk_van_aanlevervolgorde(caplog: Any) -> None:
    vak = kalender("dag", DAG)
    eigen = Kostencijfer(bron="home-control-hub", tijdvak=vak, waarde=Decimal(12), measurement_quality="measured")
    vreemd = eigen.model_copy(update={"waarde": Decimal(999)})
    bronnen = {"media-source-optimizer": {"stroomkosten": vreemd}, "home-control-hub": {"stroomkosten": eigen}}
    with caplog.at_level(INFO):
        for bijdragen in (bronnen, dict(reversed(bronnen.items()))):
            posten = unieke_posten(vak, bijdragen)
            assert [c.waarde for c in posten.values() if c.waarde is not None] == [Decimal(12)]
    assert caplog.messages == ["dubbele_kostenbron_genegeerd"] * 2


@pytest.mark.parametrize(
    ("tekst", "verwacht"),
    [
        ("€ 20,50", Decimal("20.50")),
        ("12 USD", Decimal(12)),
        ("geen data", None),
        ("20", None),
        ("20 EUR en 4 USD", None),
        ("20 API", None),
    ],
)
def test_d09_projecteert_alleen_herkenbaar_huidig_maandbudget(tekst: str, verwacht: Decimal | None) -> None:
    besluit = Decision(
        id="D09",
        status="Getest",
        getest_op=LATER,
        waarde={
            "account_gekoppeld": True,
            "inbegrepen_maandbudget": tekst,
            "harde_stop": True,
            "overage_toegestaan": False,
        },
    )
    cijfer = cloudbudget(besluit, LATER.date(), LATER, actief=True)
    assert cijfer.waarde == verwacht
    if verwacht is not None:
        assert cijfer.aanname and cijfer.measurement_quality == "estimated"
        assert cijfer.tijdvak.eerste_dag == date(2026, 11, 1)
    assert cloudbudget(besluit, DAG, LATER, actief=True).waarde is None
    assert cloudbudget(besluit, LATER.date(), LATER, actief=False).waarde is None
    besluit.status = "Open"
    assert cloudbudget(besluit, LATER.date(), LATER, actief=True).waarde is None
    besluit.status, besluit.getest_op = "Getest", datetime(2026, 10, 31, 23, 59, tzinfo=UTC)
    assert cloudbudget(besluit, LATER.date(), LATER, actief=True).waarde is None


@pytest.mark.parametrize(
    ("bronmaand", "eenheden", "verwacht"),
    [("2026-11", 25, 25), ("2026-11", 0, 0), ("2026-10", 25, None), (None, 25, None), ("2026-11", None, None)],
)
def test_d09_voorrang_en_utc_maandgrens(bronmaand: str | None, eenheden: int | None, verwacht: int | None) -> None:
    nu = datetime(2026, 11, 30, 23, 30, tzinfo=UTC)
    besluit = Decision(
        id="D09",
        status="Getest",
        getest_op=LATER,
        waarde={
            "account_gekoppeld": True,
            "harde_stop": True,
            "overage_toegestaan": False,
            "tegoedmaand": bronmaand,
            "inbegrepen_eenheden": eenheden,
            "inbegrepen_maandbudget": "EUR 250",
        },
    )
    cijfer = cloudbudget(besluit, nu.date(), nu, actief=True)
    assert cijfer.waarde == verwacht and cijfer.tijdvak.tijdzone == "UTC"
    if verwacht is not None:
        assert cijfer.eenheid == "kredieteenheden" and cijfer.measurement_quality == "estimated" and cijfer.aanname
    else:
        assert cijfer.measurement_quality == "unknown"
    assert cloudbudget(besluit, date(2026, 12, 1), nu, actief=True).waarde is None
