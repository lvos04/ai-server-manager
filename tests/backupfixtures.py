"""Testmetingen van de bestaande apps, zonder contact met een dienst."""

from datetime import datetime, timedelta
from typing import Any

from hub.timeutil import iso


def herstelpagina(now: datetime, uren: float = 0.5) -> dict[str, Any]:
    tijd = iso(now)
    deel = {
        "status": "healthy",
        "verified": True,
        "reason_code": None,
        "created_at": iso(now - timedelta(hours=uren)),
        "age_seconds": int(uren * 3600),
    }
    db = {"sha256": "a" * 64, "schema_versions": ["1"]}
    forks = [
        {"instance_id": iid, "name": f"{iid.split('-')[0]}_backup_v1_2.zip", **deel}
        for iid in (
            "sonarr-series",
            "sonarr-anime",
            "radarr-films",
            "radarr-animefilms",
        )
    ]
    rapport = {
        "id": "backups",
        "status": "healthy",
        "observed_at": tijd,
        "core": {**deel, **db},
        "encoder": {**deel, "databases": [db]},
        "bundle": {**deel, "enabled": True, "key_match": True, "fingerprint": "b" * 16},
        "offsite": {**deel, "target_kind": "webdav", "sha256": "b" * 64},
        "forks": forks,
        "rollback": {
            "owner": "mediaguard",
            "pre_update_restore_mode": "handmatig",
            "staged": False,
        },
    }
    return {
        "type": "backups",
        "status": "ok",
        "reason_code": None,
        "observed_at": tijd,
        "total": 1,
        "snapshot_id": "a" * 64,
        "items": [rapport],
        "next_cursor": None,
    }


def groene_appmetingen(now: datetime):
    """De P2-gateproeven isoleren hun eigen meetwaarde met bevestigde S-P3-100-invoer. MSO ontbreekt in de proef."""
    from hub.backup.appdekking import (
        EMBY,
        HUIS,
        MG,
        MSO,
        AppBronnen,
        Meting,
        herstelrapport,
        huisrapport,
    )

    return AppBronnen(
        metingen={
            MG: herstelrapport(herstelpagina(now), now, 900),
            HUIS: huisrapport(
                {
                    "checks": [
                        {
                            "key": "backup",
                            "state": "ok",
                            "age_h": 1,
                            "auto_failures": 0,
                            "auto_last_error": None,
                        }
                    ]
                },
                now,
            ),
            EMBY: Meting(
                status="gedekt",
                observed_at=now,
                gemaakt_op=now,
                aanwezig=True,
                in_backup=True,
            ),
        },
        afwezig={MSO},
        rpo_uren={"emby": 24},
    )
