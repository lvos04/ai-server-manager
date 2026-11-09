"""Observability van de NAS (B01-004): live CPU/RAM/ARC/GPU/schijven/pools/netwerk in één antwoord, met bron en
'laatst bijgewerkt' per metriek. Alleen TrueNAS (D10: de mini-pc hoort niet bij het platform)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from hub.deps import DB, SettingsDep, Viewer
from hub.monitoring.observability import nas_view

router = APIRouter(prefix="/api/v1/observability", tags=["observability"])


@router.get("/nas", summary="Live NAS-metingen met bron en observed_at; verouderd of zonder bron → unknown")
def nas(db: DB, settings: SettingsDep, _: Viewer) -> dict[str, Any]:
    return nas_view(db, settings)
