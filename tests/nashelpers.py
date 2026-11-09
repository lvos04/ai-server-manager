"""Gedeelde stappen voor dienst-E2E tegen de fake TrueNAS: D03 invullen, alleen-lezen-key, certificaat vertrouwen en
de inventaris vernieuwen (job + worker). Alleen tests; nooit echte NAS-gegevens."""

from __future__ import annotations

from typing import Any

from conftest import idem

READONLY_KEY = "readonly-test-key-0123456789"


def connect(admin: Any, nas: Any, key: str = READONLY_KEY) -> None:
    r = admin.put(
        "/api/v1/decisions/D03/waarde",
        json={"waarde": {"nas_adres": "127.0.0.1", "https_poort": nas.port}},
        headers=idem(),
    )
    assert r.status_code == 200, r.text
    r = admin.put("/api/v1/truenas/api-key", json={"api_key": key}, headers=idem())
    assert r.status_code == 200, r.text
    r = admin.post("/api/v1/truenas/test", headers=idem())
    assert r.status_code == 200 and r.json()["reason_code"] == "tls_untrusted", r.text
    fp = r.json()["details"]["fingerprint_weergave"]
    r = admin.post("/api/v1/truenas/tls/trust", json={"fingerprint_sha256": fp}, headers=idem())
    assert r.status_code == 200, r.text


def refresh(admin: Any, worker_once: Any) -> dict[str, Any]:
    r = admin.post("/api/v1/inventory/refresh", headers=idem())
    assert r.status_code == 202, r.text
    done = [j for j in worker_once() if j["kind"] == "inventory_refresh"]
    assert done, "geen inventaris-job uitgevoerd"
    return done[-1]
