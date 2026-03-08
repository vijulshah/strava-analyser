"""Activities router – list, detail, laps, zones, streams, comments, kudoers."""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from strava_mcp.api.dependencies import get_client
from strava_mcp.api.schemas.activity_schemas import (
    CreateActivityBody,
    GetStreamsRequest,
    UpdateActivityBody,
)
from strava_mcp.client.base import StravaClient
from strava_mcp.models.activity import (
    ActivityZone,
    Comment,
    DetailedActivity,
    Lap,
    SummaryActivity,
    SummaryGear,
)
from strava_mcp.models.filters import (
    ActivityFilter,
    TimeRangePreset,
    preset_to_epoch_range,
)
from strava_mcp.models.misc import StreamSet

router = APIRouter(prefix="/activities", tags=["Activities"])

ClientDep = Annotated[StravaClient, Depends(get_client)]


@router.get(
    "",
    response_model=List[SummaryActivity],
    summary="List activities with filtering",
    response_description="List of activities matching the filter criteria.",
)
async def list_activities(
    client: ClientDep,
    preset: TimeRangePreset = Query(
        TimeRangePreset.LAST_30_DAYS,
        description="Pre-defined time range (today/last_7_days/last_14_days/last_30_days/last_3_months/last_6_months/last_year/this_year/all_time/custom).",
    ),
    after_date: Optional[str] = Query(
        None, description="ISO 8601 custom start date (required when preset=custom)."
    ),
    before_date: Optional[str] = Query(
        None, description="ISO 8601 custom end date (optional when preset=custom)."
    ),
    sport_type: Optional[str] = Query(
        None, description="Filter by sport type e.g. 'Run', 'Ride', 'Swim'."
    ),
    per_page: int = Query(30, ge=1, le=200, description="Items per page (1–200)."),
    page: int = Query(1, ge=1, description="Page number."),
) -> List[SummaryActivity]:
    """List activities for the authenticated athlete with rich filtering options.

    Supports pre-defined time range presets (today, last 7 days, last month, etc.)
    or a fully custom date range. Optionally filter by sport type and paginate.
    """
    from datetime import datetime

    after_dt = datetime.fromisoformat(after_date) if after_date else None
    before_dt = datetime.fromisoformat(before_date) if before_date else None

    after_epoch, before_epoch = preset_to_epoch_range(preset, after_dt, before_dt)

    raw: List[Dict[str, Any]] = await client.list_activities(
        before=before_epoch,
        after=after_epoch,
        page=page,
        per_page=per_page,
    )

    activities = [SummaryActivity.model_validate(a) for a in raw]

    # Optional in-memory sport type filter (Strava API doesn't support it natively)
    if sport_type:
        activities = [
            a
            for a in activities
            if (a.sport_type and a.sport_type.value == sport_type)
            or (a.type and a.type.value == sport_type)
        ]

    return activities


@router.get(
    "/{activity_id}",
    response_model=DetailedActivity,
    summary="Get detailed activity",
    response_description="Full activity including laps, segment efforts, and splits.",
)
async def get_activity(
    activity_id: int,
    client: ClientDep,
    include_all_efforts: bool = Query(True, description="Include all segment efforts."),
) -> DetailedActivity:
    """Return the full detailed representation of a single activity."""
    data: Dict[str, Any] = await client.get_activity(activity_id, include_all_efforts)
    return DetailedActivity.model_validate(data)


@router.get(
    "/{activity_id}/laps",
    response_model=List[Lap],
    summary="Get activity laps",
    response_description="All laps recorded for the activity.",
)
async def get_activity_laps(activity_id: int, client: ClientDep) -> List[Lap]:
    """Return the list of laps for an activity."""
    raw: List[Dict[str, Any]] = await client.get_activity_laps(activity_id)
    return [Lap.model_validate(l) for l in raw]


@router.get(
    "/{activity_id}/comments",
    response_model=List[Comment],
    summary="Get activity comments",
    response_description="Comments on the activity.",
)
async def get_activity_comments(
    activity_id: int,
    client: ClientDep,
    page_size: int = Query(30, ge=1, le=200),
) -> List[Comment]:
    """Return comments on an activity."""
    raw: List[Dict[str, Any]] = await client.get_activity_comments(
        activity_id, page_size=page_size
    )
    return [Comment.model_validate(c) for c in raw]


@router.get(
    "/{activity_id}/kudoers",
    response_model=List[Dict],
    summary="Get activity kudoers",
    response_description="Athletes who kudoed this activity.",
)
async def get_activity_kudoers(
    activity_id: int,
    client: ClientDep,
    per_page: int = Query(30, ge=1, le=200),
    page: int = Query(1, ge=1),
) -> List[Dict]:
    """Return the list of athletes who gave kudos on an activity."""
    return await client.get_activity_kudoers(activity_id, page=page, per_page=per_page)


@router.get(
    "/{activity_id}/zones",
    response_model=List[ActivityZone],
    summary="Get activity HR/power zones",
    response_description="Heart rate and power zone distributions for the activity.",
)
async def get_activity_zones(activity_id: int, client: ClientDep) -> List[ActivityZone]:
    """Return heart rate and power zone time distributions for an activity."""
    raw: List[Dict[str, Any]] = await client.get_activity_zones(activity_id)
    return [ActivityZone.model_validate(z) for z in raw]


@router.get(
    "/{activity_id}/streams",
    response_model=StreamSet,
    summary="Get activity streams",
    response_description="Raw time-series sensor data (GPS, HR, power, cadence, etc.).",
)
async def get_activity_streams(
    activity_id: int,
    client: ClientDep,
    keys: str = Query(
        "time,distance,latlng,altitude,velocity_smooth,heartrate,cadence,watts,temp,moving,grade_smooth",
        description="Comma-separated stream keys to fetch.",
    ),
) -> StreamSet:
    """Return raw telemetry streams for an activity.

    Available keys: ``time``, ``distance``, ``latlng``, ``altitude``,
    ``velocity_smooth``, ``heartrate``, ``cadence``, ``watts``, ``temp``,
    ``moving``, ``grade_smooth``.
    """
    key_list = [k.strip() for k in keys.split(",") if k.strip()]
    raw: Dict[str, Any] = await client.get_activity_streams(activity_id, key_list)
    return StreamSet.model_validate(raw)


@router.post(
    "",
    response_model=DetailedActivity,
    summary="Create a manual activity",
    status_code=status.HTTP_201_CREATED,
    response_description="The newly created activity.",
)
async def create_activity(
    body: CreateActivityBody,
    client: ClientDep,
) -> DetailedActivity:
    """Create a manual (non-GPS) activity for the authenticated athlete."""
    payload = body.model_dump(exclude_none=True)
    if "start_date_local" in payload:
        payload["start_date_local"] = payload["start_date_local"].isoformat()
    if "sport_type" in payload and hasattr(payload["sport_type"], "value"):
        payload["sport_type"] = payload["sport_type"].value
    raw: Dict[str, Any] = await client._post("/activities", data=payload)
    return DetailedActivity.model_validate(raw)


@router.put(
    "/{activity_id}",
    response_model=DetailedActivity,
    summary="Update an activity",
    response_description="The updated activity.",
)
async def update_activity(
    activity_id: int,
    body: UpdateActivityBody,
    client: ClientDep,
) -> DetailedActivity:
    """Update mutable fields of an activity (name, description, sport type, gear, etc.)."""
    payload = body.model_dump(exclude_none=True)
    if "sport_type" in payload and hasattr(payload["sport_type"], "value"):
        payload["sport_type"] = payload["sport_type"].value
    raw: Dict[str, Any] = await client._put(f"/activities/{activity_id}", data=payload)
    return DetailedActivity.model_validate(raw)
