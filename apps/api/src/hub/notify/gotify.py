"""Gotify-adapter (``notification.send``, R0): bericht versturen, versie en gezondheid lezen.

Bronwaarneming (broncode ``gotify/server`` v3.1.1, NIET GEVALIDEERD tegen een echte installatie):
- ``POST /message`` met header ``X-Gotify-Key: <applicatietoken>`` en JSON ``{title, message, priority, extras}`` →
  ``200`` met ``{id, appid, …}``; 401/403 bij een ongeldig token.
- ``GET /version`` (zonder aanmelding) → ``{version, commit, buildDate}``; ``GET /health`` → ``{health, database}``.
De Hub gebruikt uitsluitend een **applicatietoken** (kan alleen berichten sturen; geen gedeeld beheertoken, I13). Het
token staat versleuteld in de vault en komt nooit in logs of antwoorden.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hub.outbound import OutboundError, OutboundPolicy, request

PRIORITEIT = {"info": 2, "waarschuwing": 5, "kritiek": 8}


@dataclass
class SendResult:
    ok: bool
    reden: str | None = None
    http: int | None = None
    extern_id: str | None = None
    definitief: bool = False  # True = opnieuw proberen heeft geen zin (token geweigerd, ongeldig verzoek)


def send(base_url: str, token: str, *, titel: str, bericht: str, ernst: str, policy: OutboundPolicy) -> SendResult:
    body: dict[str, Any] = {
        "title": titel[:160],
        "message": bericht[:2000],
        "priority": PRIORITEIT.get(ernst, 5),
        "extras": {"client::display": {"contentType": "text/plain"}},
    }
    try:
        res = request(base_url, "POST", "/message", policy=policy, headers={"X-Gotify-Key": token}, json_body=body)
    except OutboundError as exc:
        return SendResult(False, exc.reason, definitief=exc.reason in ("adres_ongeldig", "adres_niet_toegestaan"))
    if res.status in (401, 403):
        return SendResult(False, "token_geweigerd", res.status, definitief=True)
    if res.status == 400:
        return SendResult(False, "verzoek_geweigerd", res.status, definitief=True)
    if res.status != 200:
        return SendResult(False, f"http_{res.status}", res.status)
    data = res.json()
    ext = str(data.get("id")) if isinstance(data, dict) and data.get("id") is not None else None
    return SendResult(True, None, res.status, ext)


def version(base_url: str, policy: OutboundPolicy) -> tuple[str | None, str | None]:
    """``(versie, None)`` of ``(None, reden)``."""
    try:
        res = request(base_url, "GET", "/version", policy=policy, max_bytes=64 * 1024)
    except OutboundError as exc:
        return None, exc.reason
    data = res.json()
    if res.status != 200 or not isinstance(data, dict) or not isinstance(data.get("version"), str):
        return None, "versie_onbekend"
    return str(data["version"])[:64], None
