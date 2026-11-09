"""Healthcheck van de alles-in-één Hub-image: API ready (database, migraties, geheimen) én de web-UI op de app-poort."""

import os
import sys
import urllib.request
from pathlib import Path

web = Path(os.environ.get("HUB_WEB_SERVER", "/opt/hub-web/server/hub-server.mjs")).exists()
port = os.environ.get("HUB_INTERNAL_API_PORT", "8400") if web else os.environ.get("HUB_PORT", "30400")


def ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:  # noqa: S310 — vaste localhost-URL
            return bool(resp.status == 200)
    except Exception:
        return False


checks = [f"http://127.0.0.1:{port}/readyz"]
if web:
    # De web-UI (statische schil) en de doorgang naar de API via dezelfde poort als de gebruiker.
    app_port = os.environ.get("HUB_PORT", "30400")
    checks += [f"http://127.0.0.1:{app_port}/inloggen", f"http://127.0.0.1:{app_port}/healthz"]
sys.exit(0 if all(ok(u) for u in checks) else 1)
