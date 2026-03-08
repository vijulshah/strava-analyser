"""Strava OAuth2 flow endpoints.

Endpoints
---------
GET  /auth/login       – Generate and return the Strava authorization URL.
GET  /auth/callback    – Handle the redirect from Strava; exchange code for tokens.
GET  /auth/status      – Show whether the app is currently authenticated.
POST /auth/deauthorize – Revoke Strava access and clear stored tokens.

Usage flow
----------
1.  Call ``GET /auth/login`` (or open its ``auth_url`` in a browser).
2.  Strava redirects to ``/auth/callback?code=<CODE>&scope=<SCOPE>``.
3.  Tokens are stored in memory *and* written back to ``.env``.
4.  All subsequent API/MCP calls will use those tokens automatically.
"""

from __future__ import annotations

import urllib.parse
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse

from strava_mcp.client.auth import token_manager, _STRAVA_TOKEN_URL, _STRAVA_DEAUTH_URL
from strava_mcp.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])

_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
_DEFAULT_SCOPES = "activity:read_all,read_all"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_auth_url(redirect_uri: str, scopes: str, state: str = "") -> str:
    params: Dict[str, str] = {
        "client_id": settings.strava_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": scopes,
    }
    if state:
        params["state"] = state
    return f"{_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get(
    "/login",
    summary="Start Strava OAuth flow",
    response_description="The Strava authorization URL to open in a browser.",
)
async def login(
    redirect_uri: str = Query(
        default="http://localhost:8000/auth/callback",
        description="URI Strava will redirect to after authorization. Must match your app settings.",
    ),
    scope: str = Query(
        default=_DEFAULT_SCOPES,
        description="Comma-separated Strava OAuth scopes.",
    ),
    state: str = Query(
        default="", description="Optional opaque state string returned unchanged."
    ),
) -> Dict[str, str]:
    """Return the Strava authorization URL.

    Open ``auth_url`` in a browser to start the OAuth flow. After the user
    grants access, Strava will redirect to ``redirect_uri`` with a ``code``
    query parameter — which ``GET /auth/callback`` handles automatically.
    """
    auth_url = _build_auth_url(redirect_uri=redirect_uri, scopes=scope, state=state)
    return {
        "auth_url": auth_url,
        "instructions": (
            "Open auth_url in a browser, log in to Strava, and grant access. "
            "If using the default redirect_uri this server will handle the callback automatically."
        ),
    }


@router.get(
    "/callback",
    summary="OAuth callback – exchange code for tokens",
    response_description="Authentication result including athlete summary.",
)
async def callback(
    code: str = Query(..., description="Authorization code returned by Strava."),
    scope: str = Query(default="", description="Scopes granted by the user."),
    state: str = Query(
        default="", description="State parameter echoed back from Strava."
    ),
    error: str = Query(
        default="", description="Set by Strava if the user denied access."
    ),
) -> Dict[str, Any]:
    """Handle the OAuth redirect from Strava.

    Exchanges the authorization ``code`` for an access token and refresh token.
    Tokens are stored in the ``TokenManager`` singleton and written to ``.env``
    so subsequent server restarts remain authenticated.

    This endpoint is intended to be hit automatically by the browser redirect
    after a successful ``/auth/login`` flow.
    """
    if error:
        raise HTTPException(
            status_code=403, detail=f"Strava authorization denied: {error}"
        )

    payload = {
        "client_id": settings.strava_client_id,
        "client_secret": settings.strava_client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=15) as http:
        response = await http.post(_STRAVA_TOKEN_URL, data=payload)

    if response.status_code != 200:
        try:
            detail: Any = response.json()
        except Exception:
            detail = response.text
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Token exchange failed: {detail}",
        )

    data = response.json()
    access_token: str = data["access_token"]
    refresh_token: str = data["refresh_token"]
    expires_at: float = float(data["expires_at"])
    athlete: Dict[str, Any] = data.get("athlete", {})

    # Inject into the live token manager (and persist to .env)
    token_manager.set_tokens(
        access_token=access_token,
        refresh_token=refresh_token,
        token_expiry=expires_at,
    )

    name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    return {
        "status": "authenticated",
        "athlete": name or "unknown",
        "athlete_id": athlete.get("id"),
        "scopes_granted": scope,
        "expires_at": expires_at,
        "message": "Tokens saved. You may now use all Strava API and MCP tools.",
    }


@router.get(
    "/status",
    summary="Check authentication status",
    response_description="Current authentication state.",
)
async def status() -> Dict[str, Any]:
    """Return whether the application currently has valid Strava credentials."""
    authenticated = token_manager.is_authenticated()
    result: Dict[str, Any] = {
        "authenticated": authenticated,
    }
    if authenticated:
        import time

        remaining = max(0.0, token_manager._token_expiry - time.time())
        result["access_token_expires_in_seconds"] = int(remaining)
        result["access_token_valid"] = remaining > 0
    else:
        result["message"] = (
            "Not authenticated. Call GET /auth/login to get the authorization URL, "
            "then open it in a browser to complete the OAuth flow."
        )
    return result


@router.post(
    "/deauthorize",
    summary="Revoke Strava access",
    response_description="Confirmation that access has been revoked.",
)
async def deauthorize() -> Dict[str, str]:
    """Revoke the application's Strava access.

    - Calls Strava's deauthorization endpoint (invalidates all tokens server-side).
    - Clears all stored tokens from memory and ``.env``.

    After calling this, a new OAuth flow (``/auth/login``) is required.
    """
    if not token_manager.is_authenticated():
        raise HTTPException(status_code=400, detail="Not currently authenticated.")

    # Best-effort call to Strava's deauth endpoint
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            await http.post(
                _STRAVA_DEAUTH_URL,
                data={"access_token": token_manager._access_token},
            )
    except Exception:
        pass  # Even if this fails, clear local tokens

    token_manager.deauthorize()

    return {
        "status": "deauthorized",
        "message": "All tokens cleared. Call /auth/login to re-authenticate.",
    }
