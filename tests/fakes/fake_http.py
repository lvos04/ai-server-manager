"""Basis voor in-repo HTTP-fakes (alleen tests): een draadgebaseerde server op ``127.0.0.1`` met storingsinjectie.

Elke fake legt alle verzoeken vast (methode, pad, headers zonder geheimen in de tests te tonen) en kan:
``offline()`` (poort dicht), een vaste status teruggeven (``force_status``), vertragen (``delay``) of een redirect geven
(``redirect_to``). Zo testen we dat de Hub storingen nooit als succes ziet.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit


@dataclass
class Seen:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: bytes


@dataclass
class Reply:
    status: int
    body: Any = None  # dict/list → JSON; str → tekst; bytes → as-is
    headers: dict[str, str] = field(default_factory=dict)


class FakeHTTP:
    """Subklassen implementeren ``handle(seen) -> Reply``."""

    def __init__(self) -> None:
        self.requests: list[Seen] = []
        self.force_status: int | None = None
        self.delay: float = 0.0
        self.redirect_to: str | None = None
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.port = 0

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def handle(self, seen: Seen) -> Reply:  # pragma: no cover - door subklassen
        return Reply(404, {"error": "not found"})

    def start(self) -> FakeHTTP:
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # stil in tests
                return

            def _do(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                parts = urlsplit(self.path)
                headers = {k.lower(): v for k, v in self.headers.items()}
                seen = Seen(self.command, parts.path, parse_qs(parts.query), headers, body)
                fake.requests.append(seen)
                if fake.delay:
                    time.sleep(fake.delay)
                if fake.redirect_to:
                    reply = Reply(302, "", {"Location": fake.redirect_to})
                elif fake.force_status is not None:
                    reply = Reply(fake.force_status, {"error": "geforceerd"})
                else:
                    reply = fake.handle(seen)
                if isinstance(reply.body, dict | list):
                    raw = json.dumps(reply.body).encode()
                    ctype = "application/json"
                elif isinstance(reply.body, bytes):
                    raw, ctype = reply.body, "application/octet-stream"
                else:
                    raw, ctype = str(reply.body or "").encode(), "text/plain; version=0.0.4; charset=utf-8"
                self.send_response(reply.status)
                self.send_header("Content-Type", reply.headers.get("Content-Type", ctype))
                for k, v in reply.headers.items():
                    if k != "Content-Type":
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            do_GET = _do
            do_POST = _do
            do_PUT = _do
            do_HEAD = _do

        self._server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self._server.daemon_threads = True
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def offline(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

    def online(self) -> None:
        self.start()

    def stop(self) -> None:
        self.offline()

    def paths(self) -> list[str]:
        return [s.path for s in self.requests]
