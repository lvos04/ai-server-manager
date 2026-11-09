"""Weergave van jobs (gedeeld door inventaris- en back-uproutes)."""

from __future__ import annotations

from typing import Any

from hub.models import Job
from hub.timeutil import iso


def job_dict(job: Job) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "soort": job.kind,
        "status": job.status,
        "aangevraagd_door": job.requested_by,
        "aangemaakt": iso(job.created_at),
        "gestart": iso(job.started_at),
        "klaar": iso(job.finished_at),
        "resultaat": job.result,
    }
