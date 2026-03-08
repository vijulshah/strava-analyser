"""Routes router – list and detail saved routes."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, Query

from strava_mcp.api.dependencies import get_client
from strava_mcp.client.base import StravaClient
from strava_mcp.models.misc import Route

router = APIRouter(prefix="/routes", tags=["Routes"])

ClientDep = Annotated[StravaClient, Depends(get_client)]


@router.get(
    "",
    response_model=List[Route],
    summary="List athlete's routes",
    response_description="Saved routes for the authenticated athlete.",
)
async def list_routes(
    client: ClientDep,
    per_page: int = Query(30, ge=1, le=200),
    page: int = Query(1, ge=1),
) -> List[Route]:
    """Return the authenticated athlete's saved routes."""
    profile_data: Dict[str, Any] = await client.get_athlete()
    athlete_id: int = profile_data["id"]
    raw: List[Dict[str, Any]] = await client.list_routes(
        athlete_id=athlete_id, page=page, per_page=per_page
    )
    return [Route.model_validate(r) for r in raw]


@router.get(
    "/{route_id}",
    response_model=Route,
    summary="Get route details",
    response_description="Detailed information about a specific route.",
)
async def get_route(route_id: int, client: ClientDep) -> Route:
    """Return detailed information about a saved route."""
    raw: Dict[str, Any] = await client.get_route(route_id)
    return Route.model_validate(raw)
