"""Operator-runbooks (B09-006): getypeerde catalogus (alleen lezen) met hash; per incident via de incidentroutes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from hub.deps import Viewer
from hub.errors import HubError
from hub.runbooks.catalogus import BY_ID, RUNBOOKS, runbook_hash, to_dict

router = APIRouter(prefix="/api/v1/runbooks", tags=["incidenten"])


@router.get("", summary="Runbooks per scenario (observeren → isoleren → mitigeren → terugdraaien → bewijs → oorzaak)")
def list_runbooks(_: Viewer) -> dict[str, Any]:
    return {"items": [to_dict(r) for r in RUNBOOKS], "runbook_hash": runbook_hash()}


@router.get("/{runbook_id}", summary="Eén runbook")
def get_runbook(runbook_id: str, _: Viewer) -> dict[str, Any]:
    rb = BY_ID.get(runbook_id)
    if rb is None:
        raise HubError(404, "not_found", "Runbook niet gevonden.")
    return {**to_dict(rb), "runbook_hash": runbook_hash()}
