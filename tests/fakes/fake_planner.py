"""Fake planner van ``jelly-leon-platform`` (alleen tests) volgens contract 1.3 §8.2, zoals hij moet worden.

De echte planner kent ``catalog_binding`` nog niet (``extra=forbid``); deze fake doet wat het contract vraagt: hij
controleert de dienst-JWT van de Hub en de claim ``catalog_request_sha256`` over ``[methode, pad, Idempotency-Key,
body]``, bewaart de binding onveranderd en geeft haar terug bij aanmaken en ophalen.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from asm_policy.canonical import canonical_sha256

from fakes.fake_http import FakeHTTP, Reply, Seen

APP_ID = "jelly-leon-platform"
PREVIEW = "/lifecycle/v1/plans/install/preview"


class FakePlanner(FakeHTTP):
    def __init__(self, public_key: Any, parameters: dict[str, Any]) -> None:
        super().__init__()
        self.public_key = public_key
        self.parameters = parameters  # de vertaalde installatieparameters van de actiestap
        self.plans: dict[str, dict[str, Any]] = {}
        self.rejected: list[str] = []
        self.results: list[dict[str, Any]] = []
        self.ttl = timedelta(minutes=30)

    def _claims(self, seen: Seen) -> dict[str, Any] | None:
        auth = seen.headers.get("authorization", "")
        try:
            claims = jwt.decode(
                auth[7:],
                self.public_key,
                algorithms=["EdDSA"],
                audience=APP_ID,
                issuer="hub",
            )
        except jwt.PyJWTError as exc:
            self.rejected.append(type(exc).__name__)
            return None
        if claims.get("token_use") != "hub_service" or claims.get("sub") != "hub":
            self.rejected.append("token_use")
            return None
        return dict(claims)

    def handle(self, seen: Seen) -> Reply:
        claims = self._claims(seen)
        if claims is None:
            return Reply(401, {"code": "unauthorized", "message": "Nee.", "details": {}})
        if seen.method == "POST" and seen.path == PREVIEW:
            body = json.loads(seen.body)
            key = seen.headers.get("idempotency-key", "")
            if claims.get("catalog_request_sha256") != canonical_sha256(["POST", PREVIEW, key, body]):
                self.rejected.append("catalog_request_sha256")
                return Reply(
                    401,
                    {
                        "code": "unauthorized",
                        "message": "Claim past niet.",
                        "details": {},
                    },
                )
            pid = str(uuid.uuid4())
            stap = {
                "id": "installeren",
                "soort": "actie",
                "voorstel": {
                    "idempotency_key": str(uuid.uuid4()),
                    "action_id": "app.install",
                    "target": {"app_id": body["app_name"]},
                    "parameters": self.parameters,
                    "expected_version": "absent",
                },
            }
            self.plans[pid] = {
                "id": pid,
                "soort": "install",
                "status": "klaar_voor_voorstel",
                "vervallen": False,
                "plan": {
                    "stappen": [stap],
                    "controles_na_installatie": [
                        {
                            "id": "http_bereikbaar",
                            "soort": "http",
                            "beschrijving_nl": "De webinterface antwoordt.",
                        }
                    ],
                },
                "vrijgegeven_stappen": ["installeren"],
                "catalog_binding": body["catalog_binding"],
                "etag": f'"plan-{pid}-v1"',
                "expires_at": (datetime.now(UTC) + self.ttl).isoformat().replace("+00:00", "Z"),
            }
            return Reply(201, self.plans[pid])
        parts = seen.path.split("/")
        if seen.method == "GET" and len(parts) == 5 and parts[4] in self.plans:
            return Reply(200, self.plans[parts[4]])
        if seen.method == "POST" and len(parts) == 8 and parts[4] in self.plans and parts[7] == "result":
            plan = self.plans[parts[4]]
            self.results.append({"plan_id": parts[4], "step": parts[6], **json.loads(seen.body)})
            plan["etag"] = f'"plan-{parts[4]}-v2"'
            plan["vrijgegeven_stappen"] = []
            return Reply(200, {"status": "voltooid"})
        return Reply(404, {"code": "not_found", "message": "Niet gevonden.", "details": {}})
