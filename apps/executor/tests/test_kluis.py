"""Executorkant van de afzonderlijke geheime overdracht (contract 1.3 §8.3, M2; S-P2-050e).

Vormtoets per type uit de eigen regel (positief en negatief) en de markering die bijwerken met image en terugzetten
weigert vóór elke TrueNAS-aanroep. De koppelketen zelf staat in ``tests/e2e/test_kluisafgifte.py``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from asm_policy.etag import app_etag
from executorhelpers import Hub, approved, execute, nas_hub, set_write_key, write_nas
from executorhelpers import client as hub_client
from fakes.fake_truenas import FakeTrueNAS
from fastapi.testclient import TestClient
from policyhelpers import DIGEST_B, HOST, proposal

from executor.journal import Journal
from executor.kluis import KluisFout, vul_in

REF = "vault://app/demo-app/app_secret_key"
GEHEIM = "A" + "b" * 42
TOKEN = "enr_" + "C" * 43
REGEL = {
    "kluisplekken": [
        {"env": "APP_SECRET_KEY", "type": "appgeheim"},
        {"env": "HUB_ENROLLMENT_TOKEN", "type": "enrollment-token"},
    ]
}
BINDING = {"vault_refs": [{"path": "values.envs[1].value", "parameter": "app_secret_key", "ref": REF}]}
VALUES = {"envs": [{"name": "APP_MODE", "value": "prod"}, {"name": "APP_SECRET_KEY", "value": REF}]}
LINK = {"hub_url": "http://hub.test:8000", "pins": {"keyset_fingerprint": "ABCD-EFGH-JKMN-PQRS"}}


def _vul(waarden: Any = None, token: Any = TOKEN, regel: Any = REGEL, values: Any = VALUES) -> dict[str, Any]:
    afgifte = {"waarden": {"values.envs[1].value": GEHEIM} if waarden is None else waarden, "token": token}
    return vul_in(regel, BINDING, values, afgifte, LINK)


def test_vult_een_kopie_met_geheim_en_koppeling_in() -> None:
    uit = _vul()
    assert uit["envs"] == [
        {"name": "APP_MODE", "value": "prod"},
        {"name": "APP_SECRET_KEY", "value": GEHEIM},
        {"name": "HUB_URL", "value": "http://hub.test:8000"},
        {"name": "HUB_KEY_FINGERPRINT", "value": "ABCD-EFGH-JKMN-PQRS"},
        {"name": "HUB_ENROLLMENT_TOKEN", "value": TOKEN},
    ]
    assert VALUES["envs"][1]["value"] == REF  # het origineel blijft een verwijzing


@pytest.mark.parametrize(
    "geheim",
    [
        "-" + "b" * 42,  # begint met '-'
        "_" + "b" * 42,  # begint met '_'
        "A" + "b" * 41,  # 42 tekens
        "A" + "b" * 43,  # 44 tekens
        "A" + "b" * 41 + "\n",  # regeleinde
        "A" + "b" * 41 + "=",  # opvulling
        TOKEN,  # het token op de appgeheim-plek
        43,  # geen tekst
    ],
)
def test_appgeheim_met_een_andere_vorm_weigert_alles(geheim: Any) -> None:
    with pytest.raises(KluisFout) as e:
        _vul({"values.envs[1].value": geheim})
    assert e.value.code == "kluis_vorm_ongeldig" and e.value.status == 422
    assert str(geheim) not in e.value.melding and str(geheim) not in str(e.value)


@pytest.mark.parametrize(
    "token", [GEHEIM, "enr_" + "C" * 42, "enr_" + "C" * 44, "ENR_" + "C" * 43, "enr_" + "C" * 42 + "\n", None, 1]
)
def test_token_met_een_andere_vorm_weigert_alles(token: Any) -> None:
    with pytest.raises(KluisFout) as e:
        _vul(token=token)
    assert e.value.code == "kluis_vorm_ongeldig"


@pytest.mark.parametrize(
    ("naam", "waarden", "token", "regel", "values"),
    [
        ("ontbrekende waarde", {}, TOKEN, REGEL, VALUES),
        ("extra waarde", {"values.envs[1].value": GEHEIM, "values.envs[0].value": GEHEIM}, TOKEN, REGEL, VALUES),
        ("token zonder tokenplek", None, TOKEN, {"kluisplekken": REGEL["kluisplekken"][:1]}, VALUES),
        ("plek heeft geen verwijzing meer", None, TOKEN, REGEL,
         {"envs": [VALUES["envs"][0], {"name": "APP_SECRET_KEY", "value": "anders"}]}),
        ("plek is geen appgeheim volgens de regel", None, TOKEN, {"kluisplekken": REGEL["kluisplekken"][1:]}, VALUES),
    ],
)  # fmt: skip
def test_afwijkende_plekken_weigeren_alles(naam: str, waarden: Any, token: Any, regel: Any, values: Any) -> None:
    with pytest.raises(KluisFout) as e:
        _vul(waarden, token, regel, values)
    assert e.value.code == "kluis_vorm_ongeldig", naam


def test_afgifte_met_extra_velden_weigert() -> None:
    with pytest.raises(KluisFout):
        vul_in(REGEL, BINDING, VALUES, {"waarden": {}, "token": None, "typen": {}}, LINK)


# ------------------------------------------------------------------ markering: bijwerken en terugzetten
@pytest.fixture
def stack(tmp_path: Path) -> Iterator[tuple[Hub, TestClient, FakeTrueNAS]]:
    nas = write_nas().start()
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    yield hub, hub_client(hub), nas
    nas.stop()


def _prop(nas: FakeTrueNAS, action: str, params: dict[str, Any]) -> dict[str, Any]:
    target = {"host_id": HOST, "app_id": "my-house"}
    return proposal(action, target, params, expected_version=app_etag(nas.app("my-house"), nas.data["app.image.query"]))


@pytest.mark.parametrize(
    "actie",
    [
        ("app.update", {"image": {"repository": "ghcr.io/voorbeeld/my-house", "tag": f"2@{DIGEST_B}"}}),
        ("app.rollback", {"herstel_van": "00000000-0000-4000-8000-000000000001"}),
    ],
)
def test_gemarkeerde_instantie_weigert_bijwerken_en_terugzetten_zonder_nas(
    stack: tuple[Hub, TestClient, FakeTrueNAS], monkeypatch: pytest.MonkeyPatch, actie: tuple[str, dict[str, Any]]
) -> None:
    hub, c, nas = stack
    journal = Journal(hub.settings.replay_db, hub.settings.secrets_dir)
    journal.markeer_kluis(str(uuid.uuid4()), "my-house", "sha256:" + "1" * 64, [{"env": "X", "type": "appgeheim"}])
    nas.mutations.clear()

    def nooit(*_a: Any, **_k: Any) -> Any:
        raise AssertionError("waarden gelezen of bewaard")

    monkeypatch.setattr(Journal, "load_values", nooit)
    monkeypatch.setattr(Journal, "save_values", nooit)
    r = execute(c, hub, approved(hub, _prop(nas, *actie)))
    assert r.status_code == 409 and r.json()["code"] == "kluisplekken_recept_ontbreekt", r.text
    assert nas.mutations == [] and nas.updated == []


def test_onleesbaar_journaal_weigert_met_dezelfde_code(
    stack: tuple[Hub, TestClient, FakeTrueNAS], monkeypatch: Any
) -> None:
    from executor.journal import JournalUnavailable

    hub, c, nas = stack
    prop = _prop(nas, "app.update", {"image": {"repository": "ghcr.io/voorbeeld/my-house", "tag": f"2@{DIGEST_B}"}})
    req = approved(hub, prop)

    def onleesbaar(*_a: Any, **_k: Any) -> bool:
        raise JournalUnavailable("test")

    monkeypatch.setattr(Journal, "kluis_gemarkeerd", onleesbaar)
    nas.mutations.clear()
    r = execute(c, hub, req)
    assert r.status_code == 409 and r.json()["code"] == "kluisplekken_recept_ontbreekt", r.text
    assert nas.mutations == []


def test_ongemarkeerde_instantie_houdt_haar_uitkomst(stack: tuple[Hub, TestClient, FakeTrueNAS]) -> None:
    """Alleen wat de executor zelf invulde, is gemarkeerd: een andere instantie wordt gewoon bijgewerkt."""
    hub, c, nas = stack
    Journal(hub.settings.replay_db, hub.settings.secrets_dir).markeer_kluis(
        str(uuid.uuid4()), "demo-app", "sha256:" + "1" * 64, [{"env": "X", "type": "appgeheim"}]
    )
    prop = _prop(nas, "app.update", {"image": {"repository": "ghcr.io/voorbeeld/my-house", "tag": f"2@{DIGEST_B}"}})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 200 and r.json()["methode"] == "app.update", r.text
    assert [m for m in nas.mutations if m != "app.config"] == ["app.update"]
