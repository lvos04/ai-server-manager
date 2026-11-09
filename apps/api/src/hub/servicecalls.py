"""Hub → eigen dienst (contract 1.2 §4.3, §5).

- Per aanroep een **nieuwe** dienst-JWT (``token_use: "hub_service"``); nooit het service-token van de dienst.
- Nooit een redirect volgen (3xx = storing) en nooit proxy-omgevingsvariabelen gebruiken: ``http.client`` doet geen
  van beide. Tijdlimieten 5 s connect / 15 s read; antwoord hooguit 1 MiB.
- Alleen ``http://`` naar het gemeten registeradres (D03 + hostpoort); HTTPS op het LAN volgt met B10/B13.
"""

from __future__ import annotations

import http.client
import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 1024 * 1024


class ServiceCallError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class CallResult:
    status: int
    body: dict[str, Any] | None
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def code(self) -> str | None:
        return str(self.body.get("code")) if isinstance(self.body, dict) and self.body.get("code") else None

    @property
    def reason(self) -> str | None:
        details = self.body.get("details") if isinstance(self.body, dict) else None
        return str(details.get("reason")) if isinstance(details, dict) and details.get("reason") else None


def call(
    base_url: str,
    method: str,
    path: str,
    *,
    bearer: str,
    idempotency_key: str | None = None,
    body: dict[str, Any] | None = None,
    connect_timeout: float = 5.0,
    read_timeout: float = 15.0,
) -> CallResult:
    parts = urlsplit(base_url)
    if parts.scheme != "http" or not parts.hostname or parts.username or parts.password or parts.query:
        raise ServiceCallError("adres_ongeldig")
    if not path.startswith("/"):
        raise ServiceCallError("pad_ongeldig")
    headers = {"Authorization": f"Bearer {bearer}", "Accept": "application/json", "User-Agent": "ai-server-manager"}
    data = None
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode()
        headers["Content-Type"] = "application/json"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=connect_timeout)
    try:
        try:
            conn.connect()
            if conn.sock is not None:
                conn.sock.settimeout(read_timeout)
            conn.request(method, path, body=data, headers=headers)
            resp = conn.getresponse()
            raw = resp.read(MAX_RESPONSE_BYTES + 1)
        except TimeoutError:
            raise ServiceCallError("tijdslimiet") from None
        except (OSError, http.client.HTTPException):
            raise ServiceCallError("niet_bereikbaar") from None
    finally:
        conn.close()
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ServiceCallError("antwoord_te_groot")
    if 300 <= resp.status < 400:
        raise ServiceCallError("redirect_niet_gevolgd")
    parsed: dict[str, Any] | None = None
    try:
        value = json.loads(raw) if raw else None
        parsed = value if isinstance(value, dict) else None
    except ValueError:
        parsed = None
    return CallResult(resp.status, parsed, {k.lower(): v for k, v in resp.getheaders()})
