"""Begrensd diagnosekanaal tussen de Hub (568) en de runner (569), zonder gedeelde sleutels.

Een Linux Unix-seqpacket bewaart berichtgrenzen. Beide processen controleren de uid van hun
tegenpartij. Alleen de runner spreekt de door de beheerder ingestelde kredietdienst aan.
"""

from __future__ import annotations

import socket
import struct
import threading
import uuid
from dataclasses import replace
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from hub import outbound
from hub.config import Settings
from hub.redact import redact_log_text
from hub.timeutil import utcnow

ADRES = "\0asm-ai-diagnose-v1"
HUB_UID, RUNNER_UID = 568, 569
MAX_BERICHT = 8192
Naam = Annotated[str, Field(min_length=1, max_length=128)]


class Bericht(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Triage(Bericht):
    """Alleen vaste categorieën en aantallen mogen de Hub verlaten."""

    ernst: Literal["info", "waarschuwing", "kritiek"]
    gebeurtenissen: int = Field(ge=1)
    inventaris: Literal["ok", "unknown", "stale", "error"]
    logregels: int = Field(ge=0, le=10)


class Aanvraag(Bericht):
    taak_id: uuid.UUID
    aanbieder: Naam
    modelkeuze: Naam
    maand: str = Field(pattern=r"^[0-9]{4}-(0[1-9]|1[0-2])$")
    max_eenheden: int = Field(gt=0, le=1_000_000_000)
    triage: Triage


class Antwoord(Bericht):
    status: Literal["advies", "tegoed_op", "dienst_onbeschikbaar"]
    analyse: str | None = Field(default=None, max_length=1000)


class Advies(Bericht):
    analyse: str = Field(min_length=1, max_length=1000)


def raadpleeg(taak: Aanvraag, settings: Settings) -> Antwoord:
    """De gekoppelde dienst moet de bovengrens zelf atomair afdwingen en bij uitputting 402 geven."""
    url = settings.ai_provider_url
    if not settings.ai_enabled or not url or taak.maand != utcnow().strftime("%Y-%m"):
        return Antwoord(status="dienst_onbeschikbaar")
    try:
        policy = settings.outbound_policy()
        basis = outbound.validate_base_url(url, allow_loopback=policy.allow_loopback)
        adres = urlsplit(basis)
        if adres.scheme == "https":
            peers = outbound.resolve_peer_addresses(adres.hostname or "", adres.port or 443, policy.allow_loopback)
            policy = replace(policy, allowed_peer_addresses=peers)
        elif not (policy.allow_loopback and adres.hostname == "localhost"):
            return Antwoord(status="dienst_onbeschikbaar")
        antwoord = outbound.request(
            basis,
            "POST",
            "/diagnose",
            policy=policy,
            headers={"Idempotency-Key": str(taak.taak_id)},
            json_body={**taak.model_dump(mode="json"), "alleen_inbegrepen": True},
            max_bytes=MAX_BERICHT,
        )
        if antwoord.status == 402:
            return Antwoord(status="tegoed_op")
        if antwoord.status == 200:
            advies = Advies.model_validate_json(antwoord.body)
            return Antwoord(status="advies", analyse=redact_log_text(advies.analyse, max_len=1000))
    except (outbound.OutboundError, ValueError, OSError):
        pass
    return Antwoord(status="dienst_onbeschikbaar")


def _uid(kanaal: socket.socket) -> int:
    return int(struct.unpack("3i", kanaal.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))[1])


def vraag_runner(taak: Aanvraag) -> Antwoord:
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as kanaal:
            kanaal.settimeout(25)
            kanaal.connect(ADRES)
            if _uid(kanaal) == RUNNER_UID:
                kanaal.sendall(taak.model_dump_json().encode())
                return Antwoord.model_validate_json(kanaal.recv(MAX_BERICHT + 1))
    except (OSError, ValidationError):
        pass
    return Antwoord(status="dienst_onbeschikbaar")


def bedien(settings: Settings, stop: threading.Event) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as server:
        server.bind(ADRES)
        server.listen(4)
        server.settimeout(0.5)
        while not stop.is_set():
            try:
                kanaal, _ = server.accept()
            except TimeoutError:
                continue
            with kanaal:
                if _uid(kanaal) != HUB_UID:
                    continue
                kanaal.settimeout(2)
                try:
                    data = kanaal.recv(MAX_BERICHT + 1)
                    if len(data) <= MAX_BERICHT:
                        taak = Aanvraag.model_validate_json(data)
                        kanaal.sendall(raadpleeg(taak, settings).model_dump_json().encode())
                except (OSError, ValidationError):
                    continue
