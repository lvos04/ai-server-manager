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
from actiehelpers import Stack, app_target, bouw_stack, haal, keur_goed, schrijfaanroepen, stel_voor, voer_uit
from asm_policy.canonical import canonical_json, canonical_sha256
from conftest import enroll_body, idem, login_as, make_user, service_jwk
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from executorhelpers import write_nas
from fakes.fake_appstore import FakeAppstore
from fakes.fake_planner import FakePlanner
from fakes.fake_truenas import FakeTrueNAS
from policyhelpers import DIGEST, catalogus_regel, install_params, policy_met_regels, provenance_record

pytestmark = [pytest.mark.e2e, pytest.mark.integration]
APPSTORE_SEED = b"\x11" * 32
MANIFEST: dict[str, Any] = {"schema_version": 1, "app_id": "demo-app", "version": "1.2.3", "name": "Demo"}
REGEL = catalogus_regel(manifest_sha256=canonical_sha256(MANIFEST))
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
    r = admin.post("/api/v1/services/enroll", json=enroll_body(app_id, token=r.json()["enrollment_token"], jwk=jwk))
    assert r.status_code == 200, r.text
    return str(r.json()["service_id"])


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def keten(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Keten]:
    from hub.actions import beleid

    monkeypatch.setenv("ASM_POLICY_DIR", str(policy_met_regels(tmp_path / "policy", [REGEL])))
    beleid._geladen.cache_clear()
    stack = bouw_stack(
        admin=admin, app=app, nas=nas, worker_once=worker_once, tmp_path=tmp_path, monkeypatch=monkeypatch
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
        "/catalog/v1/entries/demo-app": {"entry_id": ENTRY_ID, "app_id": "demo-app"},
        f"/catalog/v1/sources/{SOURCE_ID}": {
            "id": SOURCE_ID,
            "kind": "git",
            "enabled": True,
            "require_signature": True,
            "url": REGEL["source"]["url"],
            "subpath": REGEL["source"]["subpath"],
            "pinned_commit": REGEL["source"]["commit"],
        },
    }
    planner = FakePlanner(hub_key, install_params("demo-app")).start()
    urls = {"appstore-en-fork": store.url, "jelly-leon-platform": planner.url}
    # In productie komen de adressen uit de inventaris (app.query + D03); hier zijn het de testservers.
    monkeypatch.setattr("hub.catalog.plannen.service_base_url", lambda db, s, svc: (urls[svc.app_id], None))
    yield Keten(stack, store, planner)
    store.stop()
    planner.stop()
    stack.stop()
    beleid._geladen.cache_clear()


def _plan(admin: Any, **wijzig: Any) -> Any:
    body: dict[str, Any] = {
        "app_id": "demo-app",
        "version_id": VERSION_ID,
        "app_name": "demo-app",
        "parameters": {},
        "doel": {"truenas_version": "25.04.2", "ix_app_version": "1.4.8"},
    }
    body.update(wijzig)
    return admin.post("/api/v1/catalog/plans/install", json=body, headers=idem())


def _stel_voor(admin: Any, plan: dict[str, Any]) -> Any:
    return admin.post(f"/api/v1/catalog/plans/{plan['plan_id']}/steps/{plan['step_id']}/propose", headers=idem())


def test_installeren_via_eigen_plan_met_readback_en_registratie(keten: Keten) -> None:
    admin, nas = keten.stack.admin, keten.stack.nas
    r = _plan(admin)
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["status"] == "klaar_voor_voorstel" and plan["step_id"] == "installeren"
    assert keten.planner.rejected == [] and keten.store.rejected == []
    gestuurd = keten.planner.plans[plan["plan_id"]]["catalog_binding"]
    assert set(gestuurd) == {"appstore_service_id", "source_approval_revision", "provenance", "release", "instance"}
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
    r = admin.post(f"/api/v1/catalog/plans/{uuid.uuid4()}/steps/installeren/propose", headers=idem())
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


def test_gewijzigd_plan_of_bewijs_blokkeert_voorstel_en_uitvoering(keten: Keten) -> None:
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
