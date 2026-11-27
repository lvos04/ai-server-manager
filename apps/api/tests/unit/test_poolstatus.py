"""Alleen een volledige, gedateerde meting kan de opruimer informeren (§4.4)."""

from datetime import timedelta
from typing import Any

import pytest
from fakes.fake_truenas import default_data

from hub.inventory.poolstatus import projecteer
from hub.timeutil import iso, utcnow
from hub.truenas.normalize import pools


def test_poolmeting_houdt_de_kortere_brondatum_bij_herhaling() -> None:
    nu = utcnow()
    bron = default_data()["pool.query"][0]
    data = pools([bron, {**bron, "status": "DEGRADED", "healthy": True}])
    staat = {
        "status": "ok",
        "reason_code": None,
        "observed_at": iso(nu),
        "geldig_tot": iso(nu + timedelta(seconds=60)),
        "data": data,
    }
    eerste = projecteer(staat, nu)
    assert [p.model_dump() for p in eerste.items] == [
        {"status": "ONLINE", "gezond": True},
        {"status": "DEGRADED", "gezond": False},
    ]
    assert eerste.status == "ok" and iso(eerste.geldig_tot) == staat["geldig_tot"]
    assert projecteer(staat, nu + timedelta(seconds=59)) == eerste
    assert projecteer(staat, nu + timedelta(seconds=61)).status == "unknown"


@pytest.mark.parametrize(
    ("leeftijd", "resterend", "data", "status", "reden"),
    [
        (None, 120, [], "ok", "meting_verouderd"),
        (-5, 120, [], "ok", "meting_verouderd"),
        (901, -1, [], "ok", "meting_verouderd"),
        (120, 0, [], "ok", "meting_verouderd"),
        (60, 120, [], "ok", "meting_onvolledig"),
        (60, 120, [{"naam": "testpool", "status": "ONLINE", "gezond": True}, {}], "ok", "meting_onvolledig"),
        (60, 120, [{"naam": "testpool", "status": "ONLINE", "gezond": "true"}], "ok", "meting_onvolledig"),
        (60, None, [{"naam": "testpool", "status": "ONLINE", "gezond": True}], "unknown", "method_unavailable"),
    ],
)
def test_onzekere_meting_geeft_geen_actuele_poolstatus(
    leeftijd: int | None, resterend: int | None, data: Any, status: str, reden: str
) -> None:
    nu = utcnow()
    gemeten = iso(nu - timedelta(seconds=leeftijd)) if leeftijd is not None else None
    staat = {
        "status": status,
        "reason_code": "method_unavailable" if status == "unknown" else None,
        "observed_at": gemeten,
        "geldig_tot": iso(nu + timedelta(seconds=resterend)) if resterend is not None else None,
        "data": data,
    }
    meting = projecteer(staat, nu)
    assert meting.status == "unknown" and meting.reason_code == reden
    assert meting.geldig_tot is None and meting.items == []
    assert iso(meting.observed_at) == gemeten
