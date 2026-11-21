"""Directe executorproeven met een catalogusbinding (contract 1.3 §8.1; ADR-0032 T1-direct; S-P2-050d; Sim-getest).

Een met de testsleutel van de Hub correct ondertekend verzoek gaat rechtstreeks naar de executor. De executor toetst
de binding zelf aan de witte lijst in zijn beleid en aan zijn eigen readback: bij een afwijking nul schrijfaanroepen.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from asm_policy import load_policy
from asm_policy.etag import ABSENT
from executorhelpers import Hub, execute, nas_hub, set_write_key, write_nas
from executorhelpers import client as hub_client
from fakes.fake_truenas import FakeTrueNAS
from policyhelpers import (
    DIGEST,
    DIGEST_B,
    HOST,
    approval_for,
    catalog_binding,
    catalogus_regel,
    execution_request,
    install_params,
    policy_met_regels,
    proposal,
)

REPO = "ghcr.io/voorbeeld/demo-app"


@pytest.fixture
def nas() -> Iterator[FakeTrueNAS]:
    fake = write_nas().start()
    yield fake
    fake.stop()


def _stack(tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch, regels: list[dict[str, Any]]) -> Any:
    pad = policy_met_regels(tmp_path / "policy", regels)
    monkeypatch.setenv("ASM_POLICY_DIR", str(pad))
    hub = nas_hub(tmp_path / "appdata", nas)
    set_write_key(hub, nas)
    return hub, hub_client(hub), load_policy(pad)


def _verzoek(hub: Hub, policy: Any, params: dict[str, Any]) -> dict[str, Any]:
    prop = proposal("app.install", {"host_id": HOST, "app_id": "demo-app"}, params, expected_version=ABSENT)
    approval = approval_for(prop, policy_hash=policy.hash, risk_class="R2", backup_checkpoint_id=None)
    return execution_request(hub.policy_key, prop, policy_hash=policy.hash, risk_class="R2", approval=approval)


def _params(**binding_change: Any) -> dict[str, Any]:
    p = install_params("demo-app")
    p["catalog_binding"] = catalog_binding(catalogus_regel(), **binding_change)
    p["manifest"]["manifest_sha256"] = catalogus_regel()["manifest_sha256"]
    return p


def _writes(nas: FakeTrueNAS) -> list[str]:
    return [m for m in nas.mutations if m != "app.config"]


def test_passende_binding_installeert_met_digest_uit_de_readback(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub, c, policy = _stack(tmp_path, nas, monkeypatch, [catalogus_regel()])
    r = execute(c, hub, _verzoek(hub, policy, _params()))
    assert r.status_code == 200, r.text
    assert r.json()["methode"] == "app.create" and r.json()["readback"]["digests"] == [f"{REPO}@{DIGEST}"]
    assert _writes(nas) == ["app.create"]


def test_zonder_regel_in_het_eigen_beleid_nul_schrijfaanroepen(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub, c, policy = _stack(tmp_path, nas, monkeypatch, [])
    r = execute(c, hub, _verzoek(hub, policy, _params()))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", r.text
    assert "catalogusversie_niet_toegelaten" in r.text
    assert _writes(nas) == [] and nas.logins == 0


AFWIJKINGEN: list[tuple[str, Any]] = [
    ("andere manifesthash", lambda b: b["provenance"]["record"].update(manifest_sha256="sha256:" + "9" * 64)),
    ("andere uitgever", lambda b: b["provenance"]["record"].update(publisher_key_sha256="sha256:" + "1" * 64)),
    ("andere commit", lambda b: b["provenance"]["record"]["source"].update(commit="d" * 40)),
    ("andere digest in de release", lambda b: b["release"].update(image_digests=[DIGEST_B])),
    ("andere instantie", lambda b: b["instance"].update(app_name="andere-app")),
    ("kluisplek", lambda b: b.update(vault_refs=[{"path": "p", "parameter": "q", "ref": "vault://app/demo-app/q"}])),
]


@pytest.mark.parametrize(("naam", "wijzig"), AFWIJKINGEN, ids=[a[0] for a in AFWIJKINGEN])
def test_afwijkende_binding_nul_schrijfaanroepen(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch, naam: str, wijzig: Any
) -> None:
    hub, c, policy = _stack(tmp_path, nas, monkeypatch, [catalogus_regel()])
    params = _params()
    wijzig(params["catalog_binding"])
    r = execute(c, hub, _verzoek(hub, policy, params))
    assert r.status_code == 422 and r.json()["code"] == "parameters_ongeldig", (naam, r.text)
    assert _writes(nas) == [], naam


def test_andere_digest_op_de_nas_is_een_afwijking(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub, c, policy = _stack(tmp_path, nas, monkeypatch, [catalogus_regel()])
    nas.digest_override[REPO] = DIGEST_B
    r = execute(c, hub, _verzoek(hub, policy, _params()))
    assert r.status_code == 409 and r.json()["code"] == "afwijking", r.text
    codes = [a["code"] for a in r.json()["details"]["afwijkingen"]]
    assert "digest_verschilt" in codes and r.json()["details"]["gestopt"] is True


def test_naam_al_bezet_op_de_nas_geen_installatie(
    tmp_path: Path, nas: FakeTrueNAS, monkeypatch: pytest.MonkeyPatch
) -> None:
    hub, c, policy = _stack(tmp_path, nas, monkeypatch, [catalogus_regel()])
    params = _params()
    params["app_create"]["app_name"] = "my-house"
    params["manifest"]["app_id"] = "demo-app"
    params["catalog_binding"]["instance"]["app_name"] = "my-house"
    prop = proposal("app.install", {"host_id": HOST, "app_id": "my-house"}, params, expected_version=ABSENT)
    approval = approval_for(prop, policy_hash=policy.hash, risk_class="R2", backup_checkpoint_id=None)
    req = execution_request(hub.policy_key, prop, policy_hash=policy.hash, risk_class="R2", approval=approval)
    r = execute(c, hub, req)
    assert r.status_code in (403, 409), r.text
    assert _writes(nas) == []
