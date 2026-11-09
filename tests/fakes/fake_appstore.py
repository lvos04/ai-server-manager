"""Fake ``appstore-en-fork`` (alleen tests): ``GET /catalog/v1/entries`` zoals in zijn OpenAPI, met echte controle van
de dienst-JWT van de Hub (contract §4.3: EdDSA, ``aud``, ``token_use: hub_service``, ``sub: hub``,
``roles: ["service"]``, ``service_id``)."""

from __future__ import annotations

from typing import Any

import jwt

from fakes.fake_http import FakeHTTP, Reply, Seen

APP_ID = "appstore-en-fork"


def entry(app_id: str, name: str, *, version: str = "1.0.0", install_method: str = "custom_app") -> dict[str, Any]:
    return {
        "app_id": app_id,
        "name": name,
        "category": "media",
        "owner_repo": f"lvos04/{app_id}",
        "install_method": install_method,
        "status": "valid",
        "etag": '"1"',
        "source": None,
        "latest_version": {"version": version, "manifest_sha256": "a" * 64, "valid": True},
        "description_nl": None,
        "updated_at": "2026-11-09T12:00:00Z",
        "created_at": "2026-11-09T12:00:00Z",
    }


class FakeAppstore(FakeHTTP):
    def __init__(self, public_key: Any, service_id: str | None = None) -> None:
        super().__init__()
        self.public_key = public_key
        self.service_id = service_id
        self.entries: list[dict[str, Any]] = []
        self.page_size = 200
        self.rejected: list[str] = []

    def _auth(self, seen: Seen) -> str | None:
        auth = seen.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            return "geen_bearer"
        try:
            claims = jwt.decode(auth[7:], self.public_key, algorithms=["EdDSA"], audience=APP_ID, issuer="hub")
        except jwt.PyJWTError as exc:
            return f"ongeldig:{type(exc).__name__}"
        if claims.get("token_use") != "hub_service" or claims.get("sub") != "hub" or claims.get("roles") != ["service"]:
            return "token_use_invalid"
        if self.service_id is not None and claims.get("service_id") != self.service_id:
            return "service_id"
        return None

    def handle(self, seen: Seen) -> Reply:
        if seen.path != "/catalog/v1/entries" or seen.method != "GET":
            return Reply(404, {"code": "not_found", "message": "Niet gevonden.", "details": {}, "trace_id": "x"})
        problem = self._auth(seen)
        if problem:
            self.rejected.append(problem)
            return Reply(401, {"code": "unauthorized", "message": "Nee.", "details": {"reason": problem}})
        start = int((seen.query.get("cursor") or ["0"])[0])
        limit = min(int((seen.query.get("limit") or ["50"])[0]), self.page_size)
        page = self.entries[start : start + limit]
        nxt = str(start + limit) if start + limit < len(self.entries) else None
        return Reply(200, {"items": page, "next_cursor": nxt, "observed_at": "2026-11-09T12:00:00Z"})
