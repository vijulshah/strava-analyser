"""Request schemas for analysis endpoints.

Every analysis endpoint accepts a strongly-typed Pydantic body so the
Swagger UI displays the full request structure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from strava_mcp.models.filters import TimeRangePreset


class PeriodRequest(BaseModel):
    """Base request with a single time-range period."""

    preset: TimeRangePreset = Field(
        TimeRangePreset.LAST_30_DAYS,
        description="Pre-defined time range for the analysis.",
    )
    after_date: Optional[datetime] = Field(
        None, description="Custom start date (preset='custom' only)."
    )
    before_date: Optional[datetime] = Field(
        None, description="Custom end date (preset='custom' only)."
    )
    sport_type: Optional[str] = Field(
        None,
        description="Limit analysis to this sport type (e.g. 'Run', 'Ride').",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_30_days",
                "sport_type": "Run",
            }
        }
    }


class SummaryRequest(PeriodRequest):
    """Request body for ``POST /analysis/summary``."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_30_days",
                "sport_type": "Run",
            }
        }
    }


class PerformanceTrendRequest(PeriodRequest):
    """Request body for ``POST /analysis/performance-trend``."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_3_months",
                "sport_type": "Run",
            }
        }
    }


class HRZoneRequest(PeriodRequest):
    """Request body for ``POST /analysis/hr-zones``."""

    max_hr: int = Field(
        190,
        ge=100,
        le=220,
        description="Athlete maximum HR for zone boundary calculation.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_30_days",
                "sport_type": "Run",
                "max_hr": 190,
            }
        }
    }


class PowerZoneRequest(PeriodRequest):
    """Request body for ``POST /analysis/power``."""

    ftp: int = Field(
        200,
        ge=50,
        le=600,
        description="Athlete Functional Threshold Power (FTP) in watts.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_30_days",
                "sport_type": "Ride",
                "ftp": 250,
            }
        }
    }


class PersonalRecordsRequest(PeriodRequest):
    """Request body for ``POST /analysis/personal-records``."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "all_time",
                "sport_type": "Run",
            }
        }
    }


class SegmentComparisonRequest(BaseModel):
    """Request body for ``POST /analysis/segment-comparison``."""

    segment_id: int = Field(..., description="Strava segment ID to compare efforts on.")
    after_date: Optional[datetime] = Field(
        None, description="Only include efforts after this date."
    )
    before_date: Optional[datetime] = Field(
        None, description="Only include efforts before this date."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "segment_id": 12345678,
            }
        }
    }


class ComparePeriodRequest(BaseModel):
    """Request body for ``POST /analysis/compare-periods``."""

    preset_a: TimeRangePreset = Field(
        TimeRangePreset.LAST_30_DAYS, description="First period."
    )
    after_a: Optional[datetime] = Field(None, description="Custom start for period A.")
    before_a: Optional[datetime] = Field(None, description="Custom end for period A.")
    preset_b: TimeRangePreset = Field(
        TimeRangePreset.LAST_YEAR, description="Second period for comparison."
    )
    after_b: Optional[datetime] = Field(None, description="Custom start for period B.")
    before_b: Optional[datetime] = Field(None, description="Custom end for period B.")
    sport_type: Optional[str] = Field(
        None, description="Restrict comparison to this sport type."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset_a": "last_30_days",
                "preset_b": "last_year",
                "sport_type": "Run",
            }
        }
    }


class WeeklyBreakdownRequest(PeriodRequest):
    """Request body for ``POST /analysis/weekly-breakdown``."""

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_3_months",
                "sport_type": None,
            }
        }
    }


class ActivityInsightRequest(BaseModel):
    """Request body for ``POST /analysis/activity-insight``."""

    activity_id: int = Field(..., description="Strava activity ID to analyse.")
    max_hr: int = Field(
        190, ge=100, le=220, description="Athlete max HR for zone analysis."
    )
    ftp: int = Field(
        200, ge=50, le=600, description="Athlete FTP for power zone analysis."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "activity_id": 9876543210,
                "max_hr": 185,
                "ftp": 240,
            }
        }
    }
