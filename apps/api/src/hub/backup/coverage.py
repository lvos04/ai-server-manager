"""Back-updekking per app en per dataset (B12-001/002/003) en snapshotbeleid als voorstel (B12-002).

Uitgangspunten (B12 §5, 08_UI "Backups"):
- Lokale ZFS-snapshot is geen offsite back-up; een geslaagde (OneDrive-)synchronisatie is **geen herstelgarantie**.
  Alleen een vastgelegde, geslaagde hersteltest telt als bewijs van herstelbaarheid.
- Een snapshot zonder app-consistente database-export telt **niet** als volledige app-back-up.
- App-consistente export van andere apps loopt via hun connector-capability; zonder connector is die ``unknown``
  (``capability_unavailable``), nooit gesimuleerd succes. Voor de Hub zelf telt de geverifieerde ``pg_dump``.
- Alles wat uit een verouderde of mislukte meting komt, is ``unknown``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from hub import APP_ID
from hub.timeutil import iso

SYNC_IS_GEEN_GARANTIE = "Synchronisatie is geen herstelgarantie; alleen een geslaagde hersteltest telt als bewijs."


@dataclass
class CoverageInputs:
    apps: dict[str, Any]  # kind_state("apps")
    datasets: dict[str, Any]
    pools: dict[str, Any]
    snapshot_tasks: dict[str, Any]
    latest_snapshots: dict[str, Any]
    cloudsync: dict[str, Any]
    replication: dict[str, Any]
    rpo_rto: dict[str, dict[str, float]]  # app_id -> {rpo_uren, rto_uren} uit D16 (leeg = onbekend)
    self_backup: dict[str, Any] | None  # laatste geverifieerde eigen back-up
    self_backup_max_age_seconds: int
    restore_tests: list[dict[str, Any]]
    enrolled_apps: set[str]
    extra_datasets: list[str] = field(default_factory=list)  # uit D02 (appdata/media)
    now: datetime = field(default_factory=lambda: datetime.now(UTC))


def _ok(state: dict[str, Any]) -> bool:
    return state.get("status") == "ok"


def _age_hours(ts: str | None, now: datetime) -> float | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return round((now - dt).total_seconds() / 3600, 2)


def _dataset_for_path(path: str, mounts: list[tuple[str, str]]) -> str | None:
    best: tuple[int, str] | None = None
    for mountpoint, name in mounts:
        inside = path == mountpoint or path.startswith(mountpoint.rstrip("/") + "/")
        if inside and (best is None or len(mountpoint) > best[0]):
            best = (len(mountpoint), name)
    return best[1] if best else None


def _covered_by_task(ds: str, task: dict[str, Any]) -> bool:
    tds = str(task.get("dataset") or "")
    if not task.get("ingeschakeld"):
        return False
    if ds == tds:
        return True
    if task.get("recursief") and ds.startswith(tds + "/"):
        return not any(ds == ex or ds.startswith(str(ex) + "/") for ex in task.get("uitgesloten") or [])
    return False


def _path_relation(mountpoint: str | None, pad: str | None) -> str | None:
    if not mountpoint or not pad:
        return None
    mp, p = mountpoint.rstrip("/"), pad.rstrip("/")
    if mp == p or mp.startswith(p + "/"):
        return "volledig"
    if p.startswith(mp + "/"):
        return "gedeeltelijk"
    return None


def _restore_for(app_id: str | None, dataset: str | None, tests: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [t for t in tests if (app_id and t.get("app_id") == app_id) or (dataset and t.get("dataset") == dataset)]
    matches.sort(key=lambda t: str(t.get("uitgevoerd_op") or ""), reverse=True)
    return matches[0] if matches else None


def dataset_coverage(ds: dict[str, Any], inp: CoverageInputs, apps_by_ds: dict[str, list[str]]) -> dict[str, Any]:
    name = str(ds["naam"])
    # lokaal
    if not _ok(inp.snapshot_tasks):
        lokaal: dict[str, Any] = {
            "status": "unknown",
            "reason_code": inp.snapshot_tasks.get("reason_code"),
            "taken": [],
        }
    else:
        tasks = [t for t in inp.snapshot_tasks.get("data") or [] if _covered_by_task(name, t)]
        lokaal = {
            "status": "gedekt" if tasks else "niet_gedekt",
            "reason_code": None,
            "taken": [t.get("id") for t in tasks],
        }
        if tasks:
            latest: str | None = None
            snap_reason = None
            if _ok(inp.latest_snapshots):
                per = (inp.latest_snapshots.get("data") or {}).get("per_dataset") or {}
                stamps = [str((per.get(str(t.get("dataset"))) or {}).get("aangemaakt_op") or "") for t in tasks]
                stamps = [s for s in stamps if s]
                latest = max(stamps) if stamps else None
            else:
                snap_reason = inp.latest_snapshots.get("reason_code")
            lokaal["laatste_snapshot"] = latest
            lokaal["leeftijd_uren"] = _age_hours(latest, inp.now)
            if latest is None:
                lokaal["laatste_snapshot_status"] = "unknown"
                lokaal["laatste_snapshot_reden"] = snap_reason or "geen_snapshot_gevonden"
    lokaal["observed_at"] = inp.snapshot_tasks.get("observed_at")

    # extern (cloud sync + replicatie)
    extern: dict[str, Any] = {
        "herstelgarantie": False,
        "opmerking": SYNC_IS_GEEN_GARANTIE,
        "cloud_sync": [],
        "replicatie": [],
    }
    reasons = []
    if _ok(inp.cloudsync):
        for t in inp.cloudsync.get("data") or []:
            rel = _path_relation(ds.get("mountpoint"), t.get("pad"))
            if rel and t.get("richting") == "PUSH" and t.get("ingeschakeld"):
                job = t.get("laatste_job") or {}
                extern["cloud_sync"].append(
                    {
                        "id": t.get("id"),
                        "omschrijving": t.get("omschrijving"),
                        "provider": t.get("provider"),
                        "is_onedrive": t.get("is_onedrive"),
                        "dekking": rel,
                        "versleuteld": t.get("versleuteld"),
                        "laatste_job_staat": job.get("staat"),
                        "laatste_job_beeindigd": job.get("beeindigd"),
                        "leeftijd_uren": _age_hours(job.get("beeindigd"), inp.now),
                    }
                )
    else:
        reasons.append(f"cloud_sync:{inp.cloudsync.get('reason_code')}")
    if _ok(inp.replication):
        for t in inp.replication.get("data") or []:
            srcs = [str(s) for s in t.get("bron_datasets") or []]
            if (
                t.get("richting") == "PUSH"
                and t.get("ingeschakeld")
                and any(name == s or name.startswith(s + "/") for s in srcs)
            ):
                extern["replicatie"].append(
                    {
                        "id": t.get("id"),
                        "naam": t.get("naam"),
                        "laatste_staat": t.get("laatste_staat"),
                        "laatste_run": t.get("laatste_run"),
                    }
                )
    else:
        reasons.append(f"replicatie:{inp.replication.get('reason_code')}")
    succeeded = [c for c in extern["cloud_sync"] if c["laatste_job_staat"] == "SUCCESS"] + [
        r for r in extern["replicatie"] if r["laatste_staat"] in ("FINISHED", "SUCCESS")
    ]
    if extern["cloud_sync"] or extern["replicatie"]:
        extern["status"] = "gedekt" if succeeded else "laatste_run_niet_geslaagd"
    elif reasons:
        extern["status"] = "unknown"
    else:
        extern["status"] = "niet_gedekt"
    extern["onbekende_bronnen"] = reasons
    extern["onedrive_gedetecteerd"] = any(c.get("is_onedrive") for c in extern["cloud_sync"])
    test = _restore_for(None, name, inp.restore_tests)
    if test and test.get("resultaat") == "geslaagd":
        extern["herstelgarantie"] = True
        extern["opmerking"] = "Herstel aangetoond door een geslaagde hersteltest."
    return {
        "dataset": name,
        "pool": ds.get("pool"),
        "mountpoint": ds.get("mountpoint"),
        "apps": apps_by_ds.get(name, []),
        "lokaal_snapshot": lokaal,
        "extern": extern,
        "laatste_hersteltest": test,
    }


def _aggregate(statuses: list[str]) -> str:
    if not statuses:
        return "unknown"
    if any(s == "unknown" for s in statuses):
        return "unknown"
    if all(s == "gedekt" for s in statuses):
        return "gedekt"
    if any(s == "gedekt" for s in statuses):
        return "gedeeltelijk"
    return "niet_gedekt"


def _db_export(app_id: str, inp: CoverageInputs) -> dict[str, Any]:
    if app_id == APP_ID:
        b = inp.self_backup
        if not b:
            return {"status": "ontbreekt", "bron": "pg_dump (ingebouwde database)", "reason_code": "no_verified_backup"}
        finished: datetime = b["finished_at"]
        age = (inp.now - finished).total_seconds()
        return {
            "status": "geverifieerd" if age <= inp.self_backup_max_age_seconds else "verouderd",
            "bron": "pg_dump (ingebouwde database), geverifieerd met pg_restore --list + SHA-256",
            "reason_code": None,
            "laatste": iso(finished),
            "leeftijd_uren": round(age / 3600, 2),
            "sha256": b.get("sha256"),
            "backup_id": b.get("id"),
        }
    reason = "connector_not_queried" if app_id in inp.enrolled_apps else "capability_unavailable"
    return {
        "status": "unknown",
        "bron": "connector-capability van de app",
        "reason_code": reason,
        "melding": "Geen app-consistente export bekend: de connector van deze app is nog niet gekoppeld of biedt "
        "geen export-capability. Een snapshot alleen telt niet als volledige app-back-up.",
    }


def compute(inp: CoverageInputs) -> dict[str, Any]:
    ds_list: list[dict[str, Any]] = list(inp.datasets.get("data") or []) if _ok(inp.datasets) else []
    mounts = [(str(d["mountpoint"]), str(d["naam"])) for d in ds_list if d.get("mountpoint")]
    by_name = {str(d["naam"]): d for d in ds_list}
    apps: list[dict[str, Any]] = list(inp.apps.get("data") or []) if _ok(inp.apps) else []

    apps_by_ds: dict[str, list[str]] = {}
    app_datasets: dict[str, list[str]] = {}
    for a in apps:
        dsets: list[str] = []
        for m in a.get("opslag") or []:
            src = m.get("bron")
            if not src:
                continue
            found = _dataset_for_path(str(src), mounts)
            if found and found not in dsets:
                dsets.append(found)
        app_datasets[str(a["naam"])] = dsets
        for d in dsets:
            apps_by_ds.setdefault(d, []).append(str(a["naam"]))

    relevant = sorted(set(apps_by_ds) | {d for d in inp.extra_datasets if d in by_name})
    datasets_cov = [dataset_coverage(by_name[d], inp, apps_by_ds) for d in relevant]
    ds_cov = {c["dataset"]: c for c in datasets_cov}

    app_rows: list[dict[str, Any]] = []
    for a in apps:
        name = str(a["naam"])
        app_key = str(a.get("herkend_als") or name)
        dsets = app_datasets.get(name, [])
        lokaal = _aggregate([ds_cov[d]["lokaal_snapshot"]["status"] for d in dsets]) if dsets else "unknown"
        extern = (
            _aggregate(
                [
                    ds_cov[d]["extern"]["status"]
                    if ds_cov[d]["extern"]["status"] != "laatste_run_niet_geslaagd"
                    else "niet_gedekt"
                    for d in dsets
                ]
            )
            if dsets
            else "unknown"
        )
        db_export = _db_export(app_key, inp)
        test = _restore_for(app_key, None, inp.restore_tests) or _restore_for(name, None, inp.restore_tests)
        redenen: list[str] = []
        if not dsets:
            redenen.append("Geen dataset van deze app herkend (opslag/mounts onbekend).")
        if db_export["status"] != "geverifieerd":
            redenen.append("Geen geverifieerde app-consistente database-export.")
        if lokaal != "gedekt" and extern != "gedekt":
            redenen.append("Datasets niet volledig gedekt door snapshots of externe kopie.")
        volledig = db_export["status"] == "geverifieerd" and (lokaal == "gedekt" or extern == "gedekt")

        rpo = inp.rpo_rto.get(app_key) or inp.rpo_rto.get(name)
        ages: list[float] = []
        for d in dsets:
            age = ds_cov[d]["lokaal_snapshot"].get("leeftijd_uren")
            if isinstance(age, int | float):
                ages.append(float(age))
        if db_export.get("status") == "geverifieerd" and isinstance(db_export.get("leeftijd_uren"), int | float):
            ages.append(float(db_export["leeftijd_uren"]))
        gemeten = min(ages) if ages else None
        if rpo is None:
            rpo_status = "unknown"
            rpo_reden = "Geen RPO/RTO vastgelegd in D16 voor deze app."
        elif gemeten is None:
            rpo_status, rpo_reden = "unknown", "Geen meetbaar herstelpunt."
        else:
            rpo_status = "binnen" if gemeten <= rpo["rpo_uren"] else "overschreden"
            rpo_reden = ""
        rto_gemeten = test.get("duur_minuten") if test and test.get("resultaat") == "geslaagd" else None
        if rpo is None or rto_gemeten is None:
            rto_status = "unknown"
        else:
            rto_status = "binnen" if rto_gemeten / 60 <= rpo["rto_uren"] else "overschreden"
        app_rows.append(
            {
                "app": name,
                "herkend_als": a.get("herkend_als"),
                "datasets": dsets,
                "lokaal_snapshot": lokaal,
                "extern": extern,
                "extern_herstelgarantie": any(ds_cov[d]["extern"]["herstelgarantie"] for d in dsets),
                "db_export": db_export,
                "laatste_hersteltest": test,
                "volledige_appbackup": volledig,
                "redenen": redenen,
                "rpo_rto": {
                    "bron": "D16" if rpo else None,
                    "rpo_uren": rpo["rpo_uren"] if rpo else None,
                    "rto_uren": rpo["rto_uren"] if rpo else None,
                    "gemeten_leeftijd_herstelpunt_uren": gemeten,
                    "rpo_status": rpo_status,
                    "rpo_reden": rpo_reden,
                    "gemeten_hersteltijd_minuten": rto_gemeten,
                    "rto_status": rto_status,
                },
            }
        )

    # De Hub zelf staat altijd in het rapport (eigen database), ook als TrueNAS onbekend is.
    if not any((r["herkend_als"] or r["app"]) == APP_ID for r in app_rows):
        db_export = _db_export(APP_ID, inp)
        rpo = inp.rpo_rto.get(APP_ID)
        age = db_export.get("leeftijd_uren") if db_export["status"] == "geverifieerd" else None
        app_rows.append(
            {
                "app": APP_ID,
                "herkend_als": APP_ID,
                "datasets": [],
                "lokaal_snapshot": "unknown",
                "extern": "unknown",
                "extern_herstelgarantie": False,
                "db_export": db_export,
                "laatste_hersteltest": _restore_for(APP_ID, None, inp.restore_tests),
                "volledige_appbackup": False,
                "redenen": ["Dataset van de Hub nog niet in de TrueNAS-inventaris gevonden; snapshots onbekend."],
                "rpo_rto": {
                    "bron": "D16" if rpo else None,
                    "rpo_uren": rpo["rpo_uren"] if rpo else None,
                    "rto_uren": rpo["rto_uren"] if rpo else None,
                    "gemeten_leeftijd_herstelpunt_uren": age,
                    "rpo_status": "unknown"
                    if rpo is None or age is None
                    else ("binnen" if age <= rpo["rpo_uren"] else "overschreden"),
                    "rpo_reden": "",
                    "gemeten_hersteltijd_minuten": None,
                    "rto_status": "unknown",
                },
            }
        )

    bronnen = {
        k: {
            "status": s.get("status"),
            "reason_code": s.get("reason_code"),
            "observed_at": s.get("observed_at"),
            "verouderd": s.get("verouderd"),
        }
        for k, s in (
            ("apps", inp.apps),
            ("datasets", inp.datasets),
            ("snapshot_tasks", inp.snapshot_tasks),
            ("latest_snapshots", inp.latest_snapshots),
            ("cloudsync", inp.cloudsync),
            ("replication", inp.replication),
        )
    }
    return {
        "apps": sorted(app_rows, key=lambda r: str(r["app"])),
        "datasets": datasets_cov,
        "bronnen": bronnen,
        "opmerking": SYNC_IS_GEEN_GARANTIE + " Een snapshot zonder app-consistente database-export telt niet als "
        "volledige app-back-up.",
        "afgeleid_op": iso(inp.now),
    }


def snapshot_policy_proposal(inp: CoverageInputs, coverage: dict[str, Any]) -> dict[str, Any]:
    """Voorstel; er wordt niets toegepast. Toepassen gebeurt pas via de executor (fase P2) na goedkeuring."""
    pools = {str(p["naam"]): p for p in (inp.pools.get("data") or [])} if _ok(inp.pools) else {}
    voorstellen = []
    waarschuwingen = []
    for ds in coverage["datasets"]:
        if ds["lokaal_snapshot"]["status"] == "gedekt":
            continue
        rpos = [inp.rpo_rto[a]["rpo_uren"] for a in ds["apps"] if a in inp.rpo_rto]
        rpo = min(rpos) if rpos else None
        if rpo is not None and rpo <= 1:
            schema, bewaren, frequentie = (
                {"minute": "0", "hour": "*", "dom": "*", "month": "*", "dow": "*"},
                {"waarde": 2, "eenheid": "WEEK"},
                "elk uur",
            )
        else:
            schema, bewaren, frequentie = (
                {"minute": "0", "hour": "3", "dom": "*", "month": "*", "dow": "*"},
                {"waarde": 30, "eenheid": "DAY"},
                "dagelijks",
            )
        voorstellen.append(
            {
                "dataset": ds["dataset"],
                "apps": ds["apps"],
                "reden": "Geen ingeschakelde snapshot-taak dekt deze dataset."
                if ds["lokaal_snapshot"]["status"] == "niet_gedekt"
                else "Snapshotdekking onbekend.",
                "voorstel": {
                    "recursief": True,
                    "schema": schema,
                    "bewaartermijn": bewaren,
                    "frequentie": frequentie,
                    "naamschema": "asm-auto-%Y-%m-%d_%H-%M",
                },
                "afgeleid_van_rpo_uren": rpo,
            }
        )
        pool = pools.get(str(ds.get("pool")))
        if pool and isinstance(pool.get("gebruik_pct"), int | float) and pool["gebruik_pct"] >= 80:
            waarschuwingen.append(
                f"Pool {pool['naam']} is {pool['gebruik_pct']}% vol; extra snapshots vergroten het "
                "ruimtegebruik. Stel eerst een ruimtebudget vast."
            )
    return {
        "status": "voorstel",
        "toegepast": False,
        "toepassen_via": "executor na goedkeuring (fase P2); snapshot-taken aanmaken staat nog niet in "
        "executor-allowlist v1",
        "voorstellen": voorstellen,
        "vooraf_snapshot_bij_wijziging": {
            "beleid": "Vóór elke deploy of schema-update een snapshot van de app-datasets (zfs.snapshot.create, R1) "
            "plus een app-consistente database-export.",
            "toepassen_via": "executor (fase P2)",
        },
        "waarschuwingen": waarschuwingen,
        "regel": "Een snapshot zonder app-consistente database-export telt niet als volledige app-back-up.",
        "afgeleid_op": iso(inp.now),
    }
