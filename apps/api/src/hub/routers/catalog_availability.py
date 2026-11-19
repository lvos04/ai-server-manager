"""M3: één exacte cataloguspin voor ingeschreven diensten met catalogus.lezen."""

from __future__ import annotations

import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from hub.catalog import availability
from hub.deps import DB, ServiceP, SettingsDep
from hub.errors import HubError
from hub.scopes import CATALOGUS_LEZEN, has_scope
from hub.timeutil import UtcDateTime

router = APIRouter(prefix="/api/v1/catalog", tags=["appcatalogus"])


class CatalogPin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train: availability.Train
    app: str
    version: str
    beschikbaar: availability.Availability
    gemeten_op: UtcDateTime | None = Field(
        description="Bronmeettijd in UTC met Z. Bij onbekend is de waarde null.",
        json_schema_extra={"format": "date-time"},
    )


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any]
    trace_id: str


def _storage_unavailable() -> HubError:
    return HubError(
        503, "dependency_unavailable", "De catalogusmeting is tijdelijk niet leesbaar.", headers={"Retry-After": "5"}
    )


def _authorize(db: DB, principal: ServiceP) -> None:
    if not has_scope(principal.service_app_id, CATALOGUS_LEZEN):
        raise HubError(
            403,
            "scope_ontbreekt",
            "Deze dienst heeft geen leesrecht op de catalogus.",
            {"vereiste_scope": CATALOGUS_LEZEN},
        )
    try:
        availability.charge_read(db, principal.id)
    except SQLAlchemyError as exc:
        raise _storage_unavailable() from exc


async def _check_shape(request: Request) -> None:
    fields = ("train", "app", "version")
    query = request.query_params
    errors = [
        {"veld": field, "fout": "Deze parameter is precies één keer verplicht.", "type": "count"}
        for field in fields
        if len(query.getlist(field)) != 1
    ]
    if set(query) - set(fields):
        errors.append({"veld": "query", "fout": "Extra parameters zijn verboden.", "type": "extra_forbidden"})
    if await request.body():
        errors.append({"veld": "body", "fout": "Een verzoekbody is verboden.", "type": "extra_forbidden"})
    if errors:
        raise HubError(422, "validation_error", "De invoer is ongeldig.", {"fouten": errors})


@router.get(
    "/availability",
    summary="Beschikbaarheid van één vastgezette TrueNAS-catalogusversie (dienstscope catalogus.lezen)",
    dependencies=[Depends(_authorize), Depends(_check_shape)],
    responses={
        401: {
            "model": ErrorResponse,
            "description": "unauthorized met details.reason: geldig Bearer-service-token vereist",
        },
        403: {"model": ErrorResponse, "description": "scope_ontbreekt"},
        422: {"model": ErrorResponse, "description": "validation_error met details.fouten"},
        429: {
            "model": ErrorResponse,
            "description": "rate_limited",
            "headers": {"Retry-After": {"schema": {"type": "integer", "minimum": 1}}},
        },
        503: {
            "model": ErrorResponse,
            "description": "dependency_unavailable",
            "headers": {"Retry-After": {"schema": {"type": "integer", "minimum": 1}}},
        },
    },
)
def catalog_availability(
    db: DB,
    settings: SettingsDep,
    train: Annotated[availability.Train, Query()],
    app: Annotated[str, Query(pattern=f"^{availability.APP_PATTERN}$", max_length=63)],
    version: Annotated[
        str, Query(pattern=f"^{availability.VERSION_PATTERN}$", max_length=availability.MAX_VERSION_LENGTH)
    ],
) -> CatalogPin:
    # Naast het OpenAPI-patroon geldt een volledige tekenreeksvergelijking.
    for field, value, pattern in (
        ("app", app, availability.APP_PATTERN),
        ("version", version, availability.VERSION_PATTERN),
    ):
        if re.fullmatch(pattern, value) is None:
            raise HubError(
                422,
                "validation_error",
                "De invoer is ongeldig.",
                {
                    "fouten": [{"veld": field, "fout": "Ongeldig formaat.", "type": "string_pattern_mismatch"}],
                },
            )
    try:
        state, measured = availability.read_pin(db, settings, train, app, version)
    except (OSError, SQLAlchemyError) as exc:
        raise _storage_unavailable() from exc
    return CatalogPin(train=train, app=app, version=version, beschikbaar=state, gemeten_op=measured)
