"""Leg de echte leesantwoorden van één my_house-versie vast met lokale Hue-testgegevens."""

import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from shc_integrations.hue.model import HueModel
from ws_devices_support import add_device, new_home


@pytest.mark.parametrize(("geval", "stand"), [("aan", True), ("uit", False), ("onbekend", None)])
async def test_bronantwoorden(admin, geval, stand):
    home = await new_home(admin)
    for naam, waarde in (("Proefgroep", stand), ("Referentie", True)):
        rid = str(uuid4())
        resource = {"id": rid, "type": "grouped_light"}
        if waarde is not None:
            resource["on"] = {"on": waarde}
        state = HueModel({rid: resource}).group_state(rid)
        await add_device(home, "light_group", naam, state=state, compatibility="tested", lifecycle="active")

    devices = await admin.get(f"/homes/{home}/devices")
    assert devices.status_code == 200
    for versie, query in (("standaard", ""), ("v2", "?light_state_version=2")):
        lights = await admin.get(f"/homes/{home}/lights{query}")
        assert lights.status_code == 200
        pad = Path(os.environ["WONING_ANTWOORDEN"]) / f"{geval}-{versie}.json"
        pad.write_text(json.dumps({"lights": lights.json(), "devices": devices.json()}))
