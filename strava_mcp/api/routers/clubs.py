"""Clubs router – list, details, activities, and members."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List

from fastapi import APIRouter, Depends, Query

from strava_mcp.api.dependencies import get_client
from strava_mcp.client.base import StravaClient
from strava_mcp.models.misc import ClubActivity, DetailedClub
from strava_mcp.models.athlete import SummaryClub, SummaryAthlete

router = APIRouter(prefix="/clubs", tags=["Clubs"])

ClientDep = Annotated[StravaClient, Depends(get_client)]


@router.get(
    "",
    response_model=List[SummaryClub],
    summary="List athlete's clubs",
    response_description="Clubs the authenticated athlete belongs to.",
)
async def get_my_clubs(
    client: ClientDep,
    per_page: int = Query(30, ge=1, le=200),
    page: int = Query(1, ge=1),
) -> List[SummaryClub]:
    """Return clubs that the authenticated athlete is a member of."""
    raw: List[Dict[str, Any]] = await client.get_athlete_clubs(
        page=page, per_page=per_page
    )
    return [SummaryClub.model_validate(c) for c in raw]


@router.get(
    "/{club_id}",
    response_model=DetailedClub,
    summary="Get club details",
    response_description="Detailed information about a Strava club.",
)
async def get_club(club_id: int, client: ClientDep) -> DetailedClub:
    """Return detailed information about a specific club."""
    raw: Dict[str, Any] = await client.get_club(club_id)
    return DetailedClub.model_validate(raw)


@router.get(
    "/{club_id}/activities",
    response_model=List[ClubActivity],
    summary="Get club activities feed",
    response_description="Recent activities by club members.",
)
async def get_club_activities(
    club_id: int,
    client: ClientDep,
    per_page: int = Query(30, ge=1, le=200),
    page: int = Query(1, ge=1),
) -> List[ClubActivity]:
    """Return recent activities from a club's activity feed."""
    raw: List[Dict[str, Any]] = await client.get_club_activities(
        club_id, page=page, per_page=per_page
    )
    return [ClubActivity.model_validate(a) for a in raw]


@router.get(
    "/{club_id}/members",
    response_model=List[SummaryAthlete],
    summary="Get club members",
    response_description="Members of the club.",
)
async def get_club_members(
    club_id: int,
    client: ClientDep,
    per_page: int = Query(30, ge=1, le=200),
    page: int = Query(1, ge=1),
) -> List[SummaryAthlete]:
    """Return members of a specific Strava club."""
    raw: List[Dict[str, Any]] = await client.get_club_members(
        club_id, page=page, per_page=per_page
    )
    return [SummaryAthlete.model_validate(m) for m in raw]
