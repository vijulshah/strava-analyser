"""MCP tools – activity listing with rich filtering and detail retrieval."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

from strava_mcp.client.base import StravaClient
from strava_mcp.models.activity import (
    ActivityZone,
    DetailedActivity,
    Lap,
    SummaryActivity,
)
from strava_mcp.models.filters import TimeRangePreset, preset_to_epoch_range
from strava_mcp.models.misc import StreamSet

ACTIVITY_TOOLS: list[Tool] = [
    Tool(
        name="get_activities",
        description=(
            "List Strava activities for the authenticated athlete with flexible filtering. "
            "Use preset for common time ranges or specify custom dates. "
            "Optionally filter by sport type. Returns a list of activity summaries."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset": {
                    "type": "string",
                    "enum": [
                        "today",
                        "last_7_days",
                        "last_14_days",
                        "last_30_days",
                        "last_3_months",
                        "last_6_months",
                        "last_year",
                        "this_year",
                        "all_time",
                        "custom",
                    ],
                    "default": "last_30_days",
                    "description": (
                        "Pre-defined time range. 'today'=since midnight, "
                        "'last_7_days'=rolling 7 days, 'last_14_days'=rolling 2 weeks, "
                        "'last_30_days'=rolling month, 'last_3_months'=rolling 90 days, "
                        "'last_6_months'=rolling 182 days, 'last_year'=rolling 365 days, "
                        "'this_year'=since Jan 1, 'all_time'=no filter, "
                        "'custom'=use after_date/before_date."
                    ),
                },
                "after_date": {
                    "type": "string",
                    "description": "ISO 8601 start date, e.g. '2024-01-01'. Required when preset='custom'.",
                },
                "before_date": {
                    "type": "string",
                    "description": "ISO 8601 end date, e.g. '2024-03-31'. Optional.",
                },
                "sport_type": {
                    "type": "string",
                    "description": "Filter by sport type, e.g. 'Run', 'Ride', 'Swim', 'Walk', 'Hike'.",
                },
                "per_page": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 200,
                    "description": "Number of activities to return (max 200).",
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number for pagination.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_activity_detail",
        description=(
            "Get the full detailed representation of a single Strava activity by its ID. "
            "Includes laps, segment efforts, splits, gear, and all metrics."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "The Strava activity ID.",
                },
                "include_all_efforts": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include all segment efforts in the response.",
                },
            },
            "required": ["activity_id"],
        },
    ),
    Tool(
        name="get_activity_laps",
        description="Get all recorded laps for a Strava activity.",
        inputSchema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "The Strava activity ID.",
                },
            },
            "required": ["activity_id"],
        },
    ),
    Tool(
        name="get_activity_zones",
        description=(
            "Get heart rate and power zone distributions for a specific activity. "
            "Returns time spent in each zone if HR or power data was recorded."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "The Strava activity ID.",
                },
            },
            "required": ["activity_id"],
        },
    ),
    Tool(
        name="get_activity_streams",
        description=(
            "Get raw telemetry data streams for an activity. "
            "Available streams: time, distance, latlng, altitude, velocity_smooth, "
            "heartrate, cadence, watts, temp, moving, grade_smooth."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "The Strava activity ID.",
                },
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": [
                        "time",
                        "heartrate",
                        "altitude",
                        "distance",
                        "velocity_smooth",
                    ],
                    "description": "List of stream types to fetch.",
                },
            },
            "required": ["activity_id"],
        },
    ),
]


async def handle_get_activities(args: Dict[str, Any]) -> list[TextContent]:
    """Fetch activities with filter support."""
    from datetime import datetime

    preset_str: str = args.get("preset", "last_30_days")
    preset = TimeRangePreset(preset_str)

    after_str: Optional[str] = args.get("after_date")
    before_str: Optional[str] = args.get("before_date")
    after_dt = datetime.fromisoformat(after_str) if after_str else None
    before_dt = datetime.fromisoformat(before_str) if before_str else None

    after_epoch, before_epoch = preset_to_epoch_range(preset, after_dt, before_dt)

    per_page: int = int(args.get("per_page", 30))
    page: int = int(args.get("page", 1))
    sport_type: Optional[str] = args.get("sport_type")

    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.list_activities(
            before=before_epoch,
            after=after_epoch,
            page=page,
            per_page=per_page,
        )

    activities = [SummaryActivity.model_validate(a) for a in raw]
    if sport_type:
        activities = [
            a
            for a in activities
            if (a.sport_type and a.sport_type.value == sport_type)
            or (a.type and a.type.value == sport_type)
        ]

    result = [a.model_dump(mode="json") for a in activities]
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_get_activity_detail(args: Dict[str, Any]) -> list[TextContent]:
    """Fetch a single detailed activity."""
    activity_id: int = int(args["activity_id"])
    include_all: bool = bool(args.get("include_all_efforts", True))
    async with StravaClient() as client:
        data: Dict[str, Any] = await client.get_activity(activity_id, include_all)
    act = DetailedActivity.model_validate(data)
    return [TextContent(type="text", text=act.model_dump_json(indent=2, mode="json"))]


async def handle_get_activity_laps(args: Dict[str, Any]) -> list[TextContent]:
    """Fetch laps for an activity."""
    activity_id: int = int(args["activity_id"])
    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.get_activity_laps(activity_id)
    laps = [Lap.model_validate(l) for l in raw]
    result = [l.model_dump(mode="json") for l in laps]
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_get_activity_zones(args: Dict[str, Any]) -> list[TextContent]:
    """Fetch HR/power zones for an activity."""
    activity_id: int = int(args["activity_id"])
    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.get_activity_zones(activity_id)
    zones = [ActivityZone.model_validate(z) for z in raw]
    result = [z.model_dump(mode="json") for z in zones]
    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


async def handle_get_activity_streams(args: Dict[str, Any]) -> list[TextContent]:
    """Fetch raw telemetry streams for an activity."""
    activity_id: int = int(args["activity_id"])
    keys: List[str] = args.get(
        "keys",
        ["time", "heartrate", "altitude", "distance", "velocity_smooth"],
    )
    async with StravaClient() as client:
        raw: Dict[str, Any] = await client.get_activity_streams(activity_id, keys)
    streams = StreamSet.model_validate(raw)
    return [TextContent(type="text", text=streams.model_dump_json(indent=2))]
