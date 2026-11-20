"""Gezondheid van bestaande adapters uit reeds opgeslagen metingen."""

from datetime import datetime

from pydantic import ValidationError

from hub.adapters import basis, mediaguard, mso, my_house
from hub.models import AdapterLink


def stored_health(link: AdapterLink, now: datetime, *, bound: bool) -> basis.Measurement:
    if link.app_id == mediaguard.APP_ID:
        return mediaguard.health()
    if link.app_id == mso.APP_ID:
        return mso.health()
    if link.app_id != my_house.APP_ID:
        return basis.Measurement(status="unknown", reason_code="capability_unavailable")

    try:
        checks = my_house.CheckReadings.validate_python(link.my_house_checks or [])
    except ValidationError:
        checks = []
    last = my_house.health(checks, now) if checks else None
    reason = link.laatste_fout
    if link.my_house_expires_at is not None and link.my_house_expires_at <= now:
        reason = "bron_token_verlopen"
    if not bound:
        reason = "doelbinding"
    if last is not None and reason is None:
        if last.geldig_tot is not None and link.my_house_expires_at is not None:
            last.geldig_tot = min(last.geldig_tot, link.my_house_expires_at)
        return last
    return basis.Measurement(
        status="unknown",
        reason_code=reason or "meting_onbekend",
        observed_at=last.observed_at if last is not None else None,
        laatste_status=(last.laatste_status or last.status) if last is not None else None,
    )
