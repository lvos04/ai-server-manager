"""Dienst-E2E: catalogusinstallatie via een eigen plannerplan (contract 1.3 §8.1/§8.2; ADR-0032 deel D; Sim-getest).

Echte Hub, echte executor en de fake TrueNAS; appstore en planner zijn fakes die doen wat het contract vraagt (de
echte diensten kennen de §8.1-velden en ``catalog_binding`` nog niet). Alleen testwaarden, nooit een echte NAS.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from actiehelpers import (
    Stack,
    app_target,
    bouw_stack,
    haal,
    keur_goed,
    schrijfaanroepen,
    stel_voor,
    voer_uit,
)
from asm_policy.canonical import canonical_json, canonical_sha256
from conftest import enroll_body, idem, login_as, make_user, service_jwk
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from executorhelpers import write_nas
from fakes.fake_appstore import FakeAppstore
from fakes.fake_planner import FakePlanner
from fakes.fake_truenas import FakeTrueNAS
from policyhelpers import (
    DIGEST,
    catalogus_regel,
    install_params,
    policy_met_regels,
    provenance_record,
)

from hub.catalog.plannen import SCHEMA_SHA256

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
APPSTORE_SEED = b"\x11" * 32
# Een volgens de gepinde validator geldig testmanifest (fictieve app, testdigest).
MANIFEST: dict[str, Any] = {
    "manifest_version": "1",
    "app_id": "demo-app",
    "name": "Demo",
    "owner_repo": "voorbeeld/demo-app",
    "category": "other",
    "description_nl": "Fictieve app voor de Hub-ketentest van de catalogusinstallatie.",
    "version": "1.2.3",
    "install": {"method": "custom_app"},
    "image": {
        "repository": "ghcr.io/voorbeeld/demo-app",
        "tag": "1.2.3",
        "digest": "sha256:" + "a" * 64,
    },
    "custom_app": {
        "storage": [{"name": "data", "type": "host_path", "host_path": {"param": "data_path"}}],
        "env": [
            {"name": "APP_MODE", "value": "prod"},
            {"name": "PUBLIC_URL", "value_from": {"param": "public_url"}},
        ],
        "resources": {"cpus": 2, "memory_mib": 1024},
        "gpu": "none",
        "run_as": {"mode": "custom", "user": 568, "group": 568},
        "timezone": "Etc/UTC",
        "restart_policy": "unless-stopped",
        "portal": {"port": "web", "scheme": "http", "path": "/", "name": "Web UI"},
    },
    "parameters": [
        {
            "name": "web_port",
            "type": "port",
            "source": "default",
            "default": 30555,
            "required": True,
            "description_nl": "Hostpoort voor de webinterface.",
        },
        {
            "name": "data_path",
            "type": "path",
            "source": "dataset_picker",
            "dataset_role": "demo_data",
            "decision": "D02",
            "required": True,
            "description_nl": "Dataset voor de gegevens.",
        },
        {
            "name": "public_url",
            "type": "url",
            "source": "wizard",
            "decision": "D03",
            "required": False,
            "description_nl": "Adres waarop de app bereikbaar is.",
        },
    ],
    "storage": [
        {
            "name": "data",
            "mount": "/data",
            "kind": "data",
            "required_dataset_role": "demo_data",
        }
    ],
    "network": {
        "ports": [
            {
                "name": "web",
                "container_port": 8080,
                "host_port": {"param": "web_port"},
                "protocol": "tcp",
            }
        ],
        "host_network": False,
        "host_network_reason": None,
    },
    "privileges": {"privileged": False, "cap_add": [], "devices": [], "gpu": "none"},
    "privilege_reason": "Upstream-image als Custom App. Restrisico: zonder no-new-privileges kan een "
    "setuid-programma binnen de container root worden.",
    "healthcheck": {
        "type": "http",
        "path": "/healthz",
        "port": "web",
        "interval_s": 30,
        "timeout_s": 5,
        "retries": 3,
    },
    "backup": {
        "db_export": {"method": "none"},
        "snapshot_datasets": ["data"],
        "rpo": "PT24H",
        "rto": "PT4H",
    },
    "dependencies": [],
    "sso": "native",
    "risk": {"install": "R2", "update": "R2", "uninstall": "R2"},
    "upgrade": {"migrations": False, "tag_only_rollback_safe": True},
    "decisions_required": ["D02", "D03"],
    "docs": ["B08_APPSTORE_LIFECYCLE"],
    "validation_status": "unvalidated",
    "post_install_checks": [
        {
            "id": "http_bereikbaar",
            "soort": "http",
            "beschrijving_nl": "De webinterface antwoordt.",
        }
    ],
}
REGEL = catalogus_regel(manifest_sha256=canonical_sha256(MANIFEST), schema_sha256=SCHEMA_SHA256)
RECORD = provenance_record(REGEL)
VERSION_ID, ENTRY_ID = RECORD["version_id"], RECORD["entry_id"]
SOURCE_ID = RECORD["source"]["source_id"]


def _onderteken(record: dict[str, Any]) -> dict[str, Any]:
    key = Ed25519PrivateKey.from_private_bytes(APPSTORE_SEED)
    raw = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return {
        "record": record,
        "signature": base64.b64encode(key.sign(canonical_json(record))).decode(),
        "key_id": hashlib.sha256(raw).hexdigest()[:16],
        "alg": "EdDSA",
    }


@dataclass
class Keten:
    stack: Stack
    store: FakeAppstore
    planner: FakePlanner


def _inschrijven(admin: Any, app_id: str, jwk: dict[str, str] | None = None) -> str:
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id})
    assert r.status_code == 201, r.text
    r = admin.post(
        "/api/v1/services/enroll",
        json=enroll_body(app_id, token=r.json()["enrollment_token"], jwk=jwk),
    )
    assert r.status_code == 200, r.text
    return str(r.json()["service_id"])


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def keten(
    admin: Any,
    app: Any,
    nas: FakeTrueNAS,
    worker_once: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Keten]:
    from hub.actions import beleid

    monkeypatch.setenv("ASM_POLICY_DIR", str(policy_met_regels(tmp_path / "policy", [REGEL])))
    beleid._geladen.cache_clear()
    stack = bouw_stack(
        admin=admin,
        app=app,
        nas=nas,
        worker_once=worker_once,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )
    hub_key = app.state.keyring().jwt_signing.public_key()
    store_id = _inschrijven(admin, "appstore-en-fork", service_jwk(APPSTORE_SEED))
    _inschrijven(admin, "jelly-leon-platform")
    store = FakeAppstore(hub_key, service_id=store_id).start()
    store.routes = {
        f"/catalog/v1/versions/{VERSION_ID}": {
            "id": VERSION_ID,
            "entry_id": ENTRY_ID,
            "app_id": "demo-app",
            "version": "1.2.3",
            "source_id": SOURCE_ID,
            "manifest": MANIFEST,
            "provenance": _onderteken(RECORD),
        },
        "/catalog/v1/entries/demo-app": {
            "entry_id": ENTRY_ID,
            "app_id": "demo-app",
            "source": {"id": SOURCE_ID},
        },
        f"/catalog/v1/sources/{SOURCE_ID}": {
            "id": SOURCE_ID,
            "kind": "git",
            "enabled": True,
            "require_signature": True,
            "url": REGEL["source"]["url"],
            "subpath": REGEL["source"]["subpath"],
            "pinned_commit": REGEL["source"]["commit"],
            "trusted_key_id": REGEL["publisher_key_sha256"][7:23],
        },
    }
    stap = install_params("demo-app")
    stap["manifest"]["manifest_sha256"] = REGEL["manifest_sha256"]  # zoals de planner uit zijn validatierapport
    planner = FakePlanner(hub_key, stap).start()
    urls = {"appstore-en-fork": store.url, "jelly-leon-platform": planner.url}
    # In productie komen de adressen uit de inventaris (app.query + D03); hier zijn het de testservers.
    monkeypatch.setattr(
        "hub.catalog.plannen.service_base_url",
        lambda db, s, svc: (urls[svc.app_id], None),
    )
    yield Keten(stack, store, planner)
    store.stop()
    planner.stop()
    stack.stop()
    beleid._geladen.cache_clear()


VOLLEDIG = {"public_url": "https://demo.test/", "data_path": "/mnt/testpool/apps/demo"}  # alles wat de vertaling vraagt


def _plan(admin: Any, **wijzig: Any) -> Any:
    body: dict[str, Any] = {
        "app_id": "demo-app",
        "version_id": VERSION_ID,
        "app_name": "demo-app",
        "parameters": dict(VOLLEDIG),
        "doel": {"truenas_version": "25.04.2", "ix_app_version": "1.4.8"},
    }
    body.update(wijzig)
    return admin.post("/api/v1/catalog/plans/install", json=body, headers=idem())


def _stel_voor(admin: Any, plan: dict[str, Any]) -> Any:
    return admin.post(
        f"/api/v1/catalog/plans/{plan['plan_id']}/steps/{plan['step_id']}/propose",
        headers=idem(),
    )


def test_installeren_via_eigen_plan_met_readback_en_registratie(keten: Keten) -> None:
    admin, nas = keten.stack.admin, keten.stack.nas
    r = _plan(admin)
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["status"] == "klaar_voor_voorstel" and plan["step_id"] == "installeren"
    assert keten.planner.rejected == [] and keten.store.rejected == []
    gestuurd = keten.planner.plans[plan["plan_id"]]["catalog_binding"]
    assert set(gestuurd) == {
        "appstore_service_id",
        "source_approval_revision",
        "provenance",
        "release",
        "instance",
    }
    assert gestuurd["release"]["image_digests"] == [DIGEST] and gestuurd["instance"]["expected_version"] == "absent"

    r = _stel_voor(admin, plan)
    assert r.status_code == 201, r.text
    v = r.json()
    assert v["risk_class"] == "R2" and v["status"] == "wacht_op_goedkeuring" and v["blokkades"] == [], v
    assert keur_goed(admin, v).status_code == 200
    r = voer_uit(admin, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    assert schrijfaanroepen(nas) == ["app.create"] and len(nas.created) == 1

    nu = admin.get(f"/api/v1/catalog/plans/{plan['plan_id']}").json()
    assert nu["status"] == "geinstalleerd_controles_open" and nu["melding"]["status"] == "gemeld"
    assert nu["registratie"]["digests"] == [f"ghcr.io/voorbeeld/demo-app@{DIGEST}"]
    assert nu["registratie"]["host_poort"] is None and nu["controles_na_installatie"]
    [melding] = keten.planner.results
    assert melding["status"] == "voltooid" and melding["execution_id"] == v["request_id"]
    assert melding["readback"]["digests"] == nu["registratie"]["digests"]
    # Eén plan, één voorstel.
    r = _stel_voor(admin, plan)
    assert r.status_code == 409 and r.json()["code"] == "plan_status_past_niet", r.text

    # Verwijderen blijft alleen de containers: datasets en snapshots staan er daarna nog.
    datasets, snapshots = sorted(nas.datasets()), copy.deepcopy(nas.data["snapshots"])
    u = stel_voor(admin, "app.uninstall", app_target("demo-app")).json()
    assert keur_goed(admin, u).status_code == 200
    assert voer_uit(admin, u).status_code == 200
    assert sorted(nas.datasets()) == datasets and nas.data["snapshots"] == snapshots
    assert "pool.dataset.delete" not in nas.mutations


def test_eigen_binding_via_de_gewone_actieweg_wordt_geweigerd(keten: Keten) -> None:
    from policyhelpers import catalog_binding

    params = install_params("demo-app")
    params["catalog_binding"] = catalog_binding(REGEL)
    r = stel_voor(keten.stack.admin, "app.install", app_target("demo-app"), params)
    assert r.status_code == 422 and r.json()["code"] == "catalog_binding_alleen_via_plan", r.text
    assert keten.planner.plans == {}


def test_kijker_maakt_geen_plan_en_een_vreemd_plan_bestaat_niet(keten: Keten, app: Any) -> None:
    admin = keten.stack.admin
    make_user(admin, "kijker", "viewer")
    assert _plan(login_as(app, "kijker")).status_code == 403
    r = admin.post(
        f"/api/v1/catalog/plans/{uuid.uuid4()}/steps/installeren/propose",
        headers=idem(),
    )
    assert r.status_code == 404 and keten.planner.plans == {}


@pytest.mark.parametrize(
    ("wijzig", "code"),
    [
        (lambda k: k.store.routes[f"/catalog/v1/versions/{VERSION_ID}"]["provenance"].update(signature="A" * 88),
         "bewijs_ongeldig"),
        (lambda k: k.store.routes[f"/catalog/v1/versions/{VERSION_ID}"].update(manifest={**MANIFEST, "name": "X"}),
         "bewijs_ongeldig"),
        (lambda k: k.store.routes[f"/catalog/v1/sources/{SOURCE_ID}"].update(pinned_commit="d" * 40),
         "bewijs_ongeldig"),
        (lambda k: k.store.routes[f"/catalog/v1/sources/{SOURCE_ID}"].update(require_signature=False),
         "bewijs_ongeldig"),
        (lambda k: k.store.routes.update({f"/catalog/v1/versions/{VERSION_ID}": 404}), "version_unavailable"),
    ],
    ids=["handtekening", "manifest", "commit", "zonder_ondertekening", "versie_weg"],
)  # fmt: skip
def test_afwijkend_bewijs_geeft_geen_plan(keten: Keten, wijzig: Any, code: str) -> None:
    wijzig(keten)
    r = _plan(keten.stack.admin)
    assert r.status_code == 409 and r.json()["code"] == code, r.text
    assert keten.planner.plans == {} and schrijfaanroepen(keten.stack.nas) == []


def test_naam_al_op_de_nas_geeft_geen_plan(keten: Keten) -> None:
    r = _plan(keten.stack.admin, app_name="my-house")
    assert r.status_code == 409 and r.json()["code"] == "naam_bezet", r.text


def test_gewijzigd_plan_of_bewijs_blokkeert_voorstel_en_uitvoering(
    keten: Keten,
) -> None:
    admin, nas = keten.stack.admin, keten.stack.nas
    plan = _plan(admin).json()
    # Andere ETag bij de planner: geen voorstel.
    keten.planner.plans[plan["plan_id"]]["etag"] = '"plan-anders"'
    r = _stel_voor(admin, plan)
    assert r.status_code == 409 and r.json()["code"] == "plan_bewijs_gewijzigd", r.text
    keten.planner.plans[plan["plan_id"]]["etag"] = plan["plan_etag"]
    v = _stel_voor(admin, plan).json()
    assert keur_goed(admin, v).status_code == 200
    # Na de goedkeuring verdwijnt de versie bij de appstore: niets naar de executor.
    keten.store.routes[f"/catalog/v1/versions/{VERSION_ID}"] = 404
    r = voer_uit(admin, v)
    assert r.status_code == 409 and r.json()["code"] == "version_unavailable", r.text
    assert schrijfaanroepen(nas) == [] and haal(admin, v)["status"] == "goedgekeurd"


def test_verlopen_plan_geeft_geen_voorstel(keten: Keten) -> None:
    from datetime import timedelta

    keten.planner.ttl = timedelta(seconds=-1)
    plan = _plan(keten.stack.admin).json()
    r = _stel_voor(keten.stack.admin, plan)
    assert r.status_code == 409 and r.json()["code"] == "plan_vervallen", r.text


# ------------------------------------------------------------------ herstel na R-VEILIG (S-P2-050d)
def _geweigerd(functie: Any) -> tuple[int, str]:
    from hub.errors import HubError

    try:
        functie()
    except HubError as fout:
        return fout.status, fout.code
    return 200, "aanvaard"


def test_bron_id_en_uitgeverssleutel_moeten_overal_gelijk_zijn(keten: Keten, app: Any) -> None:
    """R-VEILIG-3: item, versie, record en actieve bron noemen dezelfde bron en dezelfde uitgeverssleutel."""
    from hub.catalog import plannen

    entry = keten.store.routes["/catalog/v1/entries/demo-app"]
    bron = keten.store.routes[f"/catalog/v1/sources/{SOURCE_ID}"]
    with app.state.sessionmaker() as db:

        def toets() -> Any:
            return plannen.bewijs(
                db,
                app.state.settings,
                app.state.keyring(),
                app_id="demo-app",
                version_id=VERSION_ID,
            )

        assert _geweigerd(toets)[0] == 200
        entry["source"]["id"] = str(uuid.uuid4())
        assert _geweigerd(toets) == (409, "bewijs_ongeldig")
        entry["source"]["id"] = SOURCE_ID
        bron["trusted_key_id"] = "0" * 16
        assert _geweigerd(toets) == (409, "bewijs_ongeldig")
        del bron["trusted_key_id"]
        assert _geweigerd(toets) == (409, "bewijs_ongeldig")


def test_niet_gedeclareerde_of_geheime_parameter_bereikt_de_planner_niet(
    keten: Keten,
) -> None:
    """R-VEILIG-2: alleen gedeclareerde, niet-geheime wizardparameters gaan mee; anders nul planneraanroepen."""
    marker = "niet-geheime-testmarkering-" + uuid.uuid4().hex
    for parameters in (
        {"password": marker},
        {"admin_wachtwoord": marker},
        {"public_url": {"x": marker}},
    ):
        r = _plan(keten.stack.admin, parameters=parameters)
        assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
        assert marker not in r.text
    assert keten.planner.requests == [] and keten.planner.plans == {}
    assert _plan(keten.stack.admin).status_code == 201


@pytest.mark.parametrize("weg", ["data_path", "public_url"])
def test_ontbrekende_verplichte_parameter_bereikt_de_planner_niet(keten: Keten, weg: str) -> None:
    """R-VEILIG-2: de vertaling van de gepinde validator meldt parameter_value_missing; de Hub plant dan niets."""
    parameters = {k: v for k, v in VOLLEDIG.items() if k != weg}
    r = _plan(keten.stack.admin, parameters=parameters)
    assert r.status_code == 422 and r.json()["details"]["codes"] == ["parameter_value_missing"], r.text
    assert keten.planner.requests == [] and not schrijfaanroepen(keten.stack.nas)


def test_andere_validatorversie_dan_de_pin_bereikt_de_planner_niet(
    keten: Keten, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R-VEILIG-2: regel en record noemen een andere validatorversie dan de gepinde validator rapporteert."""
    import hub.catalog.asf.manifest.validator as validator

    monkeypatch.setattr(validator, "__version__", "9.9.9")
    r = _plan(keten.stack.admin)
    assert r.status_code == 409 and r.json()["details"] == {"reden": "manifest_schema"}, r.text
    assert keten.planner.requests == [] and not schrijfaanroepen(keten.stack.nas)


@pytest.mark.parametrize("waarde", ["voorbeeldmap", "/mnt/testpool/../etc", "/etc/demo"])
def test_ongeldige_padwaarde_bereikt_de_planner_niet(keten: Keten, waarde: str) -> None:
    """R-VEILIG-2: de parametercontrole van de gepinde validator weigert een ongeldig pad vóór de planner."""
    r = _plan(keten.stack.admin, parameters={"data_path": waarde})
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert keten.planner.requests == [] and not schrijfaanroepen(keten.stack.nas)


def test_bewaarde_oude_antwoordvorm_lekt_niet_bij_lezen_of_herhalen(keten: Keten, app: Any) -> None:
    """R-VEILIG-1: een plan of cacheantwoord van vóór het herstel met een extra controleveld toont dat veld niet."""
    import json

    import sqlalchemy as sa

    from hub.models import CatalogPlan, IdempotencyRecord

    admin = keten.stack.admin
    gemaakt = _plan(admin)
    assert gemaakt.status_code == 201
    plan_id = uuid.UUID(gemaakt.json()["plan_id"])
    sleutel = gemaakt.request.headers["Idempotency-Key"]
    with app.state.sessionmaker.begin() as db:
        rij = db.get(CatalogPlan, plan_id)
        oud = [dict(rij.controles_na_installatie[0], oude_notitie="voorbeeldnotitie")]
        rij.controles_na_installatie = oud
        cache = db.scalars(sa.select(IdempotencyRecord).where(IdempotencyRecord.key == uuid.UUID(sleutel))).one()
        cache.response_body = dict(cache.response_body, controles_na_installatie=oud)
    make_user(admin, "lezer-oud", "viewer")
    with login_as(app, "lezer-oud") as lezer:
        gelezen = lezer.get(f"/api/v1/catalog/plans/{plan_id}")
    herhaald = admin.post(
        gemaakt.request.url.path, json=json.loads(gemaakt.request.content), headers={"Idempotency-Key": sleutel}
    )
    assert gelezen.status_code == 200 and herhaald.headers.get("Idempotent-Replay") == "true"
    for antwoord in (gelezen.json(), herhaald.json()):
        assert [set(c) for c in antwoord["controles_na_installatie"]] == [{"id", "soort", "beschrijving_nl"}]
    with app.state.sessionmaker() as db:
        cache = db.scalars(sa.select(IdempotencyRecord).where(IdempotencyRecord.key == uuid.UUID(sleutel))).one()
        assert "oude_notitie" not in json.dumps(cache.response_body)  # de herhaling schoont het cacheantwoord op


def test_plannercontroles_alleen_openbare_velden(keten: Keten, app: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """R-VEILIG-1: een extra veld in een plannercontrole komt niet in opslag, antwoord of kijkerweergave."""
    import sqlalchemy as sa

    marker = "niet-geheime-testmarkering-" + uuid.uuid4().hex
    origineel = keten.planner.handle

    def antwoord(verzoek: Any) -> Any:
        resultaat = origineel(verzoek)
        if resultaat.status == 201:
            resultaat.body["plan"]["controles_na_installatie"][0]["token"] = marker
        return resultaat

    admin = keten.stack.admin
    make_user(admin, "lezer", "viewer")
    monkeypatch.setattr(keten.planner, "handle", antwoord)
    r = _plan(admin)
    assert r.status_code == 409 and r.json()["code"] == "plan_controles_verschillen" and marker not in r.text, r.text
    monkeypatch.setattr(keten.planner, "handle", origineel)
    plan = _plan(admin).json()
    lezer = login_as(app, "lezer")
    try:
        gelezen = lezer.get(f"/api/v1/catalog/plans/{plan['plan_id']}").json()
    finally:
        lezer.close()
    assert gelezen["controles_na_installatie"] == [
        {
            "id": "http_bereikbaar",
            "soort": "http",
            "beschrijving_nl": "De webinterface antwoordt.",
        }
    ]
    with app.state.sessionmaker() as db:
        for tabel in ("catalog_plan", "idempotency_record", "audit_event", "log_entry"):
            # Vaste tabelnamen; de zoekwaarde gaat als gebonden parameter mee.
            sql = f"SELECT EXISTS (SELECT 1 FROM {tabel} r WHERE strpos(to_jsonb(r)::text, :m) > 0)"  # noqa: S608
            q = sa.text(sql)
            assert db.execute(q, {"m": marker}).scalar_one() is False, tabel


@pytest.mark.parametrize("grens", ["stapinhoud", "handmatige_voorganger", "planstatus", "vervaldatum"])
def test_hercontrole_ziet_wijziging_bij_gelijke_etag(keten: Keten, app: Any, grens: str) -> None:
    """R-VEILIG-5 en -6: stapinhoud, vervaltijd, planstatus en voorgangers zelf vergelijken, niet alleen de ETag."""
    from datetime import timedelta

    from hub.catalog import plannen
    from hub.models import ActionRequest
    from hub.timeutil import utcnow

    admin = keten.stack.admin
    plan = _plan(admin).json()
    voorstel = _stel_voor(admin, plan).json()
    view = keten.planner.plans[plan["plan_id"]]
    stap = view["plan"]["stappen"][0]
    with app.state.sessionmaker() as db:
        req = db.get(ActionRequest, uuid.UUID(voorstel["request_id"]))

        def toets() -> Any:
            return plannen.hercontroleer(db, app.state.settings, app.state.keyring(), req)

        assert _geweigerd(toets)[0] == 200
        if grens == "stapinhoud":
            stap["voorstel"]["parameters"]["app_create"]["values"]["TZ"] = "Europe/Amsterdam"
        elif grens == "handmatige_voorganger":
            stap["hangt_af_van"] = ["bevestiging"]
            view["plan"]["stappen"].insert(0, {"id": "bevestiging", "soort": "handmatig", "voorstel": None})
        elif grens == "planstatus":
            view["status"] = "geblokkeerd"
        else:
            view["expires_at"] = (utcnow() - timedelta(minutes=1)).isoformat()
        assert _geweigerd(toets) == (409, "plan_bewijs_gewijzigd")
    assert schrijfaanroepen(keten.stack.nas) == []


def test_plan_met_onbevestigde_voorganger_blijft_dicht(keten: Keten, monkeypatch: pytest.MonkeyPatch) -> None:
    """R-VEILIG-6: een handmatige voorganger zonder eigen bevestiging in de Hub geeft geen voorstel."""
    origineel = keten.planner.handle

    def antwoord(verzoek: Any) -> Any:
        resultaat = origineel(verzoek)
        if resultaat.status == 201:
            stappen = resultaat.body["plan"]["stappen"]
            stappen[0]["hangt_af_van"] = ["bevestiging"]
            stappen.insert(0, {"id": "bevestiging", "soort": "handmatig", "voorstel": None})
        return resultaat

    monkeypatch.setattr(keten.planner, "handle", antwoord)
    plan = _plan(keten.stack.admin).json()
    assert plan["status"] == "geblokkeerd" and plan["reden"] == "voorganger_onbevestigd"
    r = _stel_voor(keten.stack.admin, plan)
    assert r.status_code == 409 and r.json()["code"] == "plan_status_past_niet", r.text
