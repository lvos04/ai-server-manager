"""Healthcheck van de alles-in-één Hub-image: API ready (database, migraties, geheimen) én de web-UI op de app-poort.

Contract 1.3 §2.2 (C1.3-ASM-01): Docker start dit proces in exec-vorm buiten de procesboom van PID 1, zonder "Custom
User" als root. De **eerste** handeling is daarom: bounding set leeg, naar 568:568, no_new_privs; pas daarna wordt er
iets gecontroleerd. Mislukt de wissel, dan exit 1 (rood). ``--controle`` meldt na de wissel Uid, CapEff, CapPrm,
CapAmb, CapBnd en NoNewPrivs (voor de rooktest).
"""

import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rechten import controle_regels, healthcheck_switch  # noqa: E402

if not healthcheck_switch(int(os.environ.get("HUB_UID", "568")), int(os.environ.get("HUB_GID", "568"))):
    print("healthcheck: wisselen naar 568 met no_new_privs mislukt", file=sys.stderr)
    sys.exit(1)
if "--controle" in sys.argv:
    print("\n".join(controle_regels()))
    sys.exit(0)

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
