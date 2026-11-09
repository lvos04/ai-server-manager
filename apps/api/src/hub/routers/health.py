"""``/healthz``, ``/readyz`` (zonder auth, zonder geheimen) en een kleine Nederlandse statuspagina op ``/``."""

from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select, text

from hub import APP_ID, __version__
from hub.deps import DB, SettingsDep
from hub.firststart import setup_pending
from hub.migrations import current_revision, head_revision
from hub.models import User

router = APIRouter(tags=["gezondheid"])


@router.get("/healthz", summary="Proces leeft")
def healthz() -> dict[str, str]:
    return {"status": "ok", "app": APP_ID, "version": __version__}


@router.get("/readyz", summary="Afhankelijkheden in orde (database, migraties, geheimen)")
def readyz(request: Request, db: DB, settings: SettingsDep) -> JSONResponse:
    checks: list[dict[str, Any]] = []
    ok = True
    try:
        db.execute(text("SELECT 1"))
        checks.append({"name": "database", "status": "ok"})
    except Exception:
        checks.append({"name": "database", "status": "down"})
        ok = False
    if ok:
        cur, head = current_revision(db), head_revision()
        good = cur is not None and cur == head
        checks.append(
            {"name": "migraties", "status": "ok" if good else "down", "detail": "op head" if good else "niet op head"}
        )
        ok = ok and good
    secrets_ok = all(
        (settings.secrets_dir / n).exists() for n in ("vault.key", "jwt-signing.ed25519", "policy-signing.ed25519")
    )
    checks.append({"name": "geheimen", "status": "ok" if secrets_ok else "down"})
    ok = ok and secrets_ok
    return JSONResponse({"status": "ready" if ok else "not_ready", "checks": checks}, status_code=200 if ok else 503)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def status_page(db: DB, settings: SettingsDep) -> HTMLResponse:
    try:
        has_admin = db.scalars(select(User.id).where(User.role == "admin")).first() is not None
        db_status = "bereikbaar"
    except Exception:
        has_admin, db_status = False, "niet bereikbaar"
    pending = setup_pending(settings.secrets_dir) and not has_admin
    setup = (
        "<p><strong>Eerste installatie:</strong> de eenmalige <em>setupcode</em> staat in de app-log "
        "(TrueNAS → Apps → ai-server-manager → Logs). Je vult hem in de setup-wizard van de web-UI in "
        "(of via <code>POST /api/v1/setup/admin</code>).</p>"
        if pending
        else "<p>Setup is afgerond; meld je aan in de web-UI.</p>"
    )
    html = f"""<!doctype html><html lang="nl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>AI Server Manager — Hub</title>
<style>body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}}
code{{background:#f2f2f2;padding:0 .25rem}}</style></head><body>
<h1>AI Server Manager — Hub</h1>
<p>Versie {escape(__version__)} · database {escape(db_status)}</p>
{setup}
<p>De volledige web-UI volgt in een volgende versie. API-documentatie: <a href="/api/docs">/api/docs</a>.</p>
<p>Gezondheid: <a href="/healthz">/healthz</a> · <a href="/readyz">/readyz</a></p>
</body></html>"""
    return HTMLResponse(html)
