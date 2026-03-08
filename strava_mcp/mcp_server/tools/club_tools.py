"""MCP tools – clubs membership, activity feed, and member list."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from mcp.types import TextContent, Tool

from strava_mcp.client.base import StravaClient
from strava_mcp.models.athlete import SummaryAthlete, SummaryClub
from strava_mcp.models.misc import ClubActivity, DetailedClub

CLUB_TOOLS: list[Tool] = [
    Tool(
        name="get_my_clubs",
        description="Get the clubs that the authenticated Strava athlete belongs to.",
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
        name="get_club",
        description="Get detailed information about a specific Strava club.",
        inputSchema={
            "type": "object",
            "properties": {
                "club_id": {"type": "integer", "description": "Strava club ID."},
            },
            "required": ["club_id"],
        },
    ),
    Tool(
        name="get_club_activities",
        description="Get recent activities from a Strava club's activity feed.",
        inputSchema={
            "type": "object",
            "properties": {
                "club_id": {"type": "integer", "description": "Strava club ID."},
                "per_page": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 200,
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
            },
            "required": ["club_id"],
        },
    ),
    Tool(
        name="get_club_members",
        description="Get the members of a specific Strava club.",
        inputSchema={
            "type": "object",
            "properties": {
                "club_id": {"type": "integer", "description": "Strava club ID."},
                "per_page": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "maximum": 200,
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
            },
            "required": ["club_id"],
        },
    ),
]


async def handle_get_my_clubs(args: Dict[str, Any]) -> list[TextContent]:
    per_page: int = int(args.get("per_page", 30))
    page: int = int(args.get("page", 1))
    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.get_athlete_clubs(
            page=page, per_page=per_page
        )
    clubs = [SummaryClub.model_validate(c) for c in raw]
    return [
        TextContent(
            type="text",
            text=json.dumps(
                [c.model_dump(mode="json") for c in clubs], indent=2, default=str
            ),
        )
    ]


async def handle_get_club(args: Dict[str, Any]) -> list[TextContent]:
    club_id: int = int(args["club_id"])
    async with StravaClient() as client:
        data: Dict[str, Any] = await client.get_club(club_id)
    club = DetailedClub.model_validate(data)
    return [TextContent(type="text", text=club.model_dump_json(indent=2))]


async def handle_get_club_activities(args: Dict[str, Any]) -> list[TextContent]:
    club_id: int = int(args["club_id"])
    per_page: int = int(args.get("per_page", 30))
    page: int = int(args.get("page", 1))
    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.get_club_activities(
            club_id, page=page, per_page=per_page
        )
    acts = [ClubActivity.model_validate(a) for a in raw]
    return [
        TextContent(
            type="text",
            text=json.dumps(
                [a.model_dump(mode="json") for a in acts], indent=2, default=str
            ),
        )
    ]


async def handle_get_club_members(args: Dict[str, Any]) -> list[TextContent]:
    club_id: int = int(args["club_id"])
    per_page: int = int(args.get("per_page", 30))
    page: int = int(args.get("page", 1))
    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.get_club_members(
            club_id, page=page, per_page=per_page
        )
    members = [SummaryAthlete.model_validate(m) for m in raw]
    return [
        TextContent(
            type="text",
            text=json.dumps(
                [m.model_dump(mode="json") for m in members], indent=2, default=str
            ),
        )
    ]
