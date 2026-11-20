"""MediaGuard-leesmodel zolang de bron geen neveneffectvrije routes biedt (S-P3-030)."""

from typing import Final, Literal

from pydantic import BaseModel

from hub.adapters import basis

APP_ID = "mediaguard"
REASON_CODE: Final = "geen_alleen_lezen_bron"


class UnavailableMeasurement(BaseModel, frozen=True):
    status: Literal["unknown"] = "unknown"
    observed_at: None = None
    reason_code: Literal["geen_alleen_lezen_bron"] = REASON_CODE
    reason: Literal["geen alleen-lezen bron"] = "geen alleen-lezen bron"


UNAVAILABLE = UnavailableMeasurement()


class Readings(BaseModel):
    wanted: UnavailableMeasurement = UNAVAILABLE
    status: UnavailableMeasurement = UNAVAILABLE
    downloads: UnavailableMeasurement = UNAVAILABLE
    av1: UnavailableMeasurement = UNAVAILABLE
    incidenten: UnavailableMeasurement = UNAVAILABLE
    mediaservers: UnavailableMeasurement = UNAVAILABLE
    noodstop: UnavailableMeasurement = UNAVAILABLE
    opslagprognose: UnavailableMeasurement = UNAVAILABLE
    backups: UnavailableMeasurement = UNAVAILABLE


def health() -> basis.Measurement:
    return basis.Measurement(status="unknown", reason_code=REASON_CODE)
