"""Gear router – fetch gear details by ID."""

from __future__ import annotations

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends

from strava_mcp.api.dependencies import get_client
from strava_mcp.client.base import StravaClient
from strava_mcp.models.misc import DetailedGear

router = APIRouter(prefix="/gear", tags=["Gear"])

ClientDep = Annotated[StravaClient, Depends(get_client)]


@router.get(
    "/{gear_id}",
    response_model=DetailedGear,
    summary="Get gear details",
    response_description="Detailed information about a bike or pair of shoes.",
)
async def get_gear(gear_id: str, client: ClientDep) -> DetailedGear:
    """Return detailed information about a piece of gear (bike or shoes) by its ID.

    Gear IDs start with ``'b'`` (bikes) or ``'g'`` (shoes), e.g. ``'b12345678'``.
    """
    raw: Dict[str, Any] = await client.get_gear(gear_id)
    return DetailedGear.model_validate(raw)
