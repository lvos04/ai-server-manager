"""Beoordeel het gecorreleerde incident vóór een eventuele kredietreservering."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from hub.ai.kennis import Kennis
from hub.models import Incident, IncidentEvent


def beoordeel(db: Session, inc: Incident, kennis: Kennis) -> tuple[str, str]:
    bron = kennis.incident
    if inc.status in ("gesnoozed", "opgelost"):
        return inc.status, "Het incident is gesnoozed of opgelost."
    if bron.regel != "geen_regel":
        return bron.regel, bron.hypothese
    # Het eventtype is door de incidentenmotor aan de bron en het domein gebonden.
    # Een logbericht of een tekstveld uit de payload kan geen behandelregel kiezen.
    et = (
        db.scalar(
            select(IncidentEvent.event_type)
            .where(IncidentEvent.incident_id == inc.id, IncidentEvent.soort == "probleem")
            .order_by(IncidentEvent.op.desc(), IncidentEvent.id.desc())
            .limit(1)
        )
        or ""
    )
    if et.endswith(".crashed"):
        return "proces_gecrasht", "De bron meldt een gecrasht proces. Controleer de laatste gebeurtenissen."
    if et == "media.av1.stalled":
        return "av1_stilgevallen", "De AV1-verwerking maakt geen voortgang."
    if kennis.runbook and kennis.runbook.ref.endswith("/schijf_vol"):
        return "opslag", "Controleer de beschikbare opslagruimte met het gekoppelde runbook."
    if inc.soort.startswith("backup."):
        return "backup", "Controleer het laatste geverifieerde herstelpunt."
    if inc.soort.startswith(("auth.", "sso.")):
        return "authenticatie", "Controleer het toegangsincident in het lokale auditspoor."
    return "geen_regel", bron.hypothese
