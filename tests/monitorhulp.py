"""Alleen tests: leg voor een catalogus-app een handmatig bevestigde monitor vast (monitorplan, C1.3-ASM-20), zodat
tests die over iets anders gaan een verder gezonde app als gezond kunnen zien. Zonder dit is zo'n app 'niet bewaakt'."""

from __future__ import annotations

import uuid
from typing import Any

from asm_policy.canonical import canonical_sha256

from hub import audit
from hub.models import CatalogApp
from hub.monitoring import monitorplan

MONITOR = {"pad": "/health", "verwachte_status": 200, "timeout_s": 5, "interval_s": 60}


def bevestig_monitor(app: Any, catalog_app_id: Any) -> None:
    with app.state.sessionmaker() as db:
        row = db.get(CatalogApp, uuid.UUID(str(catalog_app_id)))
        assert row is not None
        tcp = [p for p in row.poorten or [] if p.get("protocol") == "tcp" and p.get("host_poort")]
        assert tcp, "app zonder gemeten TCP-hostpoort"
        app_id = row.app_id or row.runtime_id
        manifest = {
            "app_id": app_id,
            "healthcheck": {"port": "web", "monitor": MONITOR},
            "network": {
                "ports": [
                    {
                        "name": "web",
                        "protocol": "tcp",
                        "container_port": tcp[0]["container_poort"],
                        "host_port": tcp[0]["host_poort"],
                    }
                ]
            },
        }
        sha = canonical_sha256(manifest)
        blok = monitorplan.gecontroleerd_manifest(manifest, sha, app_id, app.state.keyring().identity)
        row.appstore = {
            "status": "gekoppeld",
            "app_id": app_id,
            "manifest_sha256": sha,
            "monitor": blok,
        }
        regel = monitorplan.regel(db, row, app.state.settings)
        assert regel["plan_sha256"], regel
        audit.record(
            db,
            actor_type="user",
            actor_id="test",
            action=monitorplan.BEVESTIGING_ACTIE,
            target_type="catalog_app",
            target_id=str(row.id),
            details={"plan_sha256": regel["plan_sha256"]},
        )
        db.commit()
