"""Streams router – activity and segment raw telemetry streams."""

from __future__ import annotations

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, Query

from strava_mcp.api.dependencies import get_client
from strava_mcp.client.base import StravaClient
from strava_mcp.models.misc import StreamSet

router = APIRouter(tags=["Streams"])

ClientDep = Annotated[StravaClient, Depends(get_client)]

_ALL_STREAM_KEYS = (
    "time,distance,latlng,altitude,velocity_smooth,heartrate,"
    "cadence,watts,temp,moving,grade_smooth"
)


@router.get(
    "/activities/{activity_id}/streams",
    response_model=StreamSet,
    summary="Get activity telemetry streams",
    response_description="Raw sensor data streams for an activity.",
)
async def get_activity_streams(
    activity_id: int,
    client: ClientDep,
    keys: str = Query(
        _ALL_STREAM_KEYS,
        description="Comma-separated stream keys. Options: time, distance, latlng, altitude, velocity_smooth, heartrate, cadence, watts, temp, moving, grade_smooth.",
    ),
) -> StreamSet:
    """Return raw sensor telemetry streams for an activity.

    Request specific stream types or leave ``keys`` as the default to receive all
    available streams in one call.
    """
    key_list = [k.strip() for k in keys.split(",") if k.strip()]
    raw: Dict[str, Any] = await client.get_activity_streams(activity_id, key_list)
    return StreamSet.model_validate(raw)


@router.get(
    "/segments/{segment_id}/streams",
    response_model=StreamSet,
    summary="Get segment telemetry streams",
    response_description="Raw telemetry streams for a segment.",
)
async def get_segment_streams(
    segment_id: int,
    client: ClientDep,
    keys: str = Query(
        "distance,latlng,altitude,grade_smooth",
        description="Comma-separated stream keys for segment streams.",
    ),
) -> StreamSet:
    """Return telemetry streams for a Strava segment."""
    key_list = [k.strip() for k in keys.split(",") if k.strip()]
    raw: Dict[str, Any] = await client.get_segment_streams(segment_id, key_list)
    return StreamSet.model_validate(raw)
