"""FastAPI application entry point.

Run with::

    uvicorn strava_mcp.api.main:app --reload --port 8000

Then open http://localhost:8000/docs for the Swagger UI.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from strava_mcp.api.routers import (
    activities,
    analysis,
    athlete,
    auth,
    clubs,
    gear,
    routes,
    segments,
    streams,
)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan – startup / shutdown hooks."""
    from strava_mcp.client.auth import token_manager
    from strava_mcp.config import settings  # noqa: F401
    import sys

    if token_manager.is_authenticated():
        print("[strava-mcp] ✓ Authenticated with Strava.", file=sys.stderr)
    else:
        print(
            "[strava-mcp] ⚠  No refresh token found. "
            "Open http://localhost:8000/auth/login to authenticate.",
            file=sys.stderr,
        )
    yield
    # Cleanup (none needed for now)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Strava MCP API",
    description=(
        "Full-featured REST API wrapping the Strava API v3 with rich filtering, "
        "analysis endpoints, and Pydantic-typed request/response schemas.\n\n"
        "## Authentication\n"
        "Configure your Strava OAuth credentials in the `.env` file before starting the server.\n\n"
        "## Time Range Presets\n"
        "All list and analysis endpoints support these presets:\n"
        "`today` | `last_7_days` | `last_14_days` | `last_30_days` | "
        "`last_3_months` | `last_6_months` | `last_year` | `this_year` | `all_time` | `custom`"
    ),
    version="1.0.0",
    lifespan=lifespan,
    contact={"name": "Strava MCP", "url": "https://github.com/strava-mcp"},
    openapi_tags=[
        {
            "name": "Auth",
            "description": "Strava OAuth2 flow: login, callback, status, and deauthorize.",
        },
        {"name": "Athlete", "description": "Athlete profile, zones, and statistics."},
        {
            "name": "Activities",
            "description": "List, create, update, and analyse activities.",
        },
        {
            "name": "Segments",
            "description": "Segment details, starred segments, efforts, and exploration.",
        },
        {
            "name": "Clubs",
            "description": "Club membership, activity feed, and member list.",
        },
        {"name": "Routes", "description": "Saved route listing and details."},
        {"name": "Gear", "description": "Gear (bikes and shoes) details."},
        {
            "name": "Streams",
            "description": "Raw telemetry streams (GPS, HR, power, cadence, etc.).",
        },
        {
            "name": "Analysis",
            "description": "Cross-activity analysis: trends, HR zones, PRs, comparisons, and weekly breakdowns.",
        },
    ],
)

# CORS – allow all origins in development; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a JSON error response for unhandled exceptions."""
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        try:
            detail: Any = exc.response.json()
        except Exception:
            detail = exc.response.text
        return JSONResponse(
            status_code=status_code,
            content={"error": "Strava API error", "detail": detail},
        )

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)
app.include_router(athlete.router)
app.include_router(activities.router)
app.include_router(segments.router)
app.include_router(clubs.router)
app.include_router(routes.router)
app.include_router(gear.router)
app.include_router(streams.router)
app.include_router(analysis.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["Health"], summary="Health check")
async def health_check() -> Dict[str, str]:
    """Return service health status."""
    return {"status": "ok", "service": "strava-mcp-api"}
