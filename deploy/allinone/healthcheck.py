"""Healthcheck van de alles-in-één Hub-image: de API meldt ready (database bereikbaar, migraties op head, geheimen)."""

import os
import sys
import urllib.request
from pathlib import Path

web = Path("/opt/hub-web/server.js").exists()
port = os.environ.get("HUB_INTERNAL_API_PORT", "8400") if web else os.environ.get("HUB_PORT", "30400")


def ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=6) as resp:  # noqa: S310 — vaste localhost-URL
            return bool(resp.status == 200)
    except Exception:
        return False


checks = [f"http://127.0.0.1:{port}/readyz"]
if web:
    checks.append(f"http://127.0.0.1:{os.environ.get('HUB_PORT', '30400')}/")
sys.exit(0 if all(ok(u) for u in checks) else 1)
