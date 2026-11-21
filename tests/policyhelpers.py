"""Gedeelde testgegevens voor het risicobeleid (geen echte NAS-waarden: poolnaam en adressen zijn testwaarden)."""

from __future__ import annotations

import copy
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from asm_policy import execreq
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

REPO = Path(__file__).resolve().parents[1]
POLICY_DIR = REPO / "policy"
DIGEST = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
HOST = "nas-primary"


def install_params(app: str = "demo-app", **values: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "image": {
            "repository": "ghcr.io/voorbeeld/demo-app",
            "tag": f"1.2.3@{DIGEST}",
            "pull_policy": "missing",
        },
        "restart_policy": "unless-stopped",
        "TZ": "Etc/UTC",
        "envs": [{"name": "APP_MODE", "value": "prod"}],
        "ports": [
            {
                "bind_mode": "published",
                "port_number": 30555,
                "container_port": 8080,
                "protocol": "tcp",
            }
        ],
        "storage": [
            {
                "type": "host_path",
                "mount_path": "/data",
                "host_path_config": {
                    "path": "/mnt/testpool/apps/demo-app",
                    "acl_enable": False,
                },
            }
        ],
        "resources": {"limits": {"cpus": 2, "memory": 1024}},
    }
    base.update(values)
    return {
        "app_create": {
            "app_name": app,
            "custom_app": False,
            "catalog_app": "ix-app",
            "train": "stable",
            "version": "1.4.8",
            "values": base,
        },
        "manifest": {"app_id": app, "image_digest": DIGEST, "version": "1.2.3"},
    }


def proposal(
    action_id: str,
    target: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    **change: Any,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "idempotency_key": str(uuid.uuid4()),
        "action_id": action_id,
        "target": target,
        "parameters": parameters or {},
        "reason": "test",
        "actor": {"type": "user", "id": "beheerder"},
        "expected_version": "absent",
        "risk_claim": None,
        "evidence_ids": [],
        "expires_in_seconds": 600,
    }
    out.update(change)
    return out


def execution_request(
    key: Ed25519PrivateKey,
    prop: dict[str, Any],
    *,
    policy_hash: str,
    risk_class: str,
    rule_ids: list[str] | None = None,
    approval: dict[str, Any] | None = None,
    now: datetime | None = None,
    ttl: int = 300,
    **change: Any,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    req: dict[str, Any] = {
        "proposal": copy.deepcopy(prop),
        "approval": approval,
        "policy_decision": {
            "risk_class": risk_class,
            "rule_ids": rule_ids or [],
            "policy_hash": policy_hash,
        },
        "issued_at": execreq.iso(now),
        "expires_at": execreq.iso(now + timedelta(seconds=ttl)),
        "nonce": str(uuid.uuid4()),
    }
    req.update(change)
    return execreq.sign(req, key)


def approval_for(
    prop: dict[str, Any],
    *,
    policy_hash: str,
    risk_class: str,
    now: datetime | None = None,
    ttl: int = 600,
    **change: Any,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    out: dict[str, Any] = {
        "approval_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "preview_hash": "sha256:" + "c" * 64,
        "resource_etag": prop["expected_version"],
        "policy_hash": policy_hash,
        "risk_class": risk_class,
        "approved_by": "beheerder",
        "approved_at": execreq.iso(now),
        "expires_at": execreq.iso(now + timedelta(seconds=ttl)),
        "one_time_nonce": str(uuid.uuid4()),
        "backup_checkpoint_id": None,
        "action_scope": execreq.action_scope(prop["action_id"], prop["target"], prop["parameters"]),
    }
    out.update(change)
    return out


# ---------------------------------------------------------------------- catalogusbinding (contract §8.1; S-P2-050d)
# Testwaarden voor één toegelaten catalogusversie: een gegenereerde testuitgever, geen echte bron of release.
CAT_APP = "demo-app"
CAT_COMMIT = "c" * 40
CAT_SCHEMA = "sha256:" + "5" * 64
CAT_VALIDATOR = "0.1.0"  # de versie die de gepinde validator (hub.catalog.asf) rapporteert
CAT_URL = "https://forge.test/leon/demo-catalogus"
CAT_PUBLISHER = "sha256:" + "7" * 64
CAT_SOURCE_ID = "33333333-3333-4333-8333-333333333333"


def catalogus_regel(manifest_sha256: str = "sha256:" + "6" * 64, **change: Any) -> dict[str, Any]:
    regel: dict[str, Any] = {
        "app_id": CAT_APP,
        "version": "1.2.3",
        "catalog": {"train": "stable", "app": "ix-app", "version": "1.4.8"},
        "manifest_sha256": manifest_sha256,
        "image_digests": [DIGEST],
        "schema_sha256": CAT_SCHEMA,
        "validator_version": CAT_VALIDATOR,
        "source": {
            "source_id": CAT_SOURCE_ID,
            "url": CAT_URL,
            "subpath": "apps",
            "path": "demo-app/manifest.yaml",
            "commit": CAT_COMMIT,
        },
        "publisher_key_sha256": CAT_PUBLISHER,
        "formuliervelden": sorted(install_params()["app_create"]["values"]),
        "kluisplekken": [],
    }
    regel.update(change)
    return regel


def provenance_record(regel: dict[str, Any], **change: Any) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "app_id": regel["app_id"],
        "version": regel["version"],
        "entry_id": "11111111-1111-4111-8111-111111111111",
        "version_id": "22222222-2222-4222-8222-222222222222",
        "manifest_sha256": regel["manifest_sha256"],
        "schema_sha256": regel["schema_sha256"],
        "validator_version": regel["validator_version"],
        "source": {
            "source_id": regel["source"]["source_id"],
            "kind": "git",
            "url": regel["source"]["url"],
            "ref": "main",
            "commit": regel["source"]["commit"],
            "path": regel["source"]["path"],
            "subpath": regel["source"]["subpath"],
        },
        "fetched_at": "2026-11-21T10:00:00Z",
        "publisher_signature": "verified",
        "publisher_key_id": regel["publisher_key_sha256"][7:23],
        "publisher_key_sha256": regel["publisher_key_sha256"],
        "valid": True,
        "errors": 0,
        "warnings": 0,
    }
    rec.update(change)
    return rec


def catalog_binding(regel: dict[str, Any], app: str = CAT_APP, **change: Any) -> dict[str, Any]:
    b: dict[str, Any] = {
        "appstore_service_id": "44444444-4444-4444-8444-444444444444",
        "source_approval_revision": "sha256:" + "8" * 64,
        "provenance": {
            "record": provenance_record(regel),
            "signature": "A" * 86 + "==",
            "key_id": "0123456789abcdef",
            "alg": "EdDSA",
        },
        "release": {
            "catalog": dict(regel["catalog"]),
            "image_digests": list(regel["image_digests"]),
        },
        "plan_id": "55555555-5555-4555-8555-555555555555",
        "step_id": "installeren",
        "plan_etag": '"plan-55555555-5555-4555-8555-555555555555-v1"',
        "instance": {
            "host_id": HOST,
            "instance_id": "66666666-6666-4666-8666-666666666666",
            "registry_revision": "inventaris:1",
            "app_name": app,
            "expected_version": "absent",
        },
        "vault_refs": [],
    }
    b.update(change)
    return b


def policy_met_regels(doel: Path, regels: list[dict[str, Any]]) -> Path:
    """Kopie van het beleid met deze witte lijst (alleen tests; het echte beleid blijft leeg)."""
    import shutil

    import yaml

    shutil.copytree(POLICY_DIR, doel)
    pad = doel / "catalogus.yaml"
    doc = yaml.safe_load(pad.read_text(encoding="utf-8"))
    doc["installaties"] = regels
    pad.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return doel
