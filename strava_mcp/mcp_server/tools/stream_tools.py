"""MCP tools – raw telemetry streams for activities and segments."""

from __future__ import annotations

from typing import Any, Dict, List

from mcp.types import TextContent, Tool

from strava_mcp.client.base import StravaClient
from strava_mcp.models.misc import StreamSet

STREAM_TOOLS: list[Tool] = [
    Tool(
        name="get_segment_streams",
        description="Get raw telemetry streams for a Strava segment (GPS track, altitude, grade).",
        inputSchema={
            "type": "object",
            "properties": {
                "segment_id": {
                    "type": "integer",
                    "description": "Strava segment ID.",
                },
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["distance", "latlng", "altitude", "grade_smooth"],
                    "description": "Stream types to fetch.",
                },
            },
            "required": ["segment_id"],
        },
    ),
]


async def handle_get_segment_streams(args: Dict[str, Any]) -> list[TextContent]:
    segment_id: int = int(args["segment_id"])
    keys: List[str] = args.get(
        "keys", ["distance", "latlng", "altitude", "grade_smooth"]
    )
    async with StravaClient() as client:
        raw: Dict[str, Any] = await client.get_segment_streams(segment_id, keys)
    streams = StreamSet.model_validate(raw)
    return [TextContent(type="text", text=streams.model_dump_json(indent=2))]
