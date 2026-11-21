"""Afgifte van kluiswaarden aan de gekoppelde executor (contract 1.3 §8.3, M2; S-P2-050e).

Alleen het service-token van ``ai-server-manager-executor`` met een handtekening van zijn gepinde identiteit. Geen
gebruikersroute: een sessie (ook die van een beheerder) haalt nooit een waarde op. Elk antwoord buiten ``200`` is
zonder waarde.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from hub.catalog import kluis
from hub.deps import DB, Principal, SettingsDep, get_keyring, get_vault, require_service
from hub.keys import KeyRing
from hub.vault import Vault

router = APIRouter(prefix="/api/v1/executor", tags=["kluisafgifte"])
UUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
B64URL = r"^[A-Za-z0-9_-]+$"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RefIn(Strict):
    path: str = Field(pattern=r"^values\.envs\[[0-9]{1,3}\]\.value$")
    ref: str = Field(pattern=r"^vault://app/[a-z0-9][a-z0-9_-]{0,63}/[a-z0-9_.-]{1,128}$")
    revision: str = Field(pattern=UUID)


class SecretClaimIn(Strict):
    request_id: str = Field(pattern=UUID)
    request_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    nonce: str = Field(pattern=UUID)
    approval_id: str = Field(pattern=UUID)
    instance_id: str = Field(pattern=UUID)
    refs: list[RefIn] = Field(max_length=20)
    token: StrictBool
    ontvanger: str = Field(min_length=43, max_length=43, pattern=B64URL, description="Publieke X25519-sleutel.")
    issued_at: str = Field(max_length=32)
    handtekening: str = Field(min_length=86, max_length=86, pattern=B64URL, description="Ed25519, executor-identiteit.")


@router.post(
    "/secret-claims",
    summary="Eenmalige afgifte van kluiswaarden aan de gekoppelde executor (service-token + gepinde identiteit)",
    responses={
        403: {"description": "afgifte_geweigerd"},
        409: {"description": "afgifte_past_niet of afgifte_al_geclaimd"},
        410: {"description": "afgifte_verlopen"},
    },
)
def secret_claim(
    body: SecretClaimIn,
    db: DB,
    settings: SettingsDep,
    principal: Annotated[Principal, Depends(require_service)],
    vault: Annotated[Vault, Depends(get_vault)],
    keyring: Annotated[KeyRing, Depends(get_keyring)],
) -> dict[str, Any]:
    return kluis.claim(db, settings, vault, keyring, principal, body.model_dump(mode="json"))
