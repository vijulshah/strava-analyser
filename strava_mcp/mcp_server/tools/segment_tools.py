"""MCP tools – segments, starred segments, efforts, and exploration."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

from strava_mcp.client.base import StravaClient
from strava_mcp.models.segment import (
    DetailedSegment,
    DetailedSegmentEffort,
    ExplorerResponse,
    SummarySegment,
)

SEGMENT_TOOLS: list[Tool] = [
    Tool(
        name="get_starred_segments",
        description="Get segments that the authenticated athlete has starred on Strava.",
        inputSchema={
            "type": "object",
            "properties": {
                "per_page": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 200,
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
            },
            "required": [],
        },
    ),
    Tool(
        name="get_segment",
        description="Get detailed information about a Strava segment by its ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "segment_id": {
                    "type": "integer",
                    "description": "Strava segment ID.",
                }
            },
            "required": ["segment_id"],
        },
    ),
    Tool(
        name="get_segment_efforts",
        description=(
            "Get all the authenticated athlete's efforts on a specific segment. "
            "Optionally filter by date range. Returns efforts sorted by date."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "segment_id": {
                    "type": "integer",
                    "description": "Strava segment ID.",
                },
                "start_date_local": {
                    "type": "string",
                    "description": "ISO 8601 start date filter, e.g. '2024-01-01T00:00:00Z'.",
                },
                "end_date_local": {
                    "type": "string",
                    "description": "ISO 8601 end date filter.",
                },
                "per_page": {
                    "type": "integer",
                    "default": 200,
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "required": ["segment_id"],
        },
    ),
    Tool(
        name="explore_segments",
        description=(
            "Find Strava segments within a geographical bounding box. "
            "Returns segments sorted by athlete count."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "bounds": {
                    "type": "string",
                    "description": "Bounding box as 'SW_lat,SW_lng,NE_lat,NE_lng', e.g. '37.82,-122.53,37.83,-122.51'.",
                },
                "activity_type": {
                    "type": "string",
                    "enum": ["running", "riding"],
                    "description": "Filter by activity type.",
                },
                "min_cat": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Minimum climb category (0=no category, 5=HC).",
                },
                "max_cat": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 5,
                    "description": "Maximum climb category.",
                },
            },
            "required": ["bounds"],
        },
    ),
]


async def handle_get_starred_segments(args: Dict[str, Any]) -> list[TextContent]:
    per_page: int = int(args.get("per_page", 30))
    page: int = int(args.get("page", 1))
    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.get_starred_segments(
            page=page, per_page=per_page
        )
    segments = [SummarySegment.model_validate(s) for s in raw]
    return [
        TextContent(
            type="text",
            text=json.dumps(
                [s.model_dump(mode="json") for s in segments], indent=2, default=str
            ),
        )
    ]


async def handle_get_segment(args: Dict[str, Any]) -> list[TextContent]:
    segment_id: int = int(args["segment_id"])
    async with StravaClient() as client:
        data: Dict[str, Any] = await client.get_segment(segment_id)
    seg = DetailedSegment.model_validate(data)
    return [TextContent(type="text", text=seg.model_dump_json(indent=2))]


async def handle_get_segment_efforts(args: Dict[str, Any]) -> list[TextContent]:
    segment_id: int = int(args["segment_id"])
    start_date: Optional[str] = args.get("start_date_local")
    end_date: Optional[str] = args.get("end_date_local")
    per_page: int = int(args.get("per_page", 200))
    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.get_segment_efforts(
            segment_id=segment_id,
            start_date_local=start_date,
            end_date_local=end_date,
            per_page=per_page,
        )
    efforts = [DetailedSegmentEffort.model_validate(e) for e in raw]
    return [
        TextContent(
            type="text",
            text=json.dumps(
                [e.model_dump(mode="json") for e in efforts], indent=2, default=str
            ),
        )
    ]


async def handle_explore_segments(args: Dict[str, Any]) -> list[TextContent]:
    async with StravaClient() as client:
        data: Dict[str, Any] = await client.explore_segments(
            bounds=args["bounds"],
            activity_type=args.get("activity_type"),
            min_cat=args.get("min_cat"),
            max_cat=args.get("max_cat"),
        )
    resp = ExplorerResponse.model_validate(data)
    return [TextContent(type="text", text=resp.model_dump_json(indent=2))]
