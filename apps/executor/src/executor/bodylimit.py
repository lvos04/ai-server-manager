"""Harde grens van 1 MiB per verzoek (contract 1.2 §5), vóór routering en authenticatie, ook chunked.

Een te grote ``Content-Length`` wordt direct geweigerd. Anders leest deze ASGI-laag de body (tellend, hooguit 1 MiB in
het geheugen) vóórdat de app iets doet en breekt af met ``413 payload_too_large`` zodra er meer binnenkomt. Zo krijgt
ook een route die de body zelf niet leest, of een verzoek zonder geldige Hub-JWT, altijd 413 (nooit eerst 401/404/405).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_BYTES = 1024 * 1024


async def _no_receive() -> Message:
    return {"type": "http.disconnect"}


def _body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details or {}, "trace_id": str(uuid.uuid4())}


class BodyLimit:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app, self.max_bytes = app, max_bytes

    async def _answer(self, scope: Scope, send: Send, status: int, body: dict[str, Any]) -> None:
        await JSONResponse(body, status_code=status, headers={"Connection": "close"})(scope, _no_receive, send)

    async def _too_large(self, scope: Scope, send: Send) -> None:
        body = _body("payload_too_large", "Het verzoek is te groot (maximaal 1 MiB).", {"max_bytes": self.max_bytes})
        await self._answer(scope, send, 413, body)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for name, value in scope.get("headers") or []:
            if name == b"content-length":
                text = value.decode("latin-1").strip()
                if not text.isdigit():
                    await self._answer(scope, send, 400, _body("bad_request", "Ongeldige Content-Length."))
                    return
                if int(text) > self.max_bytes:
                    await self._too_large(scope, send)
                    return
        chunks: list[bytes] = []
        total, more = 0, True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                # Client is weg vóór de body compleet was: niets uitvoeren, alleen netjes afsluiten.
                await self._answer(scope, send, 400, _body("bad_request", "Verbinding verbroken."))
                return
            part = message.get("body", b"")
            total += len(part)
            if total > self.max_bytes:
                await self._too_large(scope, send)
                return
            chunks.append(part)
            more = bool(message.get("more_body", False))
        buffered: Message = {"type": "http.request", "body": b"".join(chunks), "more_body": False}
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return buffered
            return await receive()  # daarna alleen nog http.disconnect

        await self.app(scope, replay, send)
