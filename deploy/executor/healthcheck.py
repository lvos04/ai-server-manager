"""Healthcheck van de executor-image.

Contract 1.3 §2.2 (C1.3-ASM-01): exec-vorm; als **eerste** handeling bounding set leeg (bij root), naar 568:568 en
no_new_privs; pas daarna ``/readyz``. Mislukt de wissel, dan exit 1. ``--controle`` meldt na de wissel Uid, CapEff,
CapPrm, CapAmb, CapBnd en NoNewPrivs (voor de rooktest).
"""

import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rechten import controle_regels, healthcheck_switch  # noqa: E402

if not healthcheck_switch(568, 568):
    print("healthcheck: wisselen naar 568 met no_new_privs mislukt", file=sys.stderr)
    sys.exit(1)
if "--controle" in sys.argv:
    print("\n".join(controle_regels()))
    sys.exit(0)

port = os.environ.get("EXECUTOR_PORT", "30410")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=6) as r:  # noqa: S310 — localhost
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
