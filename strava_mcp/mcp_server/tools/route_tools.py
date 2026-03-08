"""MCP tools – saved routes listing and detail."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from mcp.types import TextContent, Tool

from strava_mcp.client.base import StravaClient
from strava_mcp.models.misc import Route

ROUTE_TOOLS: list[Tool] = [
    Tool(
        name="list_my_routes",
        description="List the saved routes for the authenticated Strava athlete.",
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
        name="get_route",
        description="Get detailed information about a specific saved Strava route.",
        inputSchema={
            "type": "object",
            "properties": {
                "route_id": {"type": "integer", "description": "Strava route ID."},
            },
            "required": ["route_id"],
        },
    ),
]


async def handle_list_my_routes(args: Dict[str, Any]) -> list[TextContent]:
    per_page: int = int(args.get("per_page", 30))
    page: int = int(args.get("page", 1))
    async with StravaClient() as client:
        profile = await client.get_athlete()
        athlete_id: int = profile["id"]
        raw: List[Dict[str, Any]] = await client.list_routes(
            athlete_id=athlete_id, page=page, per_page=per_page
        )
    routes = [Route.model_validate(r) for r in raw]
    return [
        TextContent(
            type="text",
            text=json.dumps(
                [r.model_dump(mode="json") for r in routes], indent=2, default=str
            ),
        )
    ]


async def handle_get_route(args: Dict[str, Any]) -> list[TextContent]:
    route_id: int = int(args["route_id"])
    async with StravaClient() as client:
        data: Dict[str, Any] = await client.get_route(route_id)
    route = Route.model_validate(data)
    return [TextContent(type="text", text=route.model_dump_json(indent=2))]
