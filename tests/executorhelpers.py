"""Gedeelde hulp voor de executortests: een gekoppelde ``hub-link.json`` met een gepinde Hub-sleutel en JWT's die
daarmee zijn ondertekend (contract 1.3 §4.2–§4.7), een gepinde policy-sleutel voor ondertekende ``ExecutionRequest``s
(§8) en de fake TrueNAS met een schrijfsleutel (§3.9). Alleen testwaarden; nooit echte NAS-gegevens."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from asm_policy import load_policy
from executor.app import create_app
from executor.journal import Journal
from executor.naslink import NasLinkStore
from executor.truenas import fetch_fingerprint
from executorhub import AUD, Hub, b64, linked_fields  # noqa: F401 — ook beschikbaar voor de bestaande executortests
from fakes.fake_truenas import FakeTrueNAS, KeyProfile
from fastapi.testclient import TestClient
from policyhelpers import POLICY_DIR, approval_for, execution_request

POLICY = load_policy(POLICY_DIR)
READ_KEY = "readonly-test-key-0123456789"
WRITE_KEY = "schrijf-test-key-aaaabbbbcccc"
NAS_HOST = "127.0.0.1"
UNLINK = "/connector/v1/hub-link/unlink"
# Toegestane Host voor formulier-POST's (§3.7 punt 4): een naam onder .local.
BASE = "http://executor.local"


def client(hub: Hub) -> TestClient:
    return TestClient(create_app(hub.settings), base_url=BASE)


def auth(token: str, key: str | None = None) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}"}
    if key is not None:
        h["Idempotency-Key"] = key
    return h


# ---------------------------------------------------------------------- TrueNAS (fake) en ondertekende verzoeken
def write_nas(**kwargs: Any) -> FakeTrueNAS:
    """Fake TrueNAS met een alleen-lezen-sleutel en een schrijfsleutel (FULL_ADMIN). Nog niet gestart."""
    keys = {READ_KEY: KeyProfile(), WRITE_KEY: KeyProfile(roles=["FULL_ADMIN"], write=True)}
    return FakeTrueNAS(keys=keys, noise=False, **kwargs)


def nas_hub(data_dir: Path, nas: FakeTrueNAS, **instellingen: Any) -> Hub:
    """Gekoppelde executor die de fake als TrueNAS gebruikt (adres via de instelling, zoals ``EXECUTOR_TRUENAS_HOST``).
    Het beleid komt uit de repo en is daar beschrijfbaar; in het image is het alleen-lezen."""
    basis: dict[str, Any] = {
        "truenas_host": NAS_HOST,
        "truenas_port": nas.port,
        "truenas_timeout_seconds": 5,
        "readback_wait_seconds": 0.6,
        "readback_poll_seconds": 0.05,
        "allow_writable_policy": True,
    }
    basis.update(instellingen)
    return Hub(data_dir, **basis)


def set_write_key(hub: Hub, nas: FakeTrueNAS, key: str = WRITE_KEY, roles: list[str] | None = None) -> str:
    """De schrijfsleutel rechtstreeks vastleggen (zonder het formulier): adres, vingerafdruk en versleutelde sleutel."""
    fingerprint = fetch_fingerprint(NAS_HOST, nas.port)
    NasLinkStore(hub.settings.secrets_dir).save_key(NAS_HOST, nas.port, fingerprint, key, roles or ["FULL_ADMIN"])
    return fingerprint


def signed(
    hub: Hub, prop: dict[str, Any], *, risk_class: str, approval: dict[str, Any] | None = None, **change: Any
) -> dict[str, Any]:
    return execution_request(
        hub.policy_key, prop, policy_hash=POLICY.hash, risk_class=risk_class, approval=approval, **change
    )


_BEGIN, _FINISH = Journal.begin, Journal.finish


def checkpoint(
    hub: Hub,
    dataset: str = "testpool/apps",
    snapshot: str = "testpool/apps@auto-latest",
    createtxg: str = "1000",
    nas: FakeTrueNAS | None = None,
) -> str:
    """Een checkpoint in het eigen journaal van de executor, alsof hij die snapshot zelf maakte met een voltooide
    ``zfs.snapshot.create`` (de verificatie zelf blijft echt: bestaan en createtxg per dataset, leeftijd en dekking
    worden bij de uitvoering gecontroleerd). Met ``nas``: recursief, zoals een periodieke taak; de fake krijgt dan voor
    elke dataset eronder dezelfde snapshot en het checkpoint telt ze als leden."""
    leden = {dataset: createtxg}
    if nas is not None:
        naam = snapshot.split("@", 1)[1]
        for d in nas.datasets():
            if d == dataset or d.startswith(dataset + "/"):
                rijen = nas.data["snapshots"].setdefault(d, [])
                if not any(x["name"] == f"{d}@{naam}" for x in rijen):
                    rijen.append({"name": f"{d}@{naam}", "dataset": d, "createtxg": createtxg})
                leden[d] = createtxg
    request_id = nonce = str(uuid.uuid4())
    j = Journal(hub.settings.replay_db, hub.settings.secrets_dir)
    # Ongebonden (de tests vervangen soms Journal.begin of Journal.finish om een fout na te bootsen).
    _BEGIN(
        j,
        request_id=request_id,
        nonce=nonce,
        action_id="zfs.snapshot.create",
        target={"host_id": "test", "dataset": dataset},
        methode="pool.snapshot.create",
        before_hash="voor",
    )
    j.leg_checkpoint_vast(request_id, dataset, snapshot, createtxg, True, leden)
    _FINISH(j, nonce, status="uitgevoerd", after_hash="na")
    return request_id


def approved(hub: Hub, prop: dict[str, Any], *, risk_class: str = "R2", **change: Any) -> dict[str, Any]:
    """Ondertekend verzoek met een passende goedkeuring; ``change`` wijzigt velden van de goedkeuring."""
    basis: dict[str, Any] = {"backup_checkpoint_id": str(uuid.uuid4())}
    if prop.get("action_id") in ("app.update", "app.rollback") and "backup_checkpoint_id" not in change:
        basis["backup_checkpoint_id"] = checkpoint(hub)
    basis.update(change)
    approval = approval_for(prop, policy_hash=POLICY.hash, risk_class=risk_class, **basis)
    return signed(hub, prop, risk_class=risk_class, approval=approval)


def execute(c: TestClient, hub: Hub, request: Any, key: str | None = None) -> Any:
    return c.post("/api/v1/execute", json=request, headers=auth(hub.jwt(), key or str(uuid.uuid4())))
