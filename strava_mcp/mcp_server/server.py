"""Strava MCP Server – stdio transport for Claude Desktop.

Run directly or via ``python -m strava_mcp.mcp_server.server``.

Claude Desktop config snippet::

    {
      "mcpServers": {
        "strava": {
          "command": "python",
          "args": ["-m", "strava_mcp.mcp_server.server"],
          "cwd": "C:\\Projects\\strava-analyser"
        }
      }
    }
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Sequence

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from strava_mcp.mcp_server.tools.activity_tools import (
    ACTIVITY_TOOLS,
    handle_get_activities,
    handle_get_activity_detail,
    handle_get_activity_laps,
    handle_get_activity_streams,
    handle_get_activity_zones,
)
from strava_mcp.mcp_server.tools.analysis_tools import (
    ANALYSIS_TOOLS,
    handle_analyze_hr_zones,
    handle_analyze_performance_trend,
    handle_analyze_period_summary,
    handle_analyze_power_zones,
    handle_analyze_weekly_breakdown,
    handle_compare_periods,
    handle_compare_segment_efforts,
    handle_find_personal_records,
    handle_get_activity_insights,
)
from strava_mcp.mcp_server.tools.athlete_tools import (
    ATHLETE_TOOLS,
    handle_get_my_profile,
    handle_get_my_stats,
    handle_get_my_zones,
)
from strava_mcp.mcp_server.tools.auth_tools import (
    AUTH_TOOLS,
    handle_get_auth_status,
    handle_get_auth_url,
)
from strava_mcp.mcp_server.tools.club_tools import (
    CLUB_TOOLS,
    handle_get_club,
    handle_get_club_activities,
    handle_get_club_members,
    handle_get_my_clubs,
)
from strava_mcp.mcp_server.tools.route_tools import (
    ROUTE_TOOLS,
    handle_get_route,
    handle_list_my_routes,
)
from strava_mcp.mcp_server.tools.segment_tools import (
    SEGMENT_TOOLS,
    handle_explore_segments,
    handle_get_segment,
    handle_get_segment_efforts,
    handle_get_starred_segments,
)
from strava_mcp.mcp_server.tools.stream_tools import (
    STREAM_TOOLS,
    handle_get_segment_streams,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("strava-mcp")

# ---------------------------------------------------------------------------
# Build the MCP server
# ---------------------------------------------------------------------------

server = Server("strava-mcp")

ALL_TOOLS: list[types.Tool] = (
    AUTH_TOOLS
    + ATHLETE_TOOLS
    + ACTIVITY_TOOLS
    + SEGMENT_TOOLS
    + CLUB_TOOLS
    + ROUTE_TOOLS
    + STREAM_TOOLS
    + ANALYSIS_TOOLS
)

# Dispatch table: tool name → async handler
_HANDLERS: Dict[str, Any] = {
    # Auth
    "get_auth_status": handle_get_auth_status,
    "get_auth_url": handle_get_auth_url,
    # Athlete
    "get_my_profile": handle_get_my_profile,
    "get_my_zones": handle_get_my_zones,
    "get_my_stats": handle_get_my_stats,
    # Activities
    "get_activities": handle_get_activities,
    "get_activity_detail": handle_get_activity_detail,
    "get_activity_laps": handle_get_activity_laps,
    "get_activity_zones": handle_get_activity_zones,
    "get_activity_streams": handle_get_activity_streams,
    # Segments
    "get_starred_segments": handle_get_starred_segments,
    "get_segment": handle_get_segment,
    "get_segment_efforts": handle_get_segment_efforts,
    "explore_segments": handle_explore_segments,
    # Clubs
    "get_my_clubs": handle_get_my_clubs,
    "get_club": handle_get_club,
    "get_club_activities": handle_get_club_activities,
    "get_club_members": handle_get_club_members,
    # Routes
    "list_my_routes": handle_list_my_routes,
    "get_route": handle_get_route,
    # Streams (alternate for segment streams)
    "get_segment_streams": handle_get_segment_streams,
    # Analysis
    "analyze_period_summary": handle_analyze_period_summary,
    "analyze_performance_trend": handle_analyze_performance_trend,
    "analyze_hr_zones": handle_analyze_hr_zones,
    "analyze_power_zones": handle_analyze_power_zones,
    "find_personal_records": handle_find_personal_records,
    "compare_segment_efforts": handle_compare_segment_efforts,
    "compare_periods": handle_compare_periods,
    "analyze_weekly_breakdown": handle_analyze_weekly_breakdown,
    "get_activity_insights": handle_get_activity_insights,
}


# ---------------------------------------------------------------------------
# MCP handler registrations
# ---------------------------------------------------------------------------


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Return all registered tools to the MCP host."""
    return ALL_TOOLS


@server.call_tool()
async def call_tool(
    name: str,
    arguments: Dict[str, Any],
) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Dispatch a tool call to the appropriate handler.

    Args:
        name: Tool name.
        arguments: Tool arguments from the MCP host.

    Returns:
        List of content items (usually a single TextContent with JSON).

    Raises:
        ValueError: If the tool name is not registered.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        raise ValueError(
            f"Unknown tool: {name!r}. Available tools: {list(_HANDLERS.keys())}"
        )
    try:
        return await handler(arguments or {})
    except Exception as exc:
        logger.exception("Tool %r raised an exception: %s", name, exc)
        return [types.TextContent(type="text", text=f"Error: {exc}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    """Start the MCP server using stdio transport."""
    logger.info("Starting Strava MCP server with %d tools …", len(ALL_TOOLS))
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
