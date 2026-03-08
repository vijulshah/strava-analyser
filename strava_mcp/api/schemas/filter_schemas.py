"""Filter query-parameter schemas for list endpoints.

These are used as ``Depends(...)`` in route functions so that FastAPI
exposes them as query parameters in the Swagger UI.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field

from strava_mcp.models.filters import TimeRangePreset


class ActivityQueryParams(BaseModel):
    """Query parameters for ``GET /activities``.

    Usage in route::

        @router.get("/activities")
        async def list_activities(params: ActivityQueryParams = Depends()):
            ...
    """

    preset: TimeRangePreset = Field(
        TimeRangePreset.LAST_30_DAYS,
        description="Pre-defined time range (today/last_7_days/last_14_days/…/all_time/custom).",
    )
    after_date: Optional[datetime] = Field(
        None,
        description="Custom start date (ISO 8601). Required when preset='custom'.",
    )
    before_date: Optional[datetime] = Field(
        None,
        description="Custom end date (ISO 8601). Defaults to now when preset='custom'.",
    )
    sport_type: Optional[str] = Field(
        None,
        description="Filter by sport type, e.g. 'Run', 'Ride', 'Swim'.",
    )
    per_page: int = Field(30, ge=1, le=200, description="Results per page (max 200).")
    page: int = Field(1, ge=1, description="Page number (1-based).")

    model_config = {"extra": "forbid"}
