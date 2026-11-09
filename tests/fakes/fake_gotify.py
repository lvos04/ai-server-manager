"""Fake Gotify (alleen tests), naar de routes van ``gotify/server`` v3.1.1: ``POST /message`` met het
applicatietoken in ``X-Gotify-Key`` of ``?token=``, ``GET /version`` en ``GET /health``. Ongeldig token → 401 zoals
Gotify."""

from __future__ import annotations

import json
from typing import Any

from fakes.fake_http import FakeHTTP, Reply, Seen


class FakeGotify(FakeHTTP):
    def __init__(self, tokens: set[str] | None = None, version: str = "3.1.1") -> None:
        super().__init__()
        self.tokens = tokens if tokens is not None else {"AppTokenHub123"}
        self.version = version
        self.messages: list[dict[str, Any]] = []

    def handle(self, seen: Seen) -> Reply:
        if seen.path == "/version" and seen.method == "GET":
            return Reply(200, {"version": self.version, "commit": "test", "buildDate": "2026-11-01T00:00:00Z"})
        if seen.path == "/health" and seen.method in ("GET", "HEAD"):
            return Reply(200, {"health": "green", "database": "green"})
        if seen.path == "/message" and seen.method == "POST":
            # Gotify accepteert het applicatietoken als header of als query (?token=…, zoals Uptime Kuma het stuurt).
            token = seen.headers.get("x-gotify-key") or (seen.query.get("token") or [None])[0]
            if token not in self.tokens:
                return Reply(
                    401,
                    {
                        "error": "Unauthorized",
                        "errorCode": 401,
                        "errorDescription": "you need to provide a valid token",
                    },
                )
            body = json.loads(seen.body or b"{}")
            if not body.get("message"):
                return Reply(400, {"error": "Bad Request", "errorCode": 400, "errorDescription": "message required"})
            msg = {
                "id": len(self.messages) + 1,
                "appid": 1,
                "title": body.get("title"),
                "message": body["message"],
                "priority": body.get("priority"),
                "date": "2026-11-09T12:00:00Z",
            }
            self.messages.append(msg)
            return Reply(200, msg)
        return Reply(404, {"error": "Not Found", "errorCode": 404})
