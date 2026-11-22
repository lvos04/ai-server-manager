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


# ------------------------------------------------------------------ gebruiksdoel van het afgiftebewijs (R-VEILIG-1)
@pytest.mark.parametrize("soort", ["hub_service", "user"])
def test_alleen_een_dienstcontext_met_afgiftekenmerk_bereikt_de_ontsleuteling(
    monkeypatch: pytest.MonkeyPatch, soort: str
) -> None:
    """Ook als de identiteitscontrole een gebruikerscontext doorlaat, ontsleutelt de executor niets."""
    from types import SimpleNamespace
    from unittest.mock import Mock

    from asm_policy.canonical import canonical_sha256

    from executor import kluis

    rest = {"request_sha256": canonical_sha256({})}
    velden = {**rest, "claim_sha256": canonical_sha256(rest), "enc": "", "ct": ""}
    rollen = ["service"] if soort == "hub_service" else ["viewer"]
    claims = {"token_use": soort, "roles": rollen, "kluis_afgifte": velden}
    grens = Mock()
    grens.decrypt.side_effect = ValueError("lege proefbuffer")
    monkeypatch.setattr(kluis, "SUITE", grens)
    monkeypatch.setattr(kluis, "verify_hub_jwt", lambda *_a, **_k: claims)
    k = kluis.Kluis(None, Path("."))  # type: ignore[arg-type]
    monkeypatch.setattr(k, "opvraag", lambda *_a: rest)
    monkeypatch.setattr(k, "stuur", lambda *_a: SimpleNamespace(status=200, body={"afgifte": "proef"}))
    with pytest.raises(KluisFout):
        k._vraag_op({}, {}, {})
    assert grens.decrypt.call_count == int(soort == "hub_service")


# ------------------------------------------------------------------ onvolledig herstel van het journaal (R-VEILIG-2)
def _gemarkeerd_en_gekopieerd(tmp_path: Path) -> tuple[Journal, Path]:
    """Een gebruikte installatie met markering, en een herstelset met alleen de geheimenmap."""
    import shutil

    from executor.config import Settings

    bestaand = Hub(tmp_path / "origineel").settings
    Journal(bestaand.replay_db, bestaand.secrets_dir).markeer_kluis(
        str(uuid.uuid4()), "my-house", "sha256:" + "1" * 64, [{"env": "X", "type": "appgeheim"}]
    )
    kopie = Settings(data_dir=tmp_path / "hersteld")
    shutil.copytree(bestaand.secrets_dir, kopie.secrets_dir)
    return Journal(kopie.replay_db, kopie.secrets_dir), kopie.replay_db


def test_ontbrekend_journaal_is_onbekend_en_wordt_bij_lezen_niet_aangemaakt(tmp_path: Path) -> None:
    from executor.journal import JournalUnavailable

    hersteld, pad = _gemarkeerd_en_gekopieerd(tmp_path)
    with pytest.raises(JournalUnavailable):
        hersteld.kluis_gemarkeerd("my-house")
    assert not pad.exists()


def test_leeg_heraangemaakt_journaal_na_onvolledig_herstel_is_onbekend(tmp_path: Path) -> None:
    """Het starten maakt het journaal opnieuw (leeg) aan; het anker in de geheimenmap houdt de markering onbekend."""
    from executor.journal import JournalUnavailable

    hersteld, _pad = _gemarkeerd_en_gekopieerd(tmp_path)
    assert hersteld.stopped() is None
    with pytest.raises(JournalUnavailable):
        hersteld.kluis_gemarkeerd("demo-app")


def test_eerste_ingebruikname_heeft_geen_markering(tmp_path: Path) -> None:
    s = Hub(tmp_path / "nieuw").settings
    journal = Journal(s.replay_db, s.secrets_dir)
    assert journal.stopped() is None
    assert journal.kluis_gemarkeerd("my-house") is False


def test_onvolledig_hersteld_journaal_weigert_bijwerken_zonder_nas(stack: tuple[Hub, TestClient, FakeTrueNAS]) -> None:
    """De hele weg: markering, het journaal valt weg, de executor start het leeg opnieuw en weigert toch."""
    hub, c, nas = stack
    Journal(hub.settings.replay_db, hub.settings.secrets_dir).markeer_kluis(
        str(uuid.uuid4()), "demo-app", "sha256:" + "1" * 64, [{"env": "X", "type": "appgeheim"}]
    )
    for pad in hub.settings.replay_db.parent.glob(hub.settings.replay_db.name + "*"):
        pad.unlink()
    nas.mutations.clear()
    prop = _prop(nas, "app.update", {"image": {"repository": "ghcr.io/voorbeeld/my-house", "tag": f"2@{DIGEST_B}"}})
    r = execute(c, hub, approved(hub, prop))
    assert r.status_code == 409 and r.json()["code"] == "kluisplekken_recept_ontbreekt", r.text
    assert nas.mutations == []


def _momentopname(bron: Path, doel: Path) -> None:
    import sqlite3
    from contextlib import closing

    with closing(sqlite3.connect(bron)) as origineel, closing(sqlite3.connect(doel)) as kopie:
        origineel.backup(kopie)


def _markeer(journal: Journal, app: str) -> None:
    journal.markeer_kluis(str(uuid.uuid4()), app, "sha256:" + "1" * 64, [{"env": "X", "type": "appgeheim"}])


@pytest.mark.parametrize("volledig", [True, False], ids=["volledige herstelset", "oudere journaalkopie"])
def test_herstel_met_een_oudere_journaalkopie_houdt_elke_markering_onbekend(tmp_path: Path, volledig: bool) -> None:
    import shutil

    from executor.config import Settings
    from executor.journal import JournalUnavailable

    bron = Hub(tmp_path / "origineel").settings
    journal = Journal(bron.replay_db, bron.secrets_dir)
    _markeer(journal, "my-house")
    eerder = tmp_path / "eerder.sqlite3"
    _momentopname(bron.replay_db, eerder)
    _markeer(journal, "demo-app")
    doel = Settings(data_dir=tmp_path / "hersteld")
    shutil.copytree(bron.secrets_dir, doel.secrets_dir)
    _momentopname(bron.replay_db if volledig else eerder, doel.replay_db)
    hersteld = Journal(doel.replay_db, doel.secrets_dir)
    if volledig:
        assert hersteld.kluis_gemarkeerd("demo-app") is True
        assert hersteld.kluis_gemarkeerd("ongebruikt") is False
    else:
        for app in ("my-house", "demo-app", "ongebruikt"):
            with pytest.raises(JournalUnavailable):
                hersteld.kluis_gemarkeerd(app)


@pytest.mark.parametrize("bij", ["starten", "lezen"])
def test_markering_zonder_anker_uit_de_vorige_versie_krijgt_haar_anker(tmp_path: Path, bij: str) -> None:
    """Een rij zonder anker (vorige versie, of onderbroken tussen rij en anker) krijgt het anker alsnog; daarna houdt
    een herstel van alleen de geheimenmap de markering onbekend."""
    import shutil

    from executor.config import Settings
    from executor.journal import JournalUnavailable

    bron = Hub(tmp_path / "origineel").settings
    journal = Journal(bron.replay_db, bron.secrets_dir)
    _markeer(journal, "my-house")
    shutil.rmtree(journal.ankers)
    if bij == "starten":
        from executorhelpers import BASE

        from executor.app import create_app

        with TestClient(create_app(bron), base_url=BASE):
            pass
    else:
        assert journal.kluis_gemarkeerd("my-house") is True
    assert (journal.ankers / b"my-house".hex()).is_file()
    doel = Settings(data_dir=tmp_path / "hersteld")
    shutil.copytree(bron.secrets_dir, doel.secrets_dir)
    hersteld = Journal(doel.replay_db, doel.secrets_dir)
    assert hersteld.stopped() is None
    with pytest.raises(JournalUnavailable):
        hersteld.kluis_gemarkeerd("my-house")


def test_anker_van_de_vorige_versie_zonder_markeringen_is_onbekend(tmp_path: Path) -> None:
    from executor.journal import KLUIS_ANKER, JournalUnavailable

    s = Hub(tmp_path / "nieuw").settings
    journal = Journal(s.replay_db, s.secrets_dir)
    assert journal.stopped() is None
    (s.secrets_dir / KLUIS_ANKER).touch()
    with pytest.raises(JournalUnavailable):
        journal.kluis_gemarkeerd("my-house")


def test_vreemd_bestand_in_de_ankermap_is_onbekend(tmp_path: Path) -> None:
    from executor.journal import JournalUnavailable

    s = Hub(tmp_path / "nieuw").settings
    journal = Journal(s.replay_db, s.secrets_dir)
    _markeer(journal, "my-house")
    (journal.ankers / "geen-hex").touch()
    with pytest.raises(JournalUnavailable):
        journal.kluis_gemarkeerd("my-house")
