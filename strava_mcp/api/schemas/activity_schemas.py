"""Request/response schemas for activity-related endpoints.

All schemas are Pydantic v2 models with ``json_schema_extra`` examples so
the FastAPI Swagger UI renders richly annotated request bodies.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from strava_mcp.models.activity import SportType
from strava_mcp.models.filters import TimeRangePreset


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ListActivitiesRequest(BaseModel):
    """Query parameters for ``GET /activities``."""

    preset: TimeRangePreset = Field(
        TimeRangePreset.LAST_30_DAYS,
        description="Pre-defined time range for filtering activities.",
    )
    after_date: Optional[datetime] = Field(
        None,
        description="Custom start date in ISO 8601. Required when preset='custom'.",
    )
    before_date: Optional[datetime] = Field(
        None,
        description="Custom end date in ISO 8601. Defaults to now when preset='custom'.",
    )
    sport_type: Optional[SportType] = Field(
        None,
        description="Filter by sport type. Leave blank for all sport types.",
    )
    per_page: int = Field(
        30,
        ge=1,
        le=200,
        description="Number of activities per page (1–200, default 30).",
    )
    page: int = Field(1, ge=1, description="Page number (1-based).")

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_7_days",
                "sport_type": "Run",
                "per_page": 30,
                "page": 1,
            }
        }
    }


class CreateActivityBody(BaseModel):
    """Body for ``POST /activities`` – create a manual activity."""

    name: str = Field(..., description="Activity name")
    sport_type: SportType = Field(..., description="Sport type")
    start_date_local: datetime = Field(..., description="Local start time (ISO 8601)")
    elapsed_time: int = Field(..., ge=1, description="Elapsed time in seconds")
    description: Optional[str] = Field(None, description="Optional description")
    distance: Optional[float] = Field(None, ge=0, description="Distance in metres")
    trainer: Optional[int] = Field(None, description="1 = trainer/indoor activity")
    commute: Optional[int] = Field(None, description="1 = commute")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Morning Run",
                "sport_type": "Run",
                "start_date_local": "2024-03-01T07:30:00Z",
                "elapsed_time": 3600,
                "distance": 10000.0,
                "description": "Easy 10 km",
            }
        }
    }


class UpdateActivityBody(BaseModel):
    """Body for ``PUT /activities/{id}`` – update an activity."""

    name: Optional[str] = Field(None, description="New activity name")
    sport_type: Optional[SportType] = Field(None, description="New sport type")
    description: Optional[str] = Field(None, description="New description")
    commute: Optional[bool] = Field(None, description="Mark as commute")
    trainer: Optional[bool] = Field(None, description="Mark as trainer activity")
    hide_from_home: Optional[bool] = Field(None, description="Hide from home feed")
    gear_id: Optional[str] = Field(None, description="Gear ID (pass 'none' to clear)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Evening Run",
                "commute": False,
                "description": "Updated description",
            }
        }
    }


class GetStreamsRequest(BaseModel):
    """Body for ``POST /activities/{id}/streams``."""

    keys: List[str] = Field(
        default=["time", "heartrate", "altitude", "distance", "velocity_smooth"],
        description="Stream types to fetch.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "keys": ["time", "heartrate", "watts", "cadence", "latlng", "altitude"]
            }
        }
    }
