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
from hub.redact import redact_log_text

POLICY = load_policy()
HOST = "nas-primary"
MERK = "proefgeheim"


@pytest.mark.parametrize(
    ("waarden", "verwacht"),
    [
        ({"api_token": "/padvormig/geheim", "client_secret_file": "/run/app cert/" + "a1" * 16},
         {"api_token": "***", "client_secret_file": "/run/app cert/" + "a1" * 16}),
        ({"client_secret": {"a1b2c3d4-1234-4567-a123-987654321abc": "x", "abcd1234-1234abcd": "y",
                            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa": "z"}},
         {"client_secret": {"***": "***", "*** (2)": "***", "*** (3)": "***"}}),
        ({"publication_token": MERK, "public_key": "openbaar"}, {"publication_token": "***", "public_key": "openbaar"}),
        ({"envconfig": {"MODUS": MERK}, "variables": [f"X={MERK}"], "vars": "/padvormig/geheim",
          "extra_vars": [{"name": "Y", "value": MERK}]},
         {"envconfig": {"MODUS": "***"}, "variables": ["X"], "vars": "***",
          "extra_vars": [{"name": "Y", "value": "***"}]}),
        ({"url": f"https://app.invalid/?code={MERK}&refresh_token={MERK}&mod=debug&Code_Verifier={MERK}&api-token={MERK}",
          "webhook_url": "https://app.invalid/route",
          "port": 30400},
         {"url": "https://app.invalid/?code=***&refresh_token=***&mod=debug&Code_Verifier=***&api-token=***",
          "webhook_url": "***", "port": 30400}),
        ({"seed_ratio": 1.5, "seed": MERK, "seed_path": "/run/app cert/" + "a1" * 16},
         {"seed_ratio": 1.5, "seed": "***", "seed_path": "/run/app cert/" + "a1" * 16}),
        ({"seed_ratio": MERK, "public_token": MERK}, {"seed_ratio": "***", "public_token": "***"}),
    ],
    ids=["V1", "V2", "V3", "V4", "V5", "V6", "V6-typen"],
)  # fmt: skip
def test_previewregels_deel_c(waarden: dict[str, Any], verwacht: dict[str, Any]) -> None:
    assert preview._toon(waarden) == verwacht
    if "url" in waarden:
        assert redact_log_text(waarden["url"]) == verwacht["url"]


def test_bewaarde_preview_behoudt_onderscheid_tussen_gemaskeerde_sleutels() -> None:
    oud = {
        "huidig": {
            "envs": {"MODE": True, "MODE=voorbeeld": False},
            "api_token": {"MixedCase=voorbeeld": True, "MixedCase=proeftekst": False},
        }
    }
    verwacht = {
        "huidig": {"envs": {"MODE": True, "MODE (2)": False}, "api_token": {"MixedCase": True, "MixedCase (2)": False}}
    }
    assert preview.toon_bewaarde_preview(oud) == verwacht
    assert preview.toon_bewaarde_preview(verwacht) == verwacht


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
    """Een doel met in zijn staat (``preview.huidig``, de readback van de NAS) altijd een geheim."""
    return Doel(soort="app", naam=naam, etag="etag-proef", bestaat=True, staat={"naam": naam, **staat})


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


# Velden van de preview die bewust niet door de toonfunctie gaan, met de reden (S-P2-040 herstelronde 5, W3 van
# R-VEILIG herreview 4; besluit regisseur). Elk ander veld wordt hieronder op een geplant geheim doorzocht.
BEWUST_RAUW = {
    "target": "Het doel zoals de beheerder het goedkeurt (host, app, dataset of snapshot). Het beleid toetst het vóór "
    "de preview op een vast patroon (één host, APP_NAME_RE, DATASET_RE, SNAP_NAME_RE); maskeren zou verbergen wat er "
    "wordt goedgekeurd.",
    "resource_etag": "De ETag van de gelezen staat (een SHA-256, of 'dataset:'/'snapshot:' plus de naam uit target). "
    "De goedkeuring is eraan gebonden; een gewijzigde tekst zou die binding breken.",
}
PREVIEW_VELDEN = {
    "schema", "action_id", "omschrijving", "target", "parameters_sha256", "uitvoerder", "risk_class", "rule_ids",
    "goedkeuring_nodig", "requires_backup", "opslagmutatie", "herkend_als", "kritiek", "policy_hash", "resource_etag",
    "huidig", "wijziging", "dataretentie", "terugdraaien",
}  # fmt: skip


@pytest.mark.parametrize("g", GEVALLEN, ids=[g.naam for g in GEVALLEN])
def test_de_hele_preview_bevat_geen_geheim_buiten_de_bewust_rauwe_velden(g: Geval) -> None:
    """Bewaking (S-P2-040 herstelronde 5, W3; besluit regisseur): de HELE preview, ook ``huidig`` (de readback van de
    NAS), wordt doorzocht. Alleen de velden in :data:`BEWUST_RAUW` blijven rauw, elk met een reden. Komt er een veld
    bij (ook een rauw veld naast ``wijziging``), dan is deze test rood tot het door de toonfunctie gaat of met een
    reden in :data:`BEWUST_RAUW` staat."""
    actie = POLICY.actie(g.action_id)
    assert actie is not None, g.action_id
    cls = classify(POLICY, action_id=g.action_id, target={"host_id": HOST}, parameters={}, actor_type="user")
    getoond, _hash = preview.bouw(POLICY, actie, cls, g.target, g.parameters, g.doel)
    assert set(getoond) == PREVIEW_VELDEN, (
        set(getoond) ^ PREVIEW_VELDEN,
        "een nieuw veld gaat door de toonfunctie, of staat met een reden in BEWUST_RAUW",
    )
    assert set(BEWUST_RAUW) <= PREVIEW_VELDEN and all(BEWUST_RAUW.values())
    assert MERK in json.dumps(g.doel.staat), "geen geheim geplant in de staat van het doel"
    assert getoond["huidig"] == preview._toon(g.doel.staat)
    rest = {k: v for k, v in getoond.items() if k not in BEWUST_RAUW}
    assert MERK not in json.dumps(rest), [k for k, v in rest.items() if MERK in json.dumps(v)]


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
     "environment_variables", "EXTRA_ENV", "omgevingsvariabelen", "environments", "omgeving", "EnvVars", "envvars",
     "ENV.VARS", "app-env", "environmentVariables"],
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


# ---------------------------------------------------------------------- S-P2-040 herstelronde 5 (R-VEILIG-14 t/m 17)
@pytest.mark.parametrize(
    "naam",
    ["api.key", "Api.Key", "x.api.key", "access-key", "access.key", "encryption_key", "license.key", "db_pwd", "auth",
     "client-secret", "client.secret", "private-key", "x-api-key", "apiKey", "apikey", "AccessKey", "masterKey",
     "signing.key", "dbpwd", "basic_auth", "Auth", "auth.user"],
)  # fmt: skip
def test_geheime_sleutelnamen_ook_genormaliseerd(naam: str) -> None:
    """R-VEILIG-14 (H1; besluit regisseur): een geheim-achtige sleutelnaam telt ook genormaliseerd (``_nk``, zonder punt
    of streep), net als een naam die op ``key`` eindigt, een naam met ``pwd`` en ``auth`` als los deel van de naam. Als
    sleutel en als ``key`` van een paar (label)."""
    assert preview._toon({"app": {naam: f"{MERK}-130"}}) == {"app": {naam: "***"}}
    assert preview._toon({"labels": [{"key": naam, "value": f"{MERK}-131"}]}) == {
        "labels": [{"key": naam, "value": "***"}]
    }


@pytest.mark.parametrize("naam", ["key", "Key", "KEY", "author", "authority", "keyboard", "port", "ndots"])
def test_de_kale_key_en_gewone_namen_blijven_zichtbaar(naam: str) -> None:
    """R-VEILIG-14, tegenproef: de kale ``key`` (de naam van een labelpaar) en namen waarin ``auth`` alleen deel van
    een ander woord is, tellen niet als geheim."""
    assert preview._toon({"app": {naam: "zichtbaar"}}) == {"app": {naam: "zichtbaar"}}
    assert preview._toon({"labels": [{"key": naam, "value": "zichtbaar"}]}) == {
        "labels": [{"key": naam, "value": "zichtbaar"}]
    }


def test_url_met_alleen_een_wachtwoord() -> None:
    """R-VEILIG-15 (H3): ``redact_text`` herkent ook een URL met een lege gebruikersnaam (``redis://:geheim@host``),
    in een gewone waarde en in een labelwaarde; met gebruiker blijft het zoals het was."""
    assert preview._toon(
        {
            "redis_url": f"redis://:{MERK}-140@redis:6379/0",
            "labels": [{"key": "x.info", "value": f"redis://:{MERK}-141@redis:6379"}],
            "met_gebruiker": f"redis://default:{MERK}-142@redis:6379/0",
        }
    ) == {
        "redis_url": "redis://:***@redis:6379/0",
        "labels": [{"key": "x.info", "value": "redis://:***@redis:6379"}],
        "met_gebruiker": "redis://default:***@redis:6379/0",
    }


@pytest.mark.parametrize(
    "sleutel", ["openvpn", "OpenVPN", "envoy", "Envoy", "envoy_proxy", "venv", "VENV", "my.venv", "openvpn-config"]
)
def test_env_als_deel_van_een_ander_woord_is_geen_omgevingscontext(sleutel: str) -> None:
    """R-VEILIG-16 (H4; besluit regisseur): alleen een HEEL deel van de sleutel (gescheiden door ``_ . -`` of een
    hoofdletterovergang) telt als omgevingswoord. Onder ``openvpn``, ``envoy`` of ``venv`` blijven poort, server en
    hostpad zichtbaar."""
    waarde = {"port": 1194, "server": "vpn.voorbeeld.invalid", "host_path": "/mnt/testpool/apps/venv", "aan": True}
    assert preview._toon({"app": {sleutel: waarde}}) == {"app": {sleutel: waarde}}


@pytest.mark.parametrize(
    ("tekst", "verwacht"),
    [
        ("GeheimH4woord2x", "***"),  # hoofd- en kleine letters met een cijfer: willekeurig
        ("Xk9fQ2mZ7pL4wR8tH4", "***"),
        ("Z2VoZWltLWg0LWI2NC14eXo=", "***"),  # de '='-staart van base64 is geen scheiding
        ("Z2VoZWltLWg0LWI2NC14eQ==", "***"),
        ("DB_PASSWORD\nGeheimH4regel2", "DB_PASSWORD\n***"),  # per regel
        ("d41d8cd98f00b204e9800998ecf8427e", "***"),  # hexreeks
        ("k3j5h2g8f9d7s6a1x0", "***"),  # cijfers en letters met hoge entropie
        ("A" * 65, "***"),  # niet kort
        ("Xk9fQ2mZ7pL4wR8tH4=1", "***"),  # ook de naam vóór '=' moet op een naam lijken
        ("production", "production"),
        ("DB_HOST=", "DB_HOST"),
        ("DB_HOST:", "DB_HOST"),
        ("MYSQL_ROOT_PASSWORD", "MYSQL_ROOT_PASSWORD"),
        ("SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE", "SPRING_DATASOURCE_HIKARI_MAXIMUM_POOL_SIZE"),
        ("HTTP2_PORT", "HTTP2_PORT"),
        ("A" * 64, "A" * 64),
    ],
)
def test_een_losse_waarde_onder_een_omgevingssleutel_alleen_als_hij_kort_en_niet_willekeurig_is(
    tekst: str, verwacht: str
) -> None:
    """R-VEILIG-17 (H2; besluit regisseur): onder een omgevingssleutel staat een naam alleen als hij kort is (hooguit
    64 tekens) en niet willekeurig (de entropietoets van ``hub.redact._maybe_secret`` of strenger), per regel; anders
    ``***``. Een '='-staart (base64-opvulling) telt niet als scheiding."""
    assert preview._toon({"environment": tekst}) == {"environment": verwacht}
    assert preview._toon({"env": [tekst]}) == {"env": [verwacht]}


def test_sleutels_in_een_omgevingsobject_volgen_de_naamregel() -> None:
    """R-VEILIG-17 (besluit regisseur): een sleutel van een omgevingsobject gaat ook door de naamregel: ``NAAM=geheim``
    als sleutel toont alleen ``NAAM``, een willekeurige sleutel ``***``; een gewone sleutel blijft zoals hij is."""
    assert preview._toon(
        {"environment": {f"DB_HOST={MERK}-150": "", "Xk9fQ2mZ7pL4wR8tH4": "", "Name ": "x", "LEEG": ""}}
    ) == {"environment": {"DB_HOST": "", "***": "", "Name ": "***", "LEEG": ""}}


# ---------------------------------------------------------------------- S-P2-040 herstelronde 6 (R-VEILIG-18 t/m 20)
@pytest.mark.parametrize(
    "sleutel",
    ["additionalenvs", "app.additionalenvs", "extraenv", "EXTRAENV", "appenv", "app.appenv", "environ",
     "os.environ", "Environ", "dotenv", "DOTENV", "appenvironment", "extraenvironments"],
)  # fmt: skip
def test_een_deel_dat_op_een_omgevingswoord_eindigt_is_een_omgevingscontext(sleutel: str) -> None:
    """R-VEILIG-18 (J1; besluit regisseur): een deel van de sleutel dat EINDIGT op ``env``, ``envs``, ``environment`` of
    ``environments`` (``additionalenvs``, ``extraenv``, ``appenv``), en ``environ`` en ``dotenv``, is ook een
    omgevingscontext: alleen namen. ``venv``, ``openvpn`` en ``envoy`` niet (zie
    :func:`test_env_als_deel_van_een_ander_woord_is_geen_omgevingscontext`)."""
    assert preview._toon({"app": {sleutel: {"DB_HOST": f"{MERK}-160", "LEEG": "", "AAN": True}}}) == {
        "app": {sleutel: {"DB_HOST": "***", "LEEG": "", "AAN": True}}
    }
    assert preview._toon({"app": {sleutel: [f"DB_HOST={MERK}-161", {"name": "X", "value": f"{MERK}-162"}]}}) == {
        "app": {sleutel: ["DB_HOST", {"name": "X", "value": "***"}]}
    }
    assert preview._toon({"app": {sleutel: f"DB_HOST={MERK}-163\nAPP_MODE=prod"}}) == {
        "app": {sleutel: "DB_HOST\nAPP_MODE"}
    }


@pytest.mark.parametrize(
    "naam",
    ["encryption_keys", "ssh_keys", "license_keys", "sshKeys", "api.keys", "SIGNING-KEYS", "oauth", "OAUTH",
     "oauth_client", "jwt", "JWT_SIGNING", "otp", "otp_code", "mnemonic", "wallet_mnemonic", "salt", "salt_rounds",
     "dbsalt", "seed", "seed_phrase", "walletseed"],
)  # fmt: skip
def test_meervoud_op_keys_en_andere_geheime_namen(naam: str) -> None:
    """R-VEILIG-19 (J2; besluit regisseur): een genormaliseerde naam die op ``keys`` eindigt (niet de kale ``keys``) en
    ``oauth``, ``jwt``, ``otp``, ``mnemonic``, ``salt`` en ``seed`` (als los deel of aan het eind van de genormaliseerde
    naam) zijn geheim-achtig. Als sleutel en als ``key`` van een paar (label)."""
    assert preview._toon({"app": {naam: f"{MERK}-170"}}) == {"app": {naam: "***"}}
    assert preview._toon({"labels": [{"key": naam, "value": f"{MERK}-171"}]}) == {
        "labels": [{"key": naam, "value": "***"}]
    }


@pytest.mark.parametrize("naam", ["keys", "Keys", "KEYS", "pin", "PIN", "hotplug", "speed", "seeds", "keyspace"])
def test_de_kale_keys_pin_en_gewone_namen_blijven_zichtbaar(naam: str) -> None:
    """R-VEILIG-19, tegenproef (besluit regisseur): de kale ``keys`` en ``pin`` tellen niet als geheim-achtig, net als
    een naam waarin ``otp`` of ``seed`` alleen midden in een ander woord staat."""
    assert preview._toon({"app": {naam: "zichtbaar"}}) == {"app": {naam: "zichtbaar"}}
    assert preview._toon({"labels": [{"key": naam, "value": "zichtbaar"}]}) == {
        "labels": [{"key": naam, "value": "zichtbaar"}]
    }


def test_onder_een_geheime_naam_blijft_de_vorm_staan() -> None:
    """R-VEILIG-20 (J3; besluit regisseur): onder een geheim-achtige naam blijven sleutels, ja/nee, leeg en ``None``
    zichtbaar; alleen tekst- en getalbladen worden ``***``. Zo ziet de beheerder dat ``basic_auth`` uit staat."""
    assert preview._toon({"app": {"basic_auth": {"enabled": False}}}) == {"app": {"basic_auth": {"enabled": False}}}
    assert preview._toon({"app": {"auth": {"enabled": True, "port": 8443}}}) == {
        "app": {"auth": {"enabled": True, "port": "***"}}
    }
    assert preview._toon(
        {"client_secret": {"a": f"{MERK}-180", "leeg": "", "niets": None, "lijst": [f"{MERK}-181", 3, 1.5, False]}}
    ) == {"client_secret": {"a": "***", "leeg": "", "niets": None, "lijst": ["***", "***", "***", False]}}
    assert preview._toon({"api_tokens": [{"naam": f"{MERK}-182", "aan": True}]}) == {
        "api_tokens": [{"naam": "***", "aan": True}]
    }


@pytest.mark.parametrize(
    ("naam", "pad"),
    [("tls.key", "/mnt/testpool/certs/app.key"), ("ssl_key", "/etc/ssl/private/app.key"),
     ("client_secret_file", "/run/secrets/client_secret"), ("env_file", "/mnt/testpool/apps/app.env"),
     ("env_files", ["/mnt/testpool/apps/a.env", "/mnt/testpool/apps/b.env"])],
)  # fmt: skip
def test_een_absoluut_pad_onder_een_geheime_naam_of_omgevingssleutel_blijft_zichtbaar(naam: str, pad: Any) -> None:
    """R-VEILIG-20 (besluit regisseur): een absoluut pad (begint met ``/``) verwijst naar een bestand en is zelf geen
    geheim; het blijft zichtbaar onder een geheim-achtige naam en onder een omgevingssleutel (``env_file``)."""
    assert preview._toon({"app": {naam: pad}}) == {"app": {naam: pad}}


@pytest.mark.parametrize("naam", ["public_key", "publickey", "PublicKey", "public.keys", "PUBLIC_KEY"])
def test_namen_die_met_public_beginnen_zijn_niet_geheim_achtig(naam: str) -> None:
    """R-VEILIG-20 (besluit regisseur): een naam die genormaliseerd met ``public`` begint, telt niet als geheim-achtig;
    ``redact_text`` werkt er wel op."""
    sleutel = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5 beheer"
    assert preview._toon({"app": {naam: sleutel}}) == {"app": {naam: sleutel}}
    assert preview._toon({"app": {naam: f"https://beheer:{MERK}-190@h/x"}}) == {"app": {naam: "https://beheer:***@h/x"}}
    assert preview._toon({"labels": [{"key": naam, "value": sleutel}]}) == {"labels": [{"key": naam, "value": sleutel}]}


@pytest.mark.parametrize(
    "waarde",
    ["/Xk9fQ2mZ7pL4wR8tH4", "/mnt/d41d8cd98f00b204e9800998ecf8427e/app.key", f"/x\nDB={MERK}-200", f"/a={MERK}-201",
     f"/a {MERK}-202", f"/a:{MERK}-203", f"relatief/{MERK}-204", "/"],
)  # fmt: skip
def test_wat_niet_op_een_pad_lijkt_blijft_verborgen(waarde: str) -> None:
    """R-VEILIG-20, tegenproef (invulling van het besluit): als pad telt alleen één regel die met ``/`` begint, zonder
    witruimte, ``=`` of ``:``, met minstens één teken na de ``/`` en zonder een willekeurig deel (dezelfde toets als in
    een omgevingscontext; een base64-geheim kan met ``/`` beginnen). Anders blijft het ``***`` onder een geheime
    naam."""
    assert preview._toon({"app": {"encryption_key": waarde}}) == {"app": {"encryption_key": "***"}}


def test_sleutels_onder_een_geheime_naam_en_paren() -> None:
    """R-VEILIG-20 (invulling van het besluit): een sleutel onder een geheim-achtige naam blijft zichtbaar, behalve als
    hij zelf op een geheim lijkt (willekeurig, of ``NAAM=waarde``: dan alleen de naam, zoals in een omgevingsobject).
    Een label met een geheime ``key`` en een pad als ``value`` toont het pad; de ``value`` van een omgevingsvariabele
    (paar met ``name``) blijft altijd ``***`` (ADR-0030 besluit 28)."""
    assert preview._toon({"tokens": {"Xk9fQ2mZ7pL4wR8tH4": "beheer", f"DB={MERK}-210": "x", "enabled": True}}) == {
        "tokens": {"***": "***", "DB": "***", "enabled": True}
    }
    assert preview._toon({"labels": [{"key": "tls.key", "value": "/mnt/testpool/certs/app.key"}]}) == {
        "labels": [{"key": "tls.key", "value": "/mnt/testpool/certs/app.key"}]
    }
    assert preview._toon({"app": {"additional_envs": [{"name": "CERT", "value": "/mnt/testpool/certs/app.key"}]}}) == {
        "app": {"additional_envs": [{"name": "CERT", "value": "***"}]}
    }
    assert preview._toon(
        {"app": {"extra": [{"name": "CERT", "value": "/mnt/testpool/certs/app.key"}, {"Name": "X", "Value": {"a": 1}}]}}
    ) == {"app": {"extra": [{"name": "CERT", "value": "***"}, {"Name": "X", "Value": "***"}]}}
