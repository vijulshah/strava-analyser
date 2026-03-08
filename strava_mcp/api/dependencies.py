"""Shared FastAPI dependency providers.

Import ``get_client`` in route functions to obtain a fully-initialised
:class:`~strava_mcp.client.base.StravaClient` that is closed after the
request completes.
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import HTTPException, status

from strava_mcp.client.base import StravaClient
from strava_mcp.config import settings


async def get_client() -> AsyncGenerator[StravaClient, None]:
    """FastAPI dependency that yields an authenticated :class:`StravaClient`.

    Yields:
        An open :class:`StravaClient` instance.

    Raises:
        HTTPException: 503 if Strava credentials are not configured.
    """
    try:
        async with StravaClient() as client:
            yield client
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Strava client error: {exc}",
        ) from exc
