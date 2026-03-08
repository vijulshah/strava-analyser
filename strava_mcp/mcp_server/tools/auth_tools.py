"""MCP tools – Strava OAuth2 authentication.

These tools allow Claude to check authentication status and provide the
user with a login URL when the app is not yet authorised.

Tools
-----
- ``get_auth_status``  – Check if the app is authenticated.
- ``get_auth_url``     – Return the Strava login URL so the user can authenticate.
"""

from __future__ import annotations

import json
import time
import urllib.parse
from typing import Any, Dict

from mcp.types import TextContent, Tool

from strava_mcp.client.auth import token_manager
from strava_mcp.config import settings

_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
_DEFAULT_SCOPES = "activity:read_all,read_all"

AUTH_TOOLS: list[Tool] = [
    Tool(
        name="get_auth_status",
        description=(
            "Check whether the Strava MCP server is authenticated. "
            "If not authenticated, call get_auth_url to get a login link for the user."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_auth_url",
        description=(
            "Generate a Strava OAuth2 authorization URL. "
            "Present this URL to the user and ask them to open it in a browser. "
            "Once they complete login, the server will be authenticated automatically "
            "via the /auth/callback redirect."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "redirect_uri": {
                    "type": "string",
                    "description": (
                        "URI Strava redirects to after authorization. "
                        "Defaults to http://localhost:8000/auth/callback (the FastAPI server)."
                    ),
                    "default": "http://localhost:8000/auth/callback",
                },
                "scope": {
                    "type": "string",
                    "description": "Comma-separated Strava scopes.",
                    "default": _DEFAULT_SCOPES,
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def handle_get_auth_status(args: Dict[str, Any]) -> list[TextContent]:
    """Return current authentication state."""
    authenticated = token_manager.is_authenticated()
    if authenticated:
        remaining = max(0.0, token_manager._token_expiry - time.time())
        result = {
            "authenticated": True,
            "access_token_valid": remaining > 60,
            "access_token_expires_in_seconds": int(remaining),
        }
    else:
        result = {
            "authenticated": False,
            "message": (
                "Not authenticated. Use the get_auth_url tool to get a login link, "
                "then ask the user to open it in their browser."
            ),
        }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_auth_url(args: Dict[str, Any]) -> list[TextContent]:
    """Generate and return the Strava OAuth authorization URL."""
    redirect_uri: str = args.get("redirect_uri", "http://localhost:8000/auth/callback")
    scope: str = args.get("scope", _DEFAULT_SCOPES)

    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": scope,
    }
    auth_url = f"{_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    result = {
        "auth_url": auth_url,
        "instructions": (
            "Please open the auth_url in your browser and log in to Strava. "
            "After you grant access, you will be redirected and the server will "
            "store your tokens automatically. "
            "Then call get_auth_status to confirm authentication succeeded."
        ),
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
