"""De kijkroute van beide Hub-versies leest HTTP-antwoorden van beide my_house-versies."""

import json
import os
from pathlib import Path

import pytest
from conftest import login_as, make_user
from test_adapterkoppelingen import ROUTE, invoer

from hub import outbound


@pytest.mark.parametrize("doel", ["my_house"], indirect=True)
@pytest.mark.parametrize("bron", ["oud", "nieuw"])
@pytest.mark.parametrize("geval", ["aan", "uit", "onbekend"])
def test_woning_bij_aparte_update(admin, app, doel, huis_simulatie, monkeypatch, bron, geval):
    code, _, _ = huis_simulatie
    link = admin.post(ROUTE, json=doel, headers=invoer(code))
    assert link.status_code == 201
    vorige_hub = os.environ["WONING_HUB"] == "oud"
    reacties = Path(os.environ["WONING_ANTWOORDEN"]) / bron
    transport = outbound.request

    def simulator(base, method, path, **opties):
        resource = path.rsplit("/", 1)[-1]
        if resource not in ("lights", "devices"):
            return transport(base, method, path, **opties)
        assert method == "GET"
        query = opties.get("query") or {}
        if resource == "lights":
            assert query == ({} if vorige_hub else {"light_state_version": "2"})
        versie = "v2" if query.get("light_state_version") == "2" else "standaard"
        data = json.loads((reacties / f"{geval}-{versie}.json").read_text())[resource]
        return outbound.Response(200, json.dumps(data).encode())

    monkeypatch.setattr(outbound, "request", simulator)
    make_user(admin, "proeflezer", "viewer")
    with login_as(app, "proeflezer") as kijker:
        antwoord = kijker.get(f"{ROUTE}/{link.json()['id']}/huis")
    assert antwoord.status_code == 200
    (woning,) = antwoord.json()["woningen"]
    assert woning["zones"]
    standen = {g["name"]: g["on"] for g in woning["licht"]["groups"]}
    verwacht = {"Referentie": True, "Proefgroep": {"aan": True, "uit": False, "onbekend": None}[geval]}
    if bron == "oud":
        # De oude bron had geen schakelmeettijd en vulde voor een ontbrekende meting false in.
        verwacht = {"Referentie": True, "Proefgroep": geval == "aan"} if vorige_hub else dict.fromkeys(verwacht)
    elif vorige_hub and geval == "onbekend":
        del verwacht["Proefgroep"]
    assert standen == verwacht
