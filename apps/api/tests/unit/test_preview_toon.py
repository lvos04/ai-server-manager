"""Preview: elk veld van ``wijziging`` gaat door één toonfunctie (S-P2-040, herstelronde 4; ADR-0030 besluit 32).

Zuivere functies met het echte beleid, zonder database. De keten via de API (voorstel, kijker, lijst) staat in
``apps/api/tests/integration/test_acties.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest
from asm_policy import load_policy
from asm_policy.engine import classify

from hub.actions import preview
from hub.actions.doel import Doel

POLICY = load_policy()
HOST = "nas-primary"
MERK = "proefgeheim"


def _g(n: int) -> str:
    """Een geheim in de vorm die ``hub.redact.redact_text`` herkent: een URL met wachtwoord."""
    return f"https://beheer:{MERK}-{n}@db.invalid/x"


def _b(n: int) -> str:
    """Een geheim als ``Bearer``-token (zonder ``@``, voor een image-tag: die wordt bij ``@`` gesplitst)."""
    return f"Bearer {MERK}-{n}-abcdefgh"


@dataclass
class Geval:
    """Eén actie met in elke bron van ``wijziging`` een geheim. ``vast``: velden zonder vrije tekst (een vaste tekst,
    ja/nee, een kluisverwijzing of ``None``); elk ander veld moet ruw een geheim bevatten en getoond niet meer."""

    naam: str
    action_id: str
    parameters: dict[str, Any]
    doel: Doel
    vast: set[str]
    target: dict[str, Any] = field(default_factory=lambda: {"host_id": HOST, "app_id": "demo-app"})


def _doel(naam: str = _g(1), **staat: Any) -> Doel:
    return Doel(soort="app", naam=naam, etag="etag-proef", bestaat=True, staat=dict(staat))


def _values() -> dict[str, Any]:
    return {
        "ports": [{"port_number": _g(10), "container_port": _g(11), "protocol": _g(12), "bind_mode": _g(13)}],
        "storage": [{"type": _g(14), "mount_path": _g(15), "host_path_config": {"path": _g(16)}, "read_only": True}],
        "envs": [{"name": _g(17), "value": _g(18)}],
        "resources": {"limits": {"cpus": _g(19)}, "api_token": f"{MERK}-20", "gpus": {"x": _g(21)}},
        "restart_policy": _g(22),
        "host_network": True,
        "notes": _g(23),
    }


def _manifest() -> dict[str, Any]:
    return {
        "app_id": _g(30),
        "version": _g(31),
        "image_digest": _g(32),
        "manifest_sha256": _g(33),
        "host_network_reason": _g(34),
        "install_reason": _g(35),
        "gpu": _g(36),
        "post_install_checks": [{"id": _g(37), "soort": _g(38), "beschrijving_nl": _g(39)}],
    }


INSTALL_VAST = {"soort", "custom_compose", "privileged", "gpu", "host_network", "kluisverwijzingen"}
GEVALLEN = [
    Geval(
        "install_catalogusapp",
        "app.install",
        {
            "app_create": {
                "app_name": "demo-app",
                "catalog_app": _g(40),
                "train": _g(41),
                "version": _g(42),
                "values": _values(),
            },
            "manifest": _manifest(),
        },
        _doel(),
        INSTALL_VAST | {"image"},  # een catalogusapp heeft geen verwachte image (None)
        target={"host_id": HOST, "app_id": _g(43)},
    ),
    Geval(
        "install_standaard_custom_app",
        "app.install",
        {
            "app_create": {
                "app_name": "demo-app",
                "catalog_app": "ix-app",
                "train": "stable",
                "version": _g(47),
                "values": {**_values(), "image": {"repository": _g(44), "tag": _b(45)}},
            },
            "manifest": _manifest(),
        },
        _doel(),
        INSTALL_VAST | {"installatiemethode"},  # een vaste tekst bij de standaard Custom App
        target={"host_id": HOST, "app_id": _g(46)},
    ),
    Geval(
        "uninstall",
        "app.uninstall",
        {},
        _doel(_g(50)),
        {"soort", "alleen_containers", "remove_ix_volumes", "remove_images"},
    ),
    Geval(
        "update_image",
        "app.update",
        {"image": {"repository": _g(51), "tag": _b(52)}, "image_digest": _g(53)},
        _doel(_g(54), images=[_g(55)]),
        {"soort"},
    ),
    Geval("update_catalogus", "app.update", {"catalog_version": _g(56)}, _doel(_g(57), versie=_g(58)), {"soort"}),
    Geval("rollback_herstel", "app.rollback", {"herstel_van": _g(60)}, _doel(_g(61)), {"soort", "methode"}),
    Geval("rollback_catalogus", "app.rollback", {"catalog_version": _g(62)}, _doel(_g(63)), {"soort"}),
    Geval("restart", "app.restart", {}, _doel(_g(64)), {"soort", "verwacht"}),
    Geval("stop", "app.stop", {}, _doel(_g(65)), {"soort", "verwacht"}),
    Geval("start", "app.start", {}, _doel(_g(66)), {"soort", "verwacht"}),
    Geval(
        "snapshot",
        "zfs.snapshot.create",
        {"naam": _g(67), "recursief": True},
        _doel(_g(68)),
        {"soort", "recursief"},
        target={"host_id": HOST, "dataset": "p/x"},
    ),
    Geval(
        "kloon",
        "zfs.snapshot.clone_to_sandbox",
        {"doel_dataset": _g(69)},
        _doel(_g(70)),
        {"soort"},
        target={"host_id": HOST, "snapshot": "p/x@s"},
    ),
    Geval(
        "melding", "notification.send", {"titel": _g(71), "prioriteit": _g(72)}, _doel(), {"soort"}, {"host_id": HOST}
    ),
    Geval("sso_registreren", "sso.oidc.hub.register", {"x": _g(73)}, _doel(), {"soort"}, {"host_id": HOST}),
    Geval("sso_intrekken", "sso.sessions.revoke", {"x": _g(74)}, _doel(), {"soort"}, {"host_id": HOST}),
]


def _bouw(g: Geval) -> tuple[dict[str, Any], dict[str, Any]]:
    """(``wijziging`` zoals hij in de preview staat, dezelfde velden nog ruw)."""
    actie = POLICY.actie(g.action_id)
    assert actie is not None, g.action_id
    cls = classify(POLICY, action_id=g.action_id, target={"host_id": HOST}, parameters={}, actor_type="user")
    getoond, _hash = preview.bouw(POLICY, actie, cls, g.target, g.parameters, g.doel)
    return getoond["wijziging"], preview._wijziging(actie, g.target, g.parameters, g.doel)


def test_elke_actie_van_het_beleid_heeft_een_geval() -> None:
    """Bewaking: komt er een actie bij in het beleid, dan ook een geval hieronder (anders blijft zijn ``wijziging``
    ongetest)."""
    assert set(POLICY.acties) <= {g.action_id for g in GEVALLEN}


@pytest.mark.parametrize("g", GEVALLEN, ids=[g.naam for g in GEVALLEN])
def test_elk_veld_van_wijziging_gaat_door_de_toonfunctie(g: Geval) -> None:
    """Bewaking (S-P2-040, herstelronde 4, besluit regisseur punt 1; R-VEILIG-13): geen rauw veld in
    ``preview.wijziging``. Elk veld dat niet vast is, bevat ruw een geheim en getoond niet meer. Komt er een veld bij
    zonder toon (ook na de toonfunctie in ``bouw``), of een veld dat dit geval niet kent, dan is deze test rood."""
    getoond, ruw = _bouw(g)
    assert set(getoond) == set(ruw), set(getoond) ^ set(ruw)
    for veld in sorted(ruw):
        if veld in g.vast:
            assert MERK not in json.dumps(ruw[veld]), (veld, "staat als vast, maar bevat een geheim")
            continue
        assert MERK in json.dumps(ruw[veld]), (veld, "geen geheim geplant: voeg een bron toe aan dit geval")
        assert MERK not in json.dumps(getoond[veld]), (veld, getoond[veld])
    assert getoond == preview._toon(ruw)


@pytest.mark.parametrize(
    ("tekst", "verwacht"),
    [
        ("DB_HOST=waarde", "DB_HOST"),
        ("DB_HOST: waarde", "DB_HOST"),
        (" DB_HOST = waarde", "DB_HOST"),
        ("ALLEEN", "ALLEEN"),
        ("production", "production"),
        ("_x9=1", "_x9"),
        ("", ""),
        (f"postgres://beheer:{MERK}-80@db/app", "postgres"),
        (f"Bearer {MERK}-81-abcdefgh", "***"),
        (f"export DB={MERK}-82", "***"),
        (f"1X={MERK}-83", "***"),
        (f"DB.HOST={MERK}-84", "***"),
        (f"={MERK}-85", "***"),
        (f"DB_HOST=x\nLD_PRELOAD=/opt/{MERK}-86.so", "DB_HOST\nLD_PRELOAD"),
        (f"A=1\r\n\r\nB {MERK}-87", "A\n\n***"),
    ],
)
def test_tekst_in_een_omgevingscontext_toont_alleen_namen(tekst: str, verwacht: str) -> None:
    """Besluit regisseur punt 3 (R-VEILIG-10): per regel alleen de naam vóór '=' of ':' (of de hele regel) als die op
    een variabelenaam lijkt (``^[A-Za-z_][A-Za-z0-9_]*``), anders ``***``; een lege regel blijft leeg."""
    assert preview._toon({"environment": tekst}) == {"environment": verwacht}
    assert preview._toon({"environment": [tekst]}) == {"environment": [verwacht]}


@pytest.mark.parametrize(
    "sleutel",
    ["env", "Env", "ENVS", "environment", "additional_envs", "Additional-Envs", "additionalEnvs", "env_vars",
     "environment_variables", "EXTRA_ENV", "omgevingsvariabelen"],
)  # fmt: skip
def test_elke_omgevingssleutel_toont_alleen_namen(sleutel: str) -> None:
    """Besluit regisseur punt 3 (R-VEILIG-12): elke sleutel waarvan de genormaliseerde naam ``env`` bevat (en het
    Nederlandse ``omgeving``) toont alleen namen: een object de sleutels met ``***``, een lijst per tekst de naam en
    per paar de naam. Leeg en ja/nee blijven zichtbaar."""
    waarde = {
        "object": {"DB_HOST": f"{MERK}-90", "LEEG": "", "AAN": True, "GETAL": 3},
        "lijst": [f"DB_HOST={MERK}-91", {"name": "X", "value": f"{MERK}-92", "extra": f"{MERK}-93"}, 7, [f"{MERK}-94"]],
    }
    assert preview._toon({sleutel: waarde["object"]}) == {
        sleutel: {"DB_HOST": "***", "LEEG": "", "AAN": True, "GETAL": "***"}
    }
    assert preview._toon({sleutel: waarde["lijst"]}) == {
        sleutel: ["DB_HOST", {"name": "X", "value": "***", "extra": "***"}, "***", "***"]
    }


def test_een_object_met_een_variabele_name_in_een_omgevingscontext_toont_geen_waarden() -> None:
    """R-VEILIG-9: een object met een sleutel ``NAME`` (elke schrijfwijze) maar zonder ``value`` is geen paar; onder een
    omgevingssleutel staan dan alle waarden als ``***``. Bij een echt paar staat alleen de naam erin."""
    assert preview._toon({"environment": {"NAME": "mijnapp", "DB_HOST": f"{MERK}-100"}}) == {
        "environment": {"NAME": "***", "DB_HOST": "***"}
    }
    assert preview._toon({"env": [{"Name": "mijnapp", "DB_HOST": f"{MERK}-101"}]}) == {
        "env": [{"Name": "***", "DB_HOST": "***"}]
    }
    assert preview._toon({"env": [{"KEY": "DB_HOST", "Value": f"{MERK}-102", "Name ": "Y"}]}) == {
        "env": [{"KEY": "***", "Value": "***", "Name ": "Y"}]
    }


@pytest.mark.parametrize(
    ("paar", "verwacht"),
    [
        ({"Key": "x.token", "Value": f"{MERK}-110"}, {"Key": "x.token", "Value": "***"}),
        ({"KEY": "proef.password", "VALUE": f"{MERK}-111"}, {"KEY": "proef.password", "VALUE": "***"}),
        ({"key": "x.info", "VALUE": "zichtbaar"}, {"key": "x.info", "VALUE": "zichtbaar"}),
        ({"Name": "ENCRYPTION_KEY", "Value": f"{MERK}-112"}, {"Name": "ENCRYPTION_KEY", "Value": "***"}),
        ({"name": "Web", "port": 30555}, {"name": "Web", "port": 30555}),  # geen value: geen paar
        ({"key": "ndots", "value": "2"}, {"key": "ndots", "value": "2"}),
    ],
)
def test_paren_in_elke_schrijfwijze(paar: dict[str, Any], verwacht: dict[str, Any]) -> None:
    """Besluit regisseur punt 2 (R-VEILIG-11): ``key``, ``name`` en ``value`` worden herkend in elke schrijfwijze (zoals
    ``_nk`` in het beleid); een paar telt alleen met zowel een naam (``name``/``key``) als een ``value``."""
    assert preview._toon(paar) == verwacht
    assert preview._toon({"app": {"labels": [paar]}}) == {"app": {"labels": [verwacht]}}


def test_overige_vrije_tekst_en_sleutels_gaan_door_redact_text() -> None:
    """Besluit regisseur punt 4: elke andere tekst gaat door ``redact_text`` (geen terugval ten opzichte van c359877),
    ook een sleutel; twee sleutels die daarna gelijk zijn, blijven allebei staan."""
    getoond = preview._toon(
        {
            "url": f"postgres://beheer:{MERK}-120@db/app",
            "kop": f"Bearer {MERK}-121-abcdefgh",
            "https://beheer:pw-122@h/x": 1,  # geen geheim-achtige sleutelnaam: alleen redact_text werkt hier
            "https://beheer:pw-123@h/x": 2,
        }
    )
    assert getoond == {
        "url": "postgres://beheer:***@db/app",
        "kop": "Bearer ***",
        "https://beheer:***@h/x": 1,
        "https://beheer:***@h/x (2)": 2,
    }
