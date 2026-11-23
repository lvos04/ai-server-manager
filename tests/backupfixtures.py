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
    pagina = {
        "type": "backups",
        "status": "ok",
        "reason_code": None,
        "observed_at": tijd,
        "total": 1,
        "items": [rapport],
        "next_cursor": None,
    }
    bevestig_herstelpagina(pagina)
    return pagina


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


def bevestig_herstelpagina(pagina: dict[str, Any]) -> None:
    """Bronberekening over de onbewerkte items, inclusief eventuele extra bronvelden."""
    import hashlib
    import json

    inhoud = [
        pagina["type"],
        datetime.fromisoformat(pagina["observed_at"]).isoformat(),
        pagina["reason_code"],
        pagina["items"],
    ]
    pagina["snapshot_id"] = hashlib.sha256(
        json.dumps(inhoud, separators=(",", ":"), sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def archiefopname(now: datetime, server: str = "proefserver", gebruiker: str = "proef") -> dict[str, Any]:
    return {
        "gemaakt": iso(now),
        "schema": "jelly-leon/emby-kijkgegevens-export/1",
        "tool": {"naam": "jelly-leon-emby-overname", "versie": "0.1.0"},
        "bron": {"product": "Emby Server", "server_id": server, "server_naam": "proef", "versie": "1"},
        "bibliotheken": [],
        "plugins": [],
        "classificaties": [],
        "items": {
            "film": {"id": "film", "type": "Movie", "naam": "Film", "provider_ids": {}, "pad": None, "grootte": 1}
        },
        "gebruikers": [
            {
                "id": gebruiker,
                "naam": "testpersoon",
                "beleid": {"IsAdministrator": False},
                "configuratie": {"RememberAudioSelections": True},
                "heeft_wachtwoord": True,
                "zichtbaar": ["film"],
                "kijkgegevens": {
                    "film": {
                        "gezien": True,
                        "aantal": 2,
                        "laatst": now.strftime("%Y-%m-%dT%H:%M:%S.0000000Z"),
                        "positie": 1200000,
                        "favoriet": True,
                        "beoordeling": 8.0,
                        "vind_ik_leuk": None,
                    }
                },
                "spoorkeuzes": {
                    "film": {
                        "audio": {"type": "Audio", "codec": "aac", "taal": "nl", "titel": None},
                        "ondertitel": None,
                        "bestand": {"pad": None, "grootte": 1},
                    }
                },
                "spoorkeuzes_niet_gelezen": [],
                "benoemde_favorieten": ["film"],
            },
        ],
    }


def schrijf_archiefpaar(root, opname):
    import hashlib
    import json

    inhoud = {k: v for k, v in opname.items() if k not in ("gemaakt", "inhoud_sha256")}
    opname["inhoud_sha256"] = hashlib.sha256(
        json.dumps(inhoud, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    data = json.dumps(opname, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    digest = hashlib.sha256(data).hexdigest()
    for mapnaam in ("overname", "backups"):
        mapje = root / mapnaam
        mapje.mkdir(exist_ok=True)
        (mapje / "emby-export.json").write_bytes(data)
        (mapje / "emby-export.json.sha256").write_text(f"{digest}  emby-export.json\n")
    return digest


def inventaris_referentie(root, server="proefserver", namen=("testpersoon",)):
    import hashlib
    import json

    vertrouwd = root / "overnamebron"
    vertrouwd.mkdir(exist_ok=True)
    inventaris = {
        "schema": "jelly-leon/emby-inventaris/1",
        "emby": {"server_id": server},
        "gebruikers": [{"naam": naam} for naam in namen],
        "bibliotheken": [],
        "plugins": [],
    }
    data = json.dumps(inventaris).encode()
    (vertrouwd / "inventaris.json").write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def exportbewijs(root, opname, digest, *, gelezen_sporen):
    """Simuleert de uitvoer van cmd_export en de verrichte GET's, los van de spoorkeuzes in het archief."""
    import hashlib
    import json

    vertrouwd = root / "overnamebron"
    vertrouwd.mkdir(exist_ok=True)
    gebruikers = opname["gebruikers"]
    bewijs = {
        "sha256": digest,
        "inhoud_sha256": opname["inhoud_sha256"],
        "gebruikers": len(gebruikers),
        "items_met_kijkgegevens": sum(len(g["kijkgegevens"]) for g in gebruikers),
    }
    verzoeken = [
        (p, [])
        for p in (
            "/System/Info",
            "/Library/VirtualFolders/Query",
            "/Localization/ParentalRatings",
            "/Plugins",
            "/Users",
        )
    ]
    verzoeken.extend((f"/Users/{g['id']}", []) for g in gebruikers)
    for g in gebruikers:
        uid = g["id"]
        verzoeken.append((f"/Users/{uid}/Items", ["EnableUserData", "StartIndex"]))
        verzoeken.extend((p, ["UserId", "Filters"]) for p in ("/Persons", "/Artists", "/Genres", "/Studios"))
        verzoeken.extend((f"/Items/{item}/PlaybackInfo", ["UserId"]) for item in gelezen_sporen.get(uid, ()))
    log = vertrouwd / "emby-export.log.jsonl"
    log.write_text(
        "".join(
            json.dumps(
                {
                    "doel": "Emby",
                    "methode": "GET",
                    "pad": p,
                    "query_sleutels": q,
                    "status": 200,
                    "tijd": opname["gemaakt"],
                }
            )
            + "\n"
            for p, q in verzoeken
        )
    )
    bewijs["leeslog_sha256"] = hashlib.sha256(log.read_bytes()).hexdigest()
    (vertrouwd / "exportbewijs.json").write_text(json.dumps(bewijs))
