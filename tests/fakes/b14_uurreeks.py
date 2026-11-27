"""Synthetische B14-antwoorden volgens energy/usage, met UTC-intervallen per lokale woningdag."""

from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Europe/Amsterdam")
TESTMETER = str(UUID(int=1))


def _totalen(uren: int) -> dict[str, Any]:
    return {
        "status": "volledig",
        "usage": {"source": "my_house:energy/export", "quality": "gemeten", "value": uren},
        "cost": {"source": "my_house:energy/export+tariffs", "quality": "gemeten", "value": 0.25 * uren},
    }


def uurreeks(dag: date, periode: str = "day", rol: str = "p1_net", richting: str = "import") -> dict[str, Any]:
    eerste, aantal = dag, 1
    if periode == "week":
        eerste, aantal = dag - timedelta(days=dag.weekday()), 7
    elif periode == "month":
        eerste, aantal = dag.replace(day=1), monthrange(dag.year, dag.month)[1]
    dagen = []
    for i in range(aantal):
        datum = eerste + timedelta(days=i)
        begin = datetime.combine(datum, time.min, ZONE).astimezone(UTC)
        einde = datetime.combine(datum + timedelta(days=1), time.min, ZONE).astimezone(UTC)
        uren = []
        while begin < einde:
            volgend = begin + timedelta(hours=1)
            uren.append(
                {
                    "start_utc": begin.isoformat(),
                    "end_utc": volgend.isoformat(),
                    "meter_id": TESTMETER,
                    "counter_reset": False,
                    "usage": {"source": "my_house:energy/export", "value": 1, "quality": "gemeten"},
                    "cost": {"source": "my_house:energy/export+tariffs", "value": 0.25, "quality": "gemeten"},
                }
            )
            begin = volgend
        dagen.append({"date": datum.isoformat(), "hours": uren, **_totalen(len(uren))})
    return {
        "role": rol,
        "direction": richting,
        "period": periode,
        "timezone": ZONE.key,
        "unit": "kWh",
        "currency": "EUR",
        "days": dagen,
        **_totalen(sum(len(d["hours"]) for d in dagen)),
    }
