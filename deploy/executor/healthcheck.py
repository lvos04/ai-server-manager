"""Healthcheck van de executor-image."""

import os
import sys
import urllib.request

port = os.environ.get("EXECUTOR_PORT", "30410")
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/readyz", timeout=6) as r:  # noqa: S310 — localhost
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
