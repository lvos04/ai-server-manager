"""De Hub bewaart alleen bij het goedgekeurde verzoek passende voor- en nametingen."""

from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from hub.actions import huis
from hub.errors import HubError
from hub.models import ActionRequest
from hub.timeutil import utcnow


@pytest.fixture
def proef():
    now = utcnow()
    voor = {"power": True, "mode": "heat", "target_c": 20.5, "controls": {"TemUn": 0, "WdSpd": 2}}
    na = {**voor, "target_c": 22}
    meta = {"proposal_id": str(uuid4()), "preview_hash": huis._hash({}), "before_hash": huis._hash(voor)}
    req = ActionRequest(
        action_id="zone.command",
        gestart_op=now - timedelta(seconds=1),
        parameters={"target_c": 22},
        resource_etag=huis._hash({"before": voor}),
        preview={"my_house": meta},
    )
    data = {
        "id": meta["proposal_id"],
        "action_id": req.action_id,
        "resource_etag": req.resource_etag,
        "preview_hash": meta["preview_hash"],
        "command_id": str(uuid4()),
        "status": "confirmed",
        "before": voor,
        "after": na,
        "before_hash": meta["before_hash"],
        "after_hash": huis._hash(na),
        "before_observed_at": (now - timedelta(seconds=2)).isoformat(),
        "after_observed_at": now.isoformat(),
    }
    conn = Mock(spec=huis.Verbinding)
    conn.vraag.return_value = data
    return req, data, conn


def test_journaal_bewaart_halve_graden_en_alle_bedienstanden(proef):
    req, data, conn = proef
    status, resultaat = huis.lees_bewijs(conn, req, data["command_id"])
    assert status == "uitgevoerd"
    assert resultaat["before"]["target_c"] == "20.5" and resultaat["after"]["target_c"] == "22"
    assert resultaat["before"]["controls"] == resultaat["after"]["controls"] == data["before"]["controls"]
    conn.vraag.assert_called_once_with("evidence/" + data["id"])


@pytest.mark.parametrize("veld", ["controls", "target_c", "command_id", "rollback_command_id", "after_observed_at"])
def test_bewijs_met_een_andere_uitkomst_of_bon_geeft_geen_bevestiging(proef, veld):
    req, data, conn = proef
    opdracht = data["command_id"]
    if veld in {"controls", "target_c"}:
        data["after"][veld] = {"TemUn": 0} if veld == "controls" else 23
        data["after_hash"] = huis._hash(data["after"])
    elif veld == "after_observed_at":
        data[veld] = data["before_observed_at"]
    else:
        data[veld] = str(uuid4())
    with pytest.raises(HubError) as fout:
        huis.lees_bewijs(conn, req, opdracht)
    assert fout.value.code == "bewijs_ongeldig"


@pytest.mark.parametrize(("herstel_nodig", "status"), [(True, "onbekend"), (False, "mislukt")])
def test_mislukte_readback_met_open_herstel_blijft_onbekend(proef, herstel_nodig, status):
    req, data, conn = proef
    data.update(status="failed", recovery_required=herstel_nodig)
    uit, _ = huis.lees_bewijs(conn, req, data["command_id"])
    assert uit == status
