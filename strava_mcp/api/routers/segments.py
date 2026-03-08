"""Segments router – detail, starred, explore, and efforts."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from strava_mcp.api.dependencies import get_client
from strava_mcp.client.base import StravaClient
from strava_mcp.models.segment import (
    DetailedSegment,
    DetailedSegmentEffort,
    ExplorerResponse,
    SummarySegment,
)

router = APIRouter(prefix="/segments", tags=["Segments"])

ClientDep = Annotated[StravaClient, Depends(get_client)]


@router.get(
    "/starred",
    response_model=List[SummarySegment],
    summary="Get starred segments",
    response_description="Segments the authenticated athlete has starred.",
)
async def get_starred_segments(
    client: ClientDep,
    per_page: int = Query(30, ge=1, le=200),
    page: int = Query(1, ge=1),
) -> List[SummarySegment]:
    """Return segments that the authenticated athlete has starred."""
    raw: List[Dict[str, Any]] = await client.get_starred_segments(
        page=page, per_page=per_page
    )
    return [SummarySegment.model_validate(s) for s in raw]


@router.get(
    "/explore",
    response_model=ExplorerResponse,
    summary="Explore segments in a bounding box",
    response_description="Segments found within the specified lat/lng bounding box.",
)
async def explore_segments(
    client: ClientDep,
    bounds: str = Query(
        ...,
        description="Bounding box: 'SW_lat,SW_lng,NE_lat,NE_lng', e.g. '37.82,-122.53,37.83,-122.51'.",
    ),
    activity_type: Optional[str] = Query(None, description="'running' or 'riding'."),
    min_cat: Optional[int] = Query(
        None, ge=0, le=5, description="Minimum climb category."
    ),
    max_cat: Optional[int] = Query(
        None, ge=0, le=5, description="Maximum climb category."
    ),
) -> ExplorerResponse:
    """Explore segments within a geographical bounding box."""
    raw: Dict[str, Any] = await client.explore_segments(
        bounds=bounds,
        activity_type=activity_type,
        min_cat=min_cat,
        max_cat=max_cat,
    )
    return ExplorerResponse.model_validate(raw)


@router.get(
    "/{segment_id}",
    response_model=DetailedSegment,
    summary="Get segment details",
    response_description="Detailed information about a specific segment.",
)
async def get_segment(segment_id: int, client: ClientDep) -> DetailedSegment:
    """Return the full details of a Strava segment."""
    raw: Dict[str, Any] = await client.get_segment(segment_id)
    return DetailedSegment.model_validate(raw)


@router.get(
    "/{segment_id}/efforts",
    response_model=List[DetailedSegmentEffort],
    summary="Get efforts on a segment",
    response_description="Efforts by the authenticated athlete on a segment.",
)
async def get_segment_efforts(
    segment_id: int,
    client: ClientDep,
    start_date_local: Optional[str] = Query(
        None, description="ISO 8601 start date to filter efforts."
    ),
    end_date_local: Optional[str] = Query(
        None, description="ISO 8601 end date to filter efforts."
    ),
    per_page: int = Query(30, ge=1, le=200),
) -> List[DetailedSegmentEffort]:
    """Return the authenticated athlete's efforts on a segment, optionally filtered by date."""
    raw: List[Dict[str, Any]] = await client.get_segment_efforts(
        segment_id=segment_id,
        start_date_local=start_date_local,
        end_date_local=end_date_local,
        per_page=per_page,
    )
    return [DetailedSegmentEffort.model_validate(e) for e in raw]
