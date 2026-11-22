"""Volledige keten (S-P2-050g; ADR-0032 deel G; contract 1.3 §8.1/§8.2): appstore -> planner -> Hub -> executor ->
nagebootste TrueNAS en terug.

Echt zijn: de gepinde broncode van ``appstore-en-fork`` (catalogus, bron, ondertekend herkomstrecord) en van
``jelly-leon-platform`` (planner, ``catalog_binding``), elk met een eigen PostgreSQL-database, eigen geheimen en een
eigen koppeling met deze Hub via een enrollment-token; en de Hub en de executor van deze repo. Nagebootst zijn alleen
de TrueNAS (``fakes.fake_truenas``) en de Git-forge achter de https-bron-URL (een lokale repo, zie ``_forge``).
Sim-getest; NIET GEVALIDEERD (echte NAS). Alleen testwaarden, nooit een echte NAS of een echt account.

``ASF_SOURCE`` en ``JLP_SOURCE`` wijzen naar een checkout van de twee repo's; de pins hieronder bepalen de code.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import os
import subprocess
import sys
import tarfile
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml
from actiehelpers import (
    Served,
    Stack,
    app_target,
    bouw_stack,
    haal,
    keur_goed,
    schrijfaanroepen,
    stel_voor,
    voer_uit,
)
from conftest import ADMIN_URL, idem, login_as, make_user
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from executorhelpers import write_nas
from fakes.fake_truenas import FakeTrueNAS
from policyhelpers import DIGEST, DIGEST_B, policy_met_regels

APPSTORE_PIN = "936b2da5723dfea0cb43f4813c37398cc3df1ed4"  # appstore-en-fork: §8.1-bewijs (14b1c10) en later
PLANNER_PIN = "9d59e16c9e078ca2982d4b523e21360de757eb7a"  # jelly-leon-platform: §8.2 catalog_binding (9bc9976)
FORGE_URL = "https://forge.test/leon/demo-catalogus"  # alleen de Git-forge is nagebootst
REPO = "ghcr.io/voorbeeld/demo-app"
pytestmark = [pytest.mark.e2e, pytest.mark.integration]

# Een volgens de gepinde validator geldig testmanifest (fictieve app, testdigest), zoals in de catalogusinstallatie.
MANIFEST: dict[str, Any] = {
    "manifest_version": "1",
    "app_id": "demo-app",
    "name": "Demo",
    "owner_repo": "voorbeeld/demo-app",
    "category": "other",
    "description_nl": "Fictieve app voor de volledige ketentest van S-P2-050g.",
    "version": "1.2.3",
    "install": {"method": "custom_app"},
    "image": {"repository": REPO, "tag": "1.2.3", "digest": DIGEST},
    "custom_app": {
        "storage": [{"name": "data", "type": "host_path", "host_path": {"param": "data_path"}}],
        "env": [{"name": "APP_MODE", "value": "prod"}],
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
    "compatibility": {
        "truenas_min_version": "24.10.2",
        "truenas_max_version": None,
        "ix_app_min_version": None,
    },
    "upgrade": {"migrations": False, "tag_only_rollback_safe": True},
    "decisions_required": ["D02"],
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
DATA = "/mnt/testpool/apps/demo-app"
PARAMETERS = {"data_path": DATA}
DOEL = {"truenas_version": "25.04.2", "ix_app_version": "1.4.8"}


# ------------------------------------------------------------------ gepinde broncode van appstore en planner
def _archief(bron_env: str, pin: str, paden: list[str], doel: Path) -> None:
    bron = Path(os.environ[bron_env]).resolve()
    doel.mkdir(parents=True)
    tar = doel / "bron.tar"
    subprocess.run(["git", "-C", str(bron), "archive", "-o", str(tar), pin, *paden], check=True)
    with tarfile.open(tar) as f:
        f.extractall(doel, filter="data")
    tar.unlink()


@pytest.fixture(scope="session")
def gepinde_bronnen(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """``appstore`` (volledig) en ``lifecycle`` op hun pin. De planner gebruikt zo de manifeststandaard van de
    appstore-pin; zijn eigen kopie (``src/appstore``) wordt niet geladen (alleen ``provenance.py`` verschilt,
    additief)."""
    werk = tmp_path_factory.mktemp("gepinde-bronnen")
    _archief("ASF_SOURCE", APPSTORE_PIN, ["apps/api/src/appstore", "apps/api/alembic", "apps/api/alembic.ini"],
             werk / "asf")  # fmt: skip
    _archief("JLP_SOURCE", PLANNER_PIN, ["apps/api/src/lifecycle"], werk / "jlp")
    for pad in (werk / "jlp/apps/api/src", werk / "asf/apps/api/src"):
        sys.path.insert(0, str(pad))
    for naam in [m for m in sys.modules if m == "appstore" or m.startswith(("appstore.", "lifecycle"))]:
        del sys.modules[naam]
    import appstore
    import lifecycle

    for mod, wortel in ((appstore, werk / "asf"), (lifecycle, werk / "jlp")):
        assert Path(mod.__file__ or "").resolve().is_relative_to(wortel), mod
    return werk


@contextlib.contextmanager
def _database(prefix: str) -> Iterator[str]:
    import psycopg

    naam = f"asm_keten_{prefix}_{uuid.uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(f'CREATE DATABASE "{naam}"')
    try:
        yield (ADMIN_URL.rsplit("/", 1)[0].replace("postgresql://", "postgresql+psycopg://", 1) + "/" + naam)
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{naam}" WITH (FORCE)')


def _forge(repo_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """De Git-forge nagebootst: de echte ``fetch_git`` van de appstore kloont ``FORGE_URL`` uit de lokale repo."""
    from dulwich import porcelain

    echt = porcelain.clone

    def clone(source: Any, target: Any, *a: Any, **kw: Any) -> Any:
        assert source == FORGE_URL, source
        return echt(str(repo_dir), target, *a, **kw)

    monkeypatch.setattr(porcelain, "clone", clone)
    # Naamopzoeking van de forge: een documentatieadres (RFC 5737), zodat de echte adrescontrole gewoon draait.
    import socket

    from appstore.catalog import sources

    echt_dns = socket.getaddrinfo

    def dns(host: str, *a: Any, **kw: Any) -> Any:
        if host == "forge.test":
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", 443))]
        return echt_dns(host, *a, **kw)

    monkeypatch.setattr(sources.socket, "getaddrinfo", dns)


def _git_repo(path: Path, files: dict[str, str]) -> str:
    from dulwich import porcelain

    repo = porcelain.open_repo(str(path)) if (path / ".git").exists() else porcelain.init(str(path))
    for name, content in files.items():
        (path / name).parent.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(content)
        porcelain.add(repo, [str(path / name)])
    sha = porcelain.commit(repo, message=b"catalogus", author=b"Test <t@test>", committer=b"Test <t@test>")
    repo.close()
    return str(sha.decode())


def _token(admin: Any, app_id: str) -> dict[str, Any]:
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": app_id})
    assert r.status_code == 201, r.text
    return dict(r.json())


# ------------------------------------------------------------------ de keten
@dataclass
class Keten:
    stack: Stack
    store: Any  # AppContext van de echte appstore
    planner_db: str
    regel: dict[str, Any]
    version_id: str
    entry_id: str
    hub_url: str

    @property
    def admin(self) -> Any:
        return self.stack.admin

    @property
    def nas(self) -> FakeTrueNAS:
        return self.stack.nas

    def plannen_bij_planner(self) -> list[dict[str, Any]]:
        """De plannen zoals de echte planner ze in zijn eigen database bewaart."""
        import sqlalchemy as sa

        eng = sa.create_engine(self.planner_db)
        try:
            with eng.connect() as conn:
                rijen = conn.execute(sa.text("SELECT id, document, stappen FROM lifecycle_plans")).all()
        finally:
            eng.dispose()
        return [{"id": str(r[0]), "document": r[1], "stappen": r[2]} for r in rijen]


def _formuliervelden(manifest: dict[str, Any]) -> list[str]:
    """Het veldschema van deze versie: de velden die de gepinde vertaling onder ``values`` zet (beheerderskeuze)."""
    from hub.catalog.asf.manifest.translate import Target, translate
    from hub.catalog.asf.manifest.validator import validate_data

    _r, model = validate_data(copy.deepcopy(manifest))
    assert model is not None
    uit = translate(
        model,
        dict(PARAMETERS),
        Target.model_validate(DOEL),
        "demo-app",
        trusted_app_id=True,
    )
    assert uit.payload is not None, [f.code for f in uit.blocking()]
    return sorted(uit.payload.model_dump(mode="json", exclude_none=True)["values"])


@contextlib.contextmanager
def maak_keten(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    bronnen: Path,
) -> Iterator[Keten]:  # fmt: skip
    from appstore import migrations as asf_migrations
    from appstore.app import create_app as asf_app
    from appstore.config import Settings as AsfSettings
    from appstore.manifest.canonical import sha256_digest
    from appstore.manifest.provenance import b64url, raw_public, sign_data
    from appstore.worker import build_context, run_once, startup
    from lifecycle.app import create_app as jlp_app
    from lifecycle.app import default_http_client_factory
    from lifecycle.config import Settings as JlpSettings
    from lifecycle.migrations_util import upgrade as jlp_upgrade
    from lifecycle.secrets_store import ensure_secrets
    from lifecycle.worker import Worker

    from hub.actions import beleid

    servers: list[Served] = []
    with contextlib.ExitStack() as opruimen:
        # 1. De Hub als HTTP-server voor de koppeling van appstore en planner.
        hub = Served(app)
        servers.append(hub)
        opruimen.callback(lambda: [s.stop() for s in servers])
        # 2. De echte appstore: eigen database, eigen identiteit, koppelen met het enrollment-token.
        asf_db = opruimen.enter_context(_database("appstore"))
        asf_migrations.upgrade(asf_db)
        leeg = tmp_path / "ingebouwd"
        leeg.mkdir()
        grant = _token(admin, "appstore-en-fork")
        asf_settings = AsfSettings(
            data_dir=tmp_path / "appstore", database_url=asf_db, host="127.0.0.1", port=0, hub_url=hub.url,
            enrollment_token=grant["enrollment_token"], public_url=None, bundled_catalog_dir=leeg,
            allow_insecure_sources=False, hub_key_fingerprint=grant["keyset_fingerprint"], allow_loopback_hub=True,
        )  # fmt: skip
        store = build_context(asf_settings)
        opruimen.callback(store.engine.dispose)
        startup(store)
        run_once(store)
        assert store.store.read().linked, "appstore niet gekoppeld"
        # 3. De uitgever tekent het manifest; de bron is gepinde Git met verplichte ondertekening.
        uitgever = Ed25519PrivateKey.generate()
        tekst = yaml.safe_dump(MANIFEST, sort_keys=False, allow_unicode=True)
        repo_dir = tmp_path / "forge"
        repo_dir.mkdir()
        commit = _git_repo(
            repo_dir,
            {
                "apps/demo-app.manifest.yaml": tekst,
                "apps/demo-app.manifest.yaml.sig": sign_data(uitgever, MANIFEST),
            },
        )
        _forge(repo_dir, monkeypatch)
        asf_srv = Served(asf_app(asf_settings))
        servers.append(asf_srv)
        sleutel = app.state.keyring()

        def als_beheerder() -> dict[str, str]:
            jwt_, _ = sleutel.issue_user_jwt(subject="beheer", audience="appstore-en-fork", roles=["admin"],
                                             ttl_seconds=60)  # fmt: skip
            return {"Authorization": f"Bearer {jwt_}", **idem()}

        import httpx

        with httpx.Client(base_url=asf_srv.url, trust_env=False, timeout=15) as c:
            r = c.post("/catalog/v1/sources", headers=als_beheerder(), json={
                "name": "demo-bron", "kind": "git", "url": FORGE_URL, "subpath": "apps", "pinned_commit": commit,
                "require_signature": True, "trusted_public_key": b64url(raw_public(uitgever.public_key())),
            })  # fmt: skip
            assert r.status_code == 201, r.text
            bron_id = r.json()["id"]
            r = c.post(f"/catalog/v1/sources/{bron_id}/sync", headers=als_beheerder())
            assert r.status_code == 202, r.text
            run_once(store)
            jwt_, _ = sleutel.issue_user_jwt(subject="beheer", audience="appstore-en-fork", roles=["admin"],
                                             ttl_seconds=60)  # fmt: skip
            entry = c.get(
                "/catalog/v1/entries/demo-app",
                headers={"Authorization": f"Bearer {jwt_}"},
            )
            assert entry.status_code == 200, entry.text
        version_id = entry.json()["latest_version"]["id"]
        # 4. De echte planner: eigen database en geheimen, koppelen via zijn eigen worker.
        jlp_db = opruimen.enter_context(_database("planner"))
        jlp_upgrade(jlp_db)
        ensure_secrets(tmp_path / "planner" / "secrets")
        grant = _token(admin, "jelly-leon-platform")
        jlp_settings = JlpSettings(
            data_dir=tmp_path / "planner", database_url=jlp_db, hub_url=hub.url,
            enrollment_token=grant["enrollment_token"], hub_key_fingerprint=grant["keyset_fingerprint"],
            allow_loopback_hub=True,
        )  # fmt: skip
        worker = Worker(jlp_settings, http_client_factory=default_http_client_factory(jlp_settings))
        opruimen.callback(worker.engine.dispose)
        assert worker.tick()["enrollment"] == "gekoppeld"
        jlp_srv = Served(jlp_app(jlp_settings))
        servers.append(jlp_srv)
        # 5. De beheerder laat precies deze bron, uitgever en versie toe (witte lijst onder de policy_hash).
        record = _record(c_url=asf_srv.url, sleutel=sleutel, version_id=version_id)
        sleutel_raw = uitgever.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        regel = {
            "app_id": "demo-app",
            "version": "1.2.3",
            "catalog": {"train": "stable", "app": "ix-app", "version": "1.4.8"},
            "manifest_sha256": sha256_digest(MANIFEST),
            "image_digests": [DIGEST],
            "schema_sha256": record["schema_sha256"],
            "validator_version": record["validator_version"],
            "source": {
                "source_id": bron_id,
                "url": FORGE_URL,
                "subpath": "apps",
                "path": "demo-app.manifest.yaml",
                "commit": commit,
            },
            "publisher_key_sha256": "sha256:" + hashlib.sha256(sleutel_raw).hexdigest(),
            "formuliervelden": _formuliervelden(MANIFEST),
            "kluisplekken": [],
        }
        monkeypatch.setenv("ASM_POLICY_DIR", str(policy_met_regels(tmp_path / "policy", [regel])))
        beleid._geladen.cache_clear()
        opruimen.callback(beleid._geladen.cache_clear)
        # 6. De echte executor (met dit beleid) en de fake TrueNAS.
        stack = bouw_stack(admin=admin, app=app, nas=nas, worker_once=worker_once, tmp_path=tmp_path,
                           monkeypatch=monkeypatch)  # fmt: skip
        opruimen.callback(stack.stop)
        urls = {"appstore-en-fork": asf_srv.url, "jelly-leon-platform": jlp_srv.url}
        # In productie komen de adressen uit de inventaris (app.query + D03); hier zijn het de testservers.
        monkeypatch.setattr(
            "hub.catalog.plannen.service_base_url",
            lambda db, s, svc: (urls[svc.app_id], None),
        )
        # Catalogusbeschikbaarheid meten (§4.4) voor de planner; vijf minuten terug, zodat een test meteen opnieuw
        # kan meten.
        from datetime import timedelta

        from hub.catalog import availability

        eerder = availability.utcnow() - timedelta(seconds=310)
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(availability, "utcnow", lambda: eerder)
            worker_once(schedule=True)
        yield Keten(stack, store, jlp_db, regel, version_id, entry.json()["entry_id"], hub.url)


def _record(*, c_url: str, sleutel: Any, version_id: str) -> dict[str, Any]:
    import httpx

    jwt_, _ = sleutel.issue_user_jwt(subject="beheer", audience="appstore-en-fork", roles=["admin"], ttl_seconds=60)
    with httpx.Client(base_url=c_url, trust_env=False, timeout=15) as c:
        r = c.get(
            f"/catalog/v1/versions/{version_id}",
            headers={"Authorization": f"Bearer {jwt_}"},
        )
    assert r.status_code == 200, r.text
    return dict(r.json()["provenance"]["record"])


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


@pytest.fixture
def keten(
    admin: Any, app: Any, nas: FakeTrueNAS, worker_once: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    gepinde_bronnen: Path,
) -> Iterator[Keten]:  # fmt: skip
    with maak_keten(admin, app, nas, worker_once, tmp_path, monkeypatch, gepinde_bronnen) as k:
        yield k


def _plan(k: Keten, **wijzig: Any) -> Any:
    body: dict[str, Any] = {
        "app_id": "demo-app",
        "version_id": k.version_id,
        "app_name": "demo-app",
        "parameters": dict(PARAMETERS),
        "doel": {**DOEL, "truenas_version": k.nas.version},
    }
    body.update(wijzig)
    return k.admin.post("/api/v1/catalog/plans/install", json=body, headers=idem())


def _stel_voor(k: Keten, plan: dict[str, Any]) -> Any:
    return k.admin.post(
        f"/api/v1/catalog/plans/{plan['plan_id']}/steps/{plan['step_id']}/propose",
        headers=idem(),
    )


def _codes(voorstel: dict[str, Any]) -> list[str]:
    return [b["code"] for b in voorstel["blokkades"]]


def _geblokkeerd(r: Any, code: str) -> None:
    assert r.status_code == 409 and r.json()["code"] == "actie_geblokkeerd", r.text
    assert code in [b["code"] for b in r.json()["details"]["blokkades"]], r.text


def _snapshot(k: Keten, dataset: str, naam: str) -> dict[str, Any]:
    """Een checkpoint via de productieroute: ``zfs.snapshot.create`` (R1) door de Hub en de echte executor."""
    v = stel_voor(k.admin, "zfs.snapshot.create", {"host_id": "nas-primary", "dataset": dataset},
                  {"naam": naam, "recursief": True})  # fmt: skip
    assert v.status_code == 201 and v.json()["blokkades"] == [], v.text
    r = voer_uit(k.admin, v.json())
    assert r.status_code == 200 and r.json()["resultaat"]["waarschuwingen"] == [], r.text
    return dict(v.json())


def _installeer(k: Keten) -> dict[str, Any]:
    """De hele installatieketen: eigen plan bij de echte planner, voorstel, goedkeuring, uitvoering, terugmelding."""
    apps = k.nas.datasets()["testpool/apps"]
    apps["children"].append({**apps["children"][0], "id": "testpool/apps/demo-app", "name": "testpool/apps/demo-app",
                             "mountpoint": DATA, "children": []})  # fmt: skip
    r = _plan(k)
    assert r.status_code == 201, r.text
    plan = r.json()
    assert plan["status"] == "klaar_voor_voorstel" and plan["step_id"] == "installeren", plan
    v = _stel_voor(k, plan)
    assert v.status_code == 201, v.text
    v = v.json()
    assert v["risk_class"] == "R2" and v["status"] == "wacht_op_goedkeuring" and v["blokkades"] == [], v
    assert keur_goed(k.admin, v).status_code == 200
    r = voer_uit(k.admin, v)
    assert r.status_code == 200 and r.json()["status"] == "uitgevoerd", r.text
    k.stack.vernieuw()
    return {"plan": plan, "voorstel": v}


NIEUW = {"image": {"repository": REPO, "tag": f"1.2.4@{DIGEST_B}"}}


# ------------------------------------------------------------------ T3/T9: de positieve keten
def test_t3_t9_installeren_bijwerken_terugzetten_en_verwijderen_via_de_echte_keten(
    keten: Keten,
) -> None:
    k, admin, nas = keten, keten.admin, keten.nas
    # Installeren: de echte planner bewaart precies de vijf bindingsvelden van de Hub en krijgt de terugmelding.
    stap = _installeer(k)
    plan, v = stap["plan"], stap["voorstel"]
    assert schrijfaanroepen(nas) == ["app.create"] and len(nas.created) == 1
    waarden = nas.created[0]["values"]
    assert waarden["image"]["tag"] == f"1.2.3@{DIGEST}" and waarden["storage"][0]["host_path_config"]["path"] == DATA
    assert waarden["host_network"] is False and waarden["privileged"] is False
    nu = admin.get(f"/api/v1/catalog/plans/{plan['plan_id']}").json()
    assert nu["status"] == "geinstalleerd_controles_open" and nu["melding"]["status"] == "gemeld", nu
    assert nu["registratie"]["digests"] == [f"{REPO}@{DIGEST}"]
    [bij_planner] = k.plannen_bij_planner()
    assert bij_planner["id"] == plan["plan_id"]
    binding = bij_planner["document"]["catalog_binding"]
    assert set(binding) == {
        "appstore_service_id",
        "source_approval_revision",
        "provenance",
        "release",
        "instance",
    }
    assert binding["release"]["image_digests"] == [DIGEST]
    assert binding["provenance"]["record"]["manifest_sha256"] == k.regel["manifest_sha256"]
    assert binding["provenance"]["record"]["source"]["commit"] == k.regel["source"]["commit"]
    [voortgang] = bij_planner["stappen"]
    assert voortgang["status"] == "voltooid" and voortgang["execution_id"] == v["request_id"], voortgang
    # Eén plan, één voorstel.
    r = _stel_voor(k, plan)
    assert r.status_code == 409 and r.json()["code"] == "plan_status_past_niet", r.text

    # Bijwerken: zonder eigen geverifieerd checkpoint dicht (T9 negatief), met checkpoint via de productieroute open.
    u = stel_voor(admin, "app.update", app_target("demo-app"), NIEUW).json()
    assert _codes(u) == ["backup_checkpoint_ontbreekt"] and u["blokkades"][0]["details"] == ["geen_passend_checkpoint"]
    _geblokkeerd(keur_goed(admin, u), "backup_checkpoint_ontbreekt")
    assert voer_uit(admin, u).status_code == 409 and len(nas.updated) == 0
    cp = _snapshot(k, "testpool/apps/demo-app", "voor-update")
    u = haal(admin, u)
    r = keur_goed(admin, u)
    assert r.status_code == 200 and r.json()["goedkeuring"]["backup_checkpoint_id"] == cp["request_id"], r.text
    r = voer_uit(admin, u)
    assert r.status_code == 200 and r.json()["resultaat"]["methode"] == "app.update", r.text
    assert nas.updated[-1][1]["values"]["image"]["tag"] == f"1.2.4@{DIGEST_B}"

    # Terugzetten (EX15 zonder migratie): opnieuw een vers checkpoint, dan precies de waarden van vóór de update.
    vorige = copy.deepcopy(nas.created[0]["values"])
    t = stel_voor(admin, "app.rollback", app_target("demo-app"), {"herstel_van": u["request_id"]}).json()
    assert t["preview"]["wijziging"]["soort"] == "terugzetten" and _codes(t) == ["backup_checkpoint_ontbreekt"]
    _snapshot(k, "testpool/apps", "voor-terugzetten")
    t = haal(admin, t)
    assert keur_goed(admin, t).status_code == 200
    r = voer_uit(admin, t)
    assert r.status_code == 200 and r.json()["resultaat"]["methode"] == "app.update", r.text
    assert nas.updated[-1] == ("demo-app", {"values": vorige})

    # Verwijderen: alleen de app; datasets en snapshots (ook de checkpoints) blijven.
    k.stack.vernieuw()
    datasets, snapshots = sorted(nas.datasets()), copy.deepcopy(nas.data["snapshots"])
    d = stel_voor(admin, "app.uninstall", app_target("demo-app")).json()
    assert keur_goed(admin, d).status_code == 200
    assert voer_uit(admin, d).status_code == 200
    assert sorted(nas.datasets()) == datasets and nas.data["snapshots"] == snapshots
    assert "pool.dataset.delete" not in nas.mutations and "pool.snapshot.delete" not in nas.mutations
    assert nas.app("demo-app") is None


# ------------------------------------------------------------------ T1: vervalst manifest en verkeerde binding
def _asf_sql(k: Keten, sql: str) -> None:
    import sqlalchemy as sa

    with k.store.engine.begin() as conn:
        conn.execute(sa.text(sql), {"id": k.version_id})


@pytest.mark.parametrize(
    ("sql", "details"),
    [
        pytest.param(
            "UPDATE manifest_version SET manifest = jsonb_set(manifest, '{image,digest}', "
            "'\"sha256:" + "b" * 64 + "\"') WHERE id = :id",
            {"velden": ["manifest_sha256"]}, id="manifest-gewijzigd-in-de-appstore",
        ),
        pytest.param(
            # Een veld dat alleen de handtekening van de appstore beschermt.
            "UPDATE manifest_version SET provenance = jsonb_set(provenance, '{record,source,ref}', '\"andere-tak\"') "
            "WHERE id = :id",
            {"reden": "handtekening_ongeldig"}, id="herkomstrecord-gewijzigd",
        ),
    ],
)  # fmt: skip
def test_t1_vervalst_manifest_bereikt_planner_en_nas_niet(keten: Keten, sql: str, details: dict[str, Any]) -> None:
    _asf_sql(keten, sql)
    r = _plan(keten)
    assert r.status_code == 409 and r.json()["code"] == "bewijs_ongeldig", r.text
    assert r.json()["details"] == details, r.text
    assert keten.plannen_bij_planner() == [] and schrijfaanroepen(keten.nas) == []


def _witte_lijst(monkeypatch: pytest.MonkeyPatch, regel: dict[str, Any], doel: Path) -> None:
    from hub.actions import beleid

    monkeypatch.setenv(
        "ASM_POLICY_DIR",
        str(policy_met_regels(doel / "policy-regel", [regel])),
    )
    beleid._geladen.cache_clear()


def test_t1_andere_manifesthash_dan_de_witte_lijst_geeft_geen_plan(
    keten: Keten, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _witte_lijst(monkeypatch, {**keten.regel, "manifest_sha256": "sha256:" + "6" * 64}, tmp_path)
    r = _plan(keten)
    assert r.status_code == 409 and r.json()["code"] == "catalogusversie_niet_toegelaten", r.text
    assert keten.plannen_bij_planner() == []


def test_t1_image_buiten_de_release_van_de_witte_lijst_wordt_niet_voorgesteld(
    keten: Keten, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """De regel laat een andere digest toe dan het (verder gelijke) manifest noemt: de stap van de echte planner past
    niet bij de release; de Hub stelt niets voor en TrueNAS krijgt niets."""
    _witte_lijst(monkeypatch, {**keten.regel, "image_digests": [DIGEST_B]}, tmp_path)
    r = _plan(keten)
    assert r.status_code == 201, r.text
    v = _stel_voor(keten, r.json())
    assert v.status_code in (409, 422) and "digest_verschilt" in v.text, v.text
    assert schrijfaanroepen(keten.nas) == []


def test_t1_verkeerde_binding_weigert_de_echte_planner(keten: Keten) -> None:
    """De planner zelf (§8.2): een binding die niet bij de claim van het Hub-dienst-JWT past, of een gebruiker die er
    een meestuurt, geeft 403 en geen plan."""
    import httpx

    from hub.catalog import plannen
    from hub.models import Service

    stap = _plan(keten)
    assert stap.status_code == 201, stap.text
    [eerste] = keten.plannen_bij_planner()
    body = {
        "manifest_yaml": yaml.safe_dump(MANIFEST, sort_keys=False, allow_unicode=True),
        "parameters": dict(PARAMETERS),
        "app_name": "demo-app",
        "doel": {**DOEL, "truenas_version": keten.nas.version},
        "catalog_binding": copy.deepcopy(eerste["document"]["catalog_binding"]),
    }
    sleutel_1 = str(uuid.uuid4())
    echte_claim = plannen.canonical_sha256(["POST", plannen.PREVIEW_PATH, sleutel_1, body])
    body["catalog_binding"]["release"]["image_digests"] = [DIGEST_B]  # andere release dan de Hub ondertekende
    sleutel = keten.stack.app.state.keyring()
    from sqlalchemy import select

    with keten.stack.app.state.sessionmaker() as db:
        svc = db.scalars(select(Service).where(Service.app_id == "jelly-leon-platform")).one()
        base, _ = plannen.service_base_url(db, None, svc)
        token, _ = sleutel.issue_hub_service_jwt(audience="jelly-leon-platform", service_id=str(svc.id),
                                                 catalog_request_sha256=echte_claim)  # fmt: skip
    for kop in (
        {"Authorization": f"Bearer {token}", "Idempotency-Key": sleutel_1},
        {"Authorization": "Bearer " + sleutel.issue_user_jwt(subject="beheer", audience="jelly-leon-platform",
                                                             roles=["admin"], ttl_seconds=60)[0],
         "Idempotency-Key": str(uuid.uuid4())},
    ):  # fmt: skip
        r = httpx.post(
            base + plannen.PREVIEW_PATH,
            json=body,
            headers=kop,
            trust_env=False,
            timeout=15,
        )
        assert r.status_code == 403 and r.json()["code"] == "forbidden", r.text
    assert len(keten.plannen_bij_planner()) == 1


# ------------------------------------------------------------------ EX15 en de gemarkeerde instantie
def test_ex15_na_een_migratie_geen_terugzetten_op_alleen_de_tag(keten: Keten) -> None:
    admin, nas = keten.admin, keten.nas
    _installeer(keten)
    _snapshot(keten, "testpool/apps/demo-app", "voor-update")
    u = stel_voor(
        admin,
        "app.update",
        app_target("demo-app"),
        {**NIEUW, "upgrade": {"migrations": True}},
    ).json()
    assert u["blokkades"] == [] and keur_goed(admin, u).status_code == 200
    assert voer_uit(admin, u).status_code == 200
    keten.stack.vernieuw()
    _snapshot(keten, "testpool/apps", "voor-terugzetten")
    t = stel_voor(admin, "app.rollback", app_target("demo-app"), {"herstel_van": u["request_id"]}).json()
    assert _codes(t) == ["database_herstel_vereist"]
    _geblokkeerd(keur_goed(admin, t), "database_herstel_vereist")
    # Ook via app.update terug naar de image van vóór de migratie: dicht.
    oud = {"image": {"repository": REPO, "tag": f"1.2.3@{DIGEST}"}}
    t = stel_voor(admin, "app.update", app_target("demo-app"), oud).json()
    assert _codes(t) == ["database_herstel_vereist"], t
    assert len(nas.updated) == 1


def test_gemarkeerde_instantie_zonder_recept_weigeren_hub_en_executor(
    keten: Keten,
) -> None:
    from executor.journal import Journal
    from sqlalchemy import select

    from hub.models import CatalogPlan

    admin, nas = keten.admin, keten.nas
    stap = _installeer(keten)
    _snapshot(keten, "testpool/apps/demo-app", "voor-update")
    # Executor: de installatie kreeg kluisplekken (markering in het eigen journaal).
    s = keten.stack.ex_settings
    Journal(s.replay_db, s.secrets_dir).markeer_kluis(
        str(uuid.uuid4()),
        "demo-app",
        "sha256:" + "d" * 64,
        [{"pad": "values.envs[0].value", "plek": "x"}],
    )
    # Alleen de executor weet het: de Hub stelt voor en keurt goed, de executor weigert zonder schrijfaanroep.
    u = stel_voor(admin, "app.update", app_target("demo-app"), NIEUW).json()
    assert keur_goed(admin, u).status_code == 200
    r = voer_uit(admin, u)
    assert r.status_code in (409, 502) and "kluisplekken_recept_ontbreekt" in r.text, r.text
    assert nas.updated == [] and "app.config" not in nas.mutations
    # De Hub weet het ook (register van de plannen): geen voorstel meer.
    with keten.stack.app.state.sessionmaker() as db:
        plan = db.scalars(select(CatalogPlan).where(CatalogPlan.id == uuid.UUID(stap["plan"]["plan_id"]))).one()
        plan.binding = {
            **plan.binding,
            "vault_refs": [{"pad": "values.envs[0].value", "plek": "x"}],
        }
        db.commit()
    for actie, params in (
        ("app.update", NIEUW),
        ("app.rollback", {"herstel_van": u["request_id"]}),
    ):
        r = stel_voor(admin, actie, app_target("demo-app"), params)
        assert r.status_code == 409 and r.json()["code"] == "kluisplekken_recept_ontbreekt", r.text
    assert nas.updated == []


# ------------------------------------------------------------------ rollen (kijker en V4)
def test_kijker_maakt_geen_plan_voorstel_goedkeuring_of_uitvoering(
    keten: Keten,
) -> None:
    admin = keten.admin
    make_user(admin, "vera", "viewer")
    vera = login_as(keten.stack.app, "vera")
    body = {"app_id": "demo-app", "version_id": keten.version_id, "app_name": "demo-app",
            "parameters": dict(PARAMETERS), "doel": DOEL}  # fmt: skip
    assert vera.post("/api/v1/catalog/plans/install", json=body, headers=idem()).status_code == 403
    plan = _plan(keten).json()
    r = vera.post(
        f"/api/v1/catalog/plans/{plan['plan_id']}/steps/{plan['step_id']}/propose",
        headers=idem(),
    )
    assert r.status_code == 403
    v = _stel_voor(keten, plan).json()
    assert keur_goed(vera, v).status_code == 403 and voer_uit(vera, v).status_code == 403
    assert schrijfaanroepen(keten.nas) == []


def _dienst_token(admin: Any) -> str:
    from conftest import enroll_body

    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "home-control-hub"})
    assert r.status_code == 201, r.text
    r = admin.post(
        "/api/v1/services/enroll",
        json=enroll_body("home-control-hub", token=r.json()["enrollment_token"]),
    )
    assert r.status_code == 200, r.text
    return str(r.json()["service_token"])


@pytest.mark.parametrize("wie", ["operator", "viewer", "kind", "dienst_token", "ai_runner"])
def test_v4_alleen_een_beheerder_bevestigt(keten: Keten, wie: str) -> None:
    """V4: de beheerdersbevestiging (goedkeuring van de R2-stap) kan niemand anders geven. De AI-runner heeft geen
    sessie; ook een door de Hub ondertekend token met de beheerdersrol is geen sessie."""
    from fastapi.testclient import TestClient

    admin, app = keten.admin, keten.stack.app
    plan = _plan(keten).json()
    v = _stel_voor(keten, plan).json()
    if wie in ("operator", "viewer", "kind"):
        make_user(admin, f"rol-{wie}", wie)
        c = login_as(app, f"rol-{wie}")
    else:
        c = TestClient(app)
        if wie == "dienst_token":
            c.headers["Authorization"] = f"Bearer {_dienst_token(admin)}"
        else:
            jwt_, _ = app.state.keyring().issue_user_jwt(subject="ai-runner", audience="ai-server-manager",
                                                         roles=["admin"], ttl_seconds=60)  # fmt: skip
            c.headers["Authorization"] = f"Bearer {jwt_}"
    r = keur_goed(c, v)
    assert r.status_code in (401, 403), r.text
    # Uitvoeren mag een operator (ADR-0030), maar zonder goedkeuring van een beheerder gebeurt er niets.
    r = voer_uit(c, v)
    assert r.status_code in ((409,) if wie == "operator" else (401, 403)), r.text
    assert haal(admin, v)["status"] == "wacht_op_goedkeuring" and schrijfaanroepen(keten.nas) == []
    # De beheerder kan het wel: de weigering hierboven is de rol, niet het voorstel.
    assert keur_goed(admin, v).status_code == 200


# ------------------------------------------------------------------ oorspronkelijke 050-negatieven in de keten
def test_ex47_hostnetwerk_of_privileged_naast_de_keten_geweigerd(keten: Keten) -> None:
    from policyhelpers import install_params

    for wijzig in ({"host_network": True}, {"privileged": True}):
        params = install_params("demo-app")
        params["app_create"]["values"].update(wijzig)
        r = stel_voor(keten.admin, "app.install", app_target("demo-app"), params)
        assert r.status_code in (403, 422), r.text
    assert schrijfaanroepen(keten.nas) == []


@pytest.mark.parametrize("actie", ["app.stop", "app.update", "app.uninstall"])
def test_emby_stoppen_bijwerken_of_verwijderen_geweigerd(keten: Keten, actie: str) -> None:
    nas = keten.nas
    app = copy.deepcopy(nas.app("my-house"))
    app["name"] = app["id"] = "emby"
    nas.data["app.query"].append(app)
    keten.stack.vernieuw()
    params = NIEUW if actie == "app.update" else {}
    r = stel_voor(keten.admin, actie, app_target("emby"), params)
    assert r.status_code == 403 and "emby_nooit_door_platform" in _codes(r.json()["details"]), r.text
    assert schrijfaanroepen(nas) == []


def test_verdwenen_versie_geeft_version_unavailable(keten: Keten) -> None:
    # Bij de appstore: een versie die er niet (meer) is.
    r = _plan(keten, version_id=str(uuid.uuid4()))
    assert r.status_code == 409 and r.json()["code"] == "version_unavailable", r.text
    # In de trein van TrueNAS: ix-app 1.4.8 verdwenen; de echte planner blokkeert, de Hub geeft de vaste code door.
    index = keten.nas.data["catalog.apps"]["stable"]["ix-app"]
    index["latest_version"] = "1.4.9"
    details = keten.nas.data["catalog.get_app_details"]["stable"]
    details["ix-app"] = {**index, "versions": {"1.4.9": {"version": "1.4.9"}}}
    keten.stack.worker_once(schedule=True)
    r = _plan(keten)
    assert r.status_code == 409 and r.json()["code"] == "plan_geblokkeerd", r.text
    assert "version_unavailable" in r.json()["details"]["codes"], r.text
    [bij_planner] = keten.plannen_bij_planner()
    assert bij_planner["document"]["stappen"] == []
    assert schrijfaanroepen(keten.nas) == []
