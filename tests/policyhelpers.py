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
        "image": {"repository": "ghcr.io/voorbeeld/demo-app", "tag": f"1.2.3@{DIGEST}", "pull_policy": "missing"},
        "restart_policy": "unless-stopped",
        "TZ": "Etc/UTC",
        "envs": [{"name": "APP_MODE", "value": "prod"}],
        "ports": [{"bind_mode": "published", "port_number": 30555, "container_port": 8080, "protocol": "tcp"}],
        "storage": [
            {
                "type": "host_path",
                "mount_path": "/data",
                "host_path_config": {"path": "/mnt/testpool/apps/demo-app", "acl_enable": False},
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
    action_id: str, target: dict[str, Any], parameters: dict[str, Any] | None = None, **change: Any
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
        "policy_decision": {"risk_class": risk_class, "rule_ids": rule_ids or [], "policy_hash": policy_hash},
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
