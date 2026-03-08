"""MCP tools – athlete profile, zones, and stats."""

from __future__ import annotations

import json
from typing import Any, Dict

from mcp.server import Server
from mcp.types import TextContent, Tool

from strava_mcp.client.base import StravaClient
from strava_mcp.models.athlete import DetailedAthlete, Zones
from strava_mcp.models.misc import ActivityStats

ATHLETE_TOOLS: list[Tool] = [
    Tool(
        name="get_my_profile",
        description=(
            "Get the full profile of the authenticated Strava athlete. "
            "Returns name, location, stats, clubs, bikes, shoes, FTP, weight, and more."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="get_my_zones",
        description=(
            "Get the athlete's heart-rate and power training zones from Strava. "
            "Returns 5 HR zones and 7 power zones with min/max values."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="get_my_stats",
        description=(
            "Get rolled-up activity statistics for the authenticated athlete: "
            "recent 4 weeks, year-to-date, and all-time totals for rides, runs, and swims."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
]


async def handle_get_my_profile(args: Dict[str, Any]) -> list[TextContent]:
    """Return the authenticated athlete's detailed profile as JSON."""
    async with StravaClient() as client:
        data: Dict[str, Any] = await client.get_athlete()
        athlete = DetailedAthlete.model_validate(data)
    return [TextContent(type="text", text=athlete.model_dump_json(indent=2))]


async def handle_get_my_zones(args: Dict[str, Any]) -> list[TextContent]:
    """Return the athlete's HR and power training zones."""
    async with StravaClient() as client:
        data: Dict[str, Any] = await client.get_athlete_zones()
        zones = Zones.model_validate(data)
    return [TextContent(type="text", text=zones.model_dump_json(indent=2))]


async def handle_get_my_stats(args: Dict[str, Any]) -> list[TextContent]:
    """Return rolled-up activity stats for the athlete."""
    async with StravaClient() as client:
        profile = await client.get_athlete()
        athlete_id: int = profile["id"]
        stats_data: Dict[str, Any] = await client.get_athlete_stats(athlete_id)
        stats = ActivityStats.model_validate(stats_data)
    return [TextContent(type="text", text=stats.model_dump_json(indent=2))]
