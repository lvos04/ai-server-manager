"""Rechtenmatrix over ÁLLE routes van de Hub-API (contract §4; 03_RISICO_AUTONOMIE: autorisatie op elke route).

- Elke route moet in ``MATRIX`` staan: een nieuwe route zonder expliciete rechtenkeuze laat deze test falen.
- Zonder aanmelding → 401 ``unauthorized`` op elke niet-publieke route (nooit "open bij fout").
- Een rol onder het minimum → 403 ``forbidden``; een service-token op een gebruikersroute → 403; een gebruikerssessie
  op een dienstroute → 401.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from conftest import enroll_body, idem, login_as, make_user

pytestmark = pytest.mark.integration

PUBLIC = "public"
SERVICE = "service"
VIEWER_OR_SERVICE = "viewer_or_service"
RANK = {"kind": 0, "viewer": 1, "operator": 2, "admin": 3}

MATRIX: dict[tuple[str, str], str] = {
    ("GET", "/healthz"): PUBLIC,
    ("GET", "/readyz"): PUBLIC,
    ("GET", "/"): PUBLIC,
    ("GET", "/api/v1/setup/status"): PUBLIC,
    ("POST", "/api/v1/setup/admin"): PUBLIC,
    ("POST", "/api/v1/auth/login"): PUBLIC,
    ("GET", "/api/v1/auth/jwks"): PUBLIC,
    ("GET", "/api/v1/auth/key-rotations"): PUBLIC,
    ("POST", "/api/v1/auth/break-glass/login"): PUBLIC,
    ("GET", "/api/v1/auth/keyset"): "viewer",
    ("GET", "/api/v1/auth/break-glass"): "admin",
    ("POST", "/api/v1/auth/break-glass/setup"): "admin",
    ("POST", "/api/v1/auth/break-glass/rotate"): "admin",
    ("POST", "/api/v1/auth/break-glass/confirm"): "admin",
    ("POST", "/api/v1/auth/break-glass/selftest"): "admin",
    ("POST", "/api/v1/services/enroll"): PUBLIC,
    ("POST", "/api/v1/auth/logout"): "kind",
    ("GET", "/api/v1/auth/me"): "kind",
    ("POST", "/api/v1/auth/password"): "kind",
    ("POST", "/api/v1/auth/service-jwt"): "kind",
    ("GET", "/api/v1/auth/sessions"): "kind",
    ("POST", "/api/v1/auth/sessions/{session_id}/revoke"): "kind",
    ("GET", "/api/v1/audit"): "admin",
    ("GET", "/api/v1/apps"): "viewer",
    ("POST", "/api/v1/apps/discover"): "operator",
    ("GET", "/api/v1/apps/{app_uuid}"): "viewer",
    ("GET", "/api/v1/monitoring/sources"): "operator",
    ("POST", "/api/v1/monitoring/sources"): "admin",
    ("GET", "/api/v1/monitoring/sources/{source_id}"): "operator",
    ("PATCH", "/api/v1/monitoring/sources/{source_id}"): "admin",
    ("POST", "/api/v1/monitoring/sources/{source_id}/test"): "admin",
    ("POST", "/api/v1/monitoring/poll"): "operator",
    ("GET", "/api/v1/monitoring/health"): "viewer",
    ("POST", "/api/v1/monitoring/heartbeat"): SERVICE,
    ("GET", "/api/v1/monitoring/status"): "viewer",
    ("GET", "/api/v1/monitoring/coverage"): "viewer",
    ("GET", "/api/v1/observability/nas"): "viewer",
    ("GET", "/api/v1/metrics/series"): "viewer",
    ("GET", "/api/v1/metrics/query"): "viewer",
    ("GET", "/api/v1/alerts"): "viewer",
    ("POST", "/api/v1/alerts/{alert_id}/snooze"): "operator",
    ("GET", "/api/v1/alerts/rules"): "viewer",
    ("POST", "/api/v1/alerts/rules"): "admin",
    ("PATCH", "/api/v1/alerts/rules/{rule_id}"): "admin",
    ("POST", "/api/v1/alerts/rules/{rule_id}/snooze"): "operator",
    ("GET", "/api/v1/notifications"): "operator",
    ("POST", "/api/v1/notifications"): "operator",
    ("GET", "/api/v1/notifications/channels"): "operator",
    ("POST", "/api/v1/notifications/channels"): "admin",
    ("PATCH", "/api/v1/notifications/channels/{channel_id}"): "admin",
    ("POST", "/api/v1/notifications/channels/{channel_id}/test"): "admin",
    ("GET", "/api/v1/users"): "admin",
    ("POST", "/api/v1/users"): "admin",
    ("PATCH", "/api/v1/users/{user_id}"): "admin",
    ("GET", "/api/v1/backups/coverage"): "viewer",
    ("GET", "/api/v1/backups/restore-tests"): "viewer",
    ("POST", "/api/v1/backups/restore-tests"): "admin",
    ("GET", "/api/v1/backups/self"): "viewer",
    ("POST", "/api/v1/backups/self"): "admin",
    ("POST", "/api/v1/backups/self/{backup_id}/verify"): "operator",
    ("GET", "/api/v1/backups/snapshot-policy/proposal"): "viewer",
    ("GET", "/api/v1/decisions"): "viewer",
    ("GET", "/api/v1/decisions/{decision_id}"): "viewer",
    ("POST", "/api/v1/decisions/{decision_id}/bewijs"): "admin",
    ("POST", "/api/v1/decisions/{decision_id}/meting"): "operator",
    ("POST", "/api/v1/decisions/{decision_id}/status"): "admin",
    ("PUT", "/api/v1/decisions/{decision_id}/waarde"): "admin",
    ("GET", "/api/v1/events"): "viewer",
    ("POST", "/api/v1/events/inbox"): SERVICE,
    ("GET", "/api/v1/gates"): "viewer",
    ("GET", "/api/v1/gates/{gate_id}"): "viewer",
    ("GET", "/api/v1/inventory"): "viewer",
    ("POST", "/api/v1/inventory/refresh"): "operator",
    ("GET", "/api/v1/inventory/{soort}"): "viewer",
    ("GET", "/api/v1/jobs"): "viewer",
    ("GET", "/api/v1/jobs/{job_id}"): "viewer",
    ("GET", "/api/v1/registry/services"): "viewer",
    ("GET", "/api/v1/services"): "operator",
    ("POST", "/api/v1/services/enrollment-tokens"): "admin",
    ("POST", "/api/v1/services/pairing-codes"): "admin",
    ("POST", "/api/v1/services/self/rotate"): SERVICE,
    ("GET", "/api/v1/services/self"): SERVICE,
    ("POST", "/api/v1/services/{service_id}/unlink"): "admin",
    ("PUT", "/api/v1/services/{service_id}/truenas-app"): "admin",
    ("POST", "/api/v1/services/{service_id}/revoke"): "admin",
    ("POST", "/api/v1/services/{service_id}/rotate"): "admin",
    ("GET", "/api/v1/truenas"): "viewer",
    ("PUT", "/api/v1/truenas/api-key"): "admin",
    ("POST", "/api/v1/truenas/test"): "operator",
    ("POST", "/api/v1/truenas/tls/trust"): "admin",
    ("POST", "/api/v1/truenas/tls/untrust"): "admin",
    ("GET", "/connector/v1/discover"): VIEWER_OR_SERVICE,
    ("GET", "/connector/v1/health"): VIEWER_OR_SERVICE,
    ("GET", "/connector/v1/items"): VIEWER_OR_SERVICE,
    ("GET", "/connector/v1/events"): VIEWER_OR_SERVICE,
    ("GET", "/connector/v1/evidence/{evidence_id}"): VIEWER_OR_SERVICE,
    ("POST", "/connector/v1/propose"): VIEWER_OR_SERVICE,
    ("POST", "/connector/v1/apply"): VIEWER_OR_SERVICE,
    ("POST", "/connector/v1/rollback"): VIEWER_OR_SERVICE,
}

PATH_VALUES = {
    "decision_id": "D03",
    "soort": "pools",
    "gate_id": "deploy",
    "evidence_id": "onbekend",
}


def _routes(app: Any) -> set[tuple[str, str]]:
    """Alle routes uit het OpenAPI-schema (bron van waarheid, ook voor geneste routers) plus de statuspagina ``/``
    (``include_in_schema=False``). Ingebouwde documentatieroutes van FastAPI tellen niet mee."""
    out = {(m.upper(), path) for path, ops in app.openapi()["paths"].items() for m in ops}
    out.add(("GET", "/"))
    return out


def test_geen_verborgen_routes_buiten_het_schema(client: Any) -> None:
    """Routes die niet in het schema staan zouden de matrix ontlopen: alleen ``/`` en de docs zijn verborgen."""
    for path in ("/", "/api/openapi.json", "/api/docs"):
        assert client.get(path).status_code == 200
    assert client.get("/docs").status_code == 404 and client.get("/redoc").status_code == 404


def _url(path: str) -> str:
    for name, value in PATH_VALUES.items():
        path = path.replace("{" + name + "}", value)
    while "{" in path:
        start, end = path.index("{"), path.index("}")
        path = path[:start] + str(uuid.uuid4()) + path[end + 1 :]
    return path


def _call(client: Any, method: str, path: str, headers: dict[str, str] | None = None) -> Any:
    h = {**idem(), **(headers or {})}
    kwargs: dict[str, Any] = {"headers": h}
    if method in ("POST", "PUT", "PATCH"):
        kwargs["json"] = {}
    if path == "/connector/v1/items":
        path += "?type=decision"
    return client.request(method, _url(path), **kwargs)


def test_elke_route_staat_in_de_rechtenmatrix(app: Any) -> None:
    routes = _routes(app)
    missing = sorted(routes - set(MATRIX))
    stale = sorted(set(MATRIX) - routes)
    assert not missing, f"routes zonder expliciete rechtenkeuze in MATRIX: {missing}"
    assert not stale, f"MATRIX noemt routes die niet (meer) bestaan: {stale}"


def test_zonder_aanmelding_401_op_elke_niet_publieke_route(client: Any) -> None:
    for (method, path), need in sorted(MATRIX.items()):
        if need == PUBLIC:
            continue
        r = _call(client, method, path)
        assert r.status_code == 401, f"{method} {path}: {r.status_code} {r.text[:200]}"
        body = r.json()
        assert body["code"] == "unauthorized" and body["trace_id"], f"{method} {path}: {body}"
    # Een vervalst/ingetrokken service-token opent ook niets.
    for (method, path), need in sorted(MATRIX.items()):
        if need == PUBLIC:
            continue
        r = _call(client, method, path, {"Authorization": "Bearer svc_vervalst-token"})
        assert r.status_code == 401, f"{method} {path} met vervalst token: {r.status_code}"


def _service_token(admin: Any) -> str:
    r = admin.post("/api/v1/services/enrollment-tokens", json={"app_id": "home-control-hub"})
    assert r.status_code == 201, r.text
    r = admin.post(
        "/api/v1/services/enroll",
        json=enroll_body("home-control-hub", token=r.json()["enrollment_token"]),
    )
    assert r.status_code == 200, r.text
    return str(r.json()["service_token"])


def test_rol_onder_minimum_krijgt_403_en_dienst_versus_gebruiker(admin: Any, app: Any) -> None:
    for role in ("kind", "viewer", "operator"):
        make_user(admin, f"rol-{role}", role)
    clients = {role: login_as(app, f"rol-{role}") for role in ("kind", "viewer", "operator")}
    clients["admin"] = admin
    svc_headers = {"Authorization": f"Bearer {_service_token(admin)}"}

    for (method, path), need in sorted(MATRIX.items()):
        if need == PUBLIC:
            continue
        for role, c in clients.items():
            if need == SERVICE:
                denied, expect = True, 401  # gebruikerssessie op een dienstroute
            elif need == VIEWER_OR_SERVICE:
                denied, expect = RANK[role] < RANK["viewer"], 403
            else:
                denied, expect = RANK[role] < RANK[need], 403
            if not denied:
                continue
            r = _call(c, method, path)
            assert r.status_code == expect, f"{role} → {method} {path}: {r.status_code} {r.text[:200]}"
            assert r.json()["code"] in ("forbidden", "unauthorized")
        if need not in (SERVICE, VIEWER_OR_SERVICE):
            # Een service-token is geen gebruiker: gebruikersroutes (ook 'kind') blijven dicht.
            r = _call(admin, method, path, svc_headers)
            assert r.status_code == 403, f"service-token → {method} {path}: {r.status_code} {r.text[:200]}"

    # Positieve controle (alleen lezen, zonder bijwerkingen): de minimale rol komt erdoor.
    for (method, path), need in sorted(MATRIX.items()):
        if method != "GET" or need in (PUBLIC, SERVICE):
            continue
        role = "viewer" if need == VIEWER_OR_SERVICE else need
        r = _call(clients[role], method, path)
        assert r.status_code not in (401, 403), f"{role} → {method} {path}: {r.status_code} {r.text[:200]}"
    for path in ("/connector/v1/discover", "/connector/v1/health", "/connector/v1/items"):
        assert _call(admin, "GET", path, svc_headers).status_code == 200
