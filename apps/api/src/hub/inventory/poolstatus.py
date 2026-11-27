"""De volledige poolstatus uit één inventarismeting voor MediaGuard (§4.4)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from hub.timeutil import UtcDateTime


class Pool(BaseModel):
    status: str
    gezond: bool


class Poolmeting(BaseModel):
    kind: Literal["pools"] = "pools"
    status: Literal["ok", "unknown"]
    reason_code: str | None
    observed_at: UtcDateTime | None = Field(description="UTC-bronmeettijd van de gezamenlijke meting.")
    geldig_tot: UtcDateTime | None = Field(description="Einde van de geldigheid in UTC, uiterlijk 900 s na de meting.")
    items: list[Pool] = Field(description="Alle pools uit dezelfde meting. Leeg bij een onbekende meting.")


def projecteer(staat: dict[str, Any], nu: datetime) -> Poolmeting:
    gemeten = datetime.fromisoformat(staat["observed_at"]) if staat["observed_at"] else None
    geldig_tot = datetime.fromisoformat(staat["geldig_tot"]) if staat["geldig_tot"] else None
    data = staat["data"]
    reden = staat["reason_code"]
    if staat["status"] == "ok":
        if gemeten is None or gemeten > nu or geldig_tot is None or geldig_tot <= nu:
            reden = "meting_verouderd"
        elif (
            not isinstance(data, list)
            or not data
            or not all(
                isinstance(p, dict)
                and isinstance(p.get("naam"), str)
                and p["naam"].strip()
                and isinstance(p.get("status"), str)
                and p["status"].strip()
                and isinstance(p.get("gezond"), bool)
                for p in data
            )
        ):
            reden = "meting_onvolledig"
        else:
            return Poolmeting(
                status="ok",
                reason_code=None,
                observed_at=gemeten,
                geldig_tot=geldig_tot,
                items=[Pool(status=p["status"], gezond=p["status"] == "ONLINE" and p["gezond"]) for p in data],
            )
    return Poolmeting(status="unknown", reason_code=reden, observed_at=gemeten, geldig_tot=None, items=[])
