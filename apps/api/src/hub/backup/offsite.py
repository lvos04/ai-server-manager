"""Verificatie van de externe (OneDrive-)back-up (B12-004): leest de uploadtaken uit de alleen-lezen inventaris.

De Hub maakt of wijzigt geen opslagdienst; hij leest alleen ``cloudsync.query`` (zonder credential-attributen) en
toetst de taken uit besluit D04. Positieve witte lijst: alleen een ingeschakelde PUSH-taak naar OneDrive met een
laatste job ``SUCCESS`` binnen het venster telt als ``ok``. Al het andere is een probleem (``verouderd``,
``aanmelding_verlopen``, ``mislukt``, ``ontbreekt``) of ``unknown``; alleen ``ok`` houdt de back-upgate open.
Een geslaagde upload is nog steeds geen herstelgarantie (zie :mod:`hub.backup.coverage`).

Een D04-taak koppelt alleen eenduidig (één taak-ID of één omschrijving); per taak bewaart de Hub de laatste
bevestigde storing (:data:`STORINGEN_KEY`) en alleen een LATERE geslaagde upload heft die op. Vrije taaktekst
(omschrijving) gaat nooit naar buiten: alleen ID, staat en tijden.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from hub.timeutil import binnen_venster, iso

# TrueNAS/rclone-meldingen bij een verlopen of ingetrokken OneDrive-aanmelding (Microsoft identity platform).
AANMELDING_PATROON = re.compile(
    r"invalid_grant|unauthori[sz]ed|unauthenticated|expired|verlopen|token|AADSTS\d+|\b401\b|re-?auth|InvalidAuthentication",
    re.IGNORECASE,
)
# Ernstigste eerst; ``ok`` en ``unknown`` zijn geen probleem voor het incident (``unknown`` houdt de gate wel dicht).
PROBLEMEN = ("aanmelding_verlopen", "mislukt", "ontbreekt", "verouderd")
STORINGEN = ("aanmelding_verlopen", "mislukt")  # bevestigde storing van een job: alleen een latere upload heft op
STORINGEN_KEY = "backup.extern.storingen"  # HubSetting: {taak-id: ISO-tijd van de laatste bevestigde storing}


def lees_tijd(waarde: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(waarde).replace("Z", "+00:00")) if waarde else None
    except ValueError:
        return None


def _taak(t: dict[str, Any], now: datetime, max_age_seconds: int, storing: Any = None) -> dict[str, Any]:
    ruw = t.get("laatste_job")
    job: dict[str, Any] = ruw if isinstance(ruw, dict) else {}
    staat, beeindigd, fout = job.get("staat"), job.get("beeindigd"), job.get("fout")
    rij = {"id": t.get("id"), "laatste_job_staat": staat, "beeindigd": beeindigd}  # geen vrije tekst (R-HARDE-EIS-7)
    if not (t.get("ingeschakeld") is True and t.get("richting") == "PUSH" and t.get("is_onedrive") is True):
        return {**rij, "status": "ontbreekt", "reden": "taak_uit_of_geen_onedrive_push"}
    if staat == "SUCCESS" and fout:
        return {**rij, "status": "mislukt", "reden": "tegenstrijdige_jobstatus"}  # SUCCESS mét fout: dicht
    if staat == "SUCCESS":
        klaar, laatste_storing = lees_tijd(beeindigd), lees_tijd(storing)
        if storing is not None and (klaar is None or laatste_storing is None or klaar <= laatste_storing):
            return {**rij, "status": "mislukt", "reden": "geen_upload_na_storing"}
        if klaar is not None and binnen_venster(klaar, now, max_age_seconds):
            return {**rij, "status": "ok", "reden": None}
        return {**rij, "status": "verouderd", "reden": "laatste_upload_te_oud"}
    if staat in ("FAILED", "ERROR", "ABORTED"):
        if fout and AANMELDING_PATROON.search(str(fout)):
            return {**rij, "status": "aanmelding_verlopen", "reden": "aanmelding_verlopen"}
        return {**rij, "status": "mislukt", "reden": "laatste_upload_mislukt"}
    if staat is None:
        return {**rij, "status": "verouderd", "reden": "nooit_geupload"}
    # shortcut: een lopende job (RUNNING/WAITING) verbergt de vorige uitkomst; dan unknown (gate dicht, geen incident).
    # Versie 2: de laatste afgeronde job via core.get_jobs lezen.
    return {**rij, "status": "unknown", "reden": f"job_{str(staat).lower()[:16]}"}


def beoordeel(
    d04: tuple[str, Any] | None,
    cloudsync: dict[str, Any],
    now: datetime,
    max_age_seconds: int,
    storingen: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """``{status, reden, taken, max_leeftijd_s, afgeleid_op}`` voor de taken uit D04; ``storingen`` is per taak-ID de
    laatste bevestigde storing (zie :data:`STORINGEN_KEY`)."""

    def uit(status: str, reden: str | None, taken: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {
            "status": status,
            "reden": reden,
            "taken": taken or [],
            "max_leeftijd_s": max_age_seconds,
            "afgeleid_op": iso(now),
        }

    status, waarde = d04 or ("Open", None)
    if status not in ("Ingevuld", "Getest") or not isinstance(waarde, dict):
        return uit("unknown", "d04_niet_ingevuld")
    if waarde.get("methode") != "truenas_cloud_sync":
        return uit("unknown", "capability_unavailable")  # alleen TrueNAS Cloud Sync is uit te lezen
    if cloudsync.get("status") != "ok":
        return uit("unknown", f"cloudsync_{cloudsync.get('reason_code') or 'onbekend'}")
    alle = [t for t in cloudsync.get("data") or [] if isinstance(t, dict)]
    taken: list[dict[str, Any]] = []
    for naam in waarde.get("taken") or []:
        sleutel = str(naam).strip().lower()
        # Eenduidig of niet (R-HARDE-EIS-3): een tweede taak met dezelfde omschrijving of ID houdt de gate dicht,
        # in elke sorteervolgorde.
        treffers = [
            t
            for t in alle
            if str(t.get("id")) == sleutel or str(t.get("omschrijving") or "").strip().lower() == sleutel
        ]
        if len(treffers) != 1 or treffers[0].get("id") is None:
            reden = "taak_niet_eenduidig" if treffers else "taak_niet_gevonden"
            taken.append({"id": None, "status": "ontbreekt", "reden": reden})  # volgorde = volgorde in D04
        else:
            taken.append(_taak(treffers[0], now, max_age_seconds, (storingen or {}).get(str(treffers[0]["id"]))))
    if not taken:
        return uit("unknown", "geen_taken_in_d04")
    for p in PROBLEMEN:
        if any(t["status"] == p for t in taken):
            return uit(p, next(t["reden"] for t in taken if t["status"] == p), taken)
    if all(t["status"] == "ok" for t in taken):
        return uit("ok", None, taken)
    return uit("unknown", next(t["reden"] for t in taken if t["status"] != "ok"), taken)
