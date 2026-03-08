"""Athlete router – profile, zones, and stats endpoints."""

from __future__ import annotations

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status

from strava_mcp.api.dependencies import get_client
from strava_mcp.client.base import StravaClient
from strava_mcp.models.athlete import DetailedAthlete, Zones
from strava_mcp.models.misc import ActivityStats

router = APIRouter(prefix="/athlete", tags=["Athlete"])

ClientDep = Annotated[StravaClient, Depends(get_client)]


@router.get(
    "",
    response_model=DetailedAthlete,
    summary="Get authenticated athlete profile",
    response_description="Full profile of the authenticated Strava athlete.",
)
async def get_athlete(client: ClientDep) -> DetailedAthlete:
    """Return the detailed profile of the authenticated athlete.

    Includes personal details, gear, clubs, FTP, weight, and measurement preferences.
    """
    data: Dict[str, Any] = await client.get_athlete()
    return DetailedAthlete.model_validate(data)


@router.get(
    "/zones",
    response_model=Zones,
    summary="Get athlete training zones",
    response_description="Heart rate and power training zones for the athlete.",
)
async def get_athlete_zones(client: ClientDep) -> Zones:
    """Return the authenticated athlete's heart-rate and power training zones."""
    data: Dict[str, Any] = await client.get_athlete_zones()
    return Zones.model_validate(data)


@router.get(
    "/stats",
    response_model=ActivityStats,
    summary="Get athlete activity statistics",
    response_description="Lifetime + YTD + recent-4-week activity statistics.",
)
async def get_athlete_stats(client: ClientDep) -> ActivityStats:
    """Return rolled-up statistics (recent 4 weeks, year-to-date, all-time) for the athlete."""
    profile_data: Dict[str, Any] = await client.get_athlete()
    athlete_id: int = profile_data["id"]
    stats_data: Dict[str, Any] = await client.get_athlete_stats(athlete_id)
    return ActivityStats.model_validate(stats_data)
