"""Strava API models – Stats, Filters, Streams, Gear, Club, Route, Uploads."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from strava_mcp.models.activity import LatLng, PolylineMap, SummaryGear
from strava_mcp.models.athlete import SummaryAthlete, SummaryClub
from strava_mcp.models.segment import SummarySegment


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class ActivityTotal(BaseModel):
    """Roll-up of activity metrics (used in ActivityStats)."""

    count: Optional[int] = Field(None, description="Number of activities")
    distance: Optional[float] = Field(None, description="Total distance in meters")
    moving_time: Optional[int] = Field(None, description="Total moving time seconds")
    elapsed_time: Optional[int] = Field(None, description="Total elapsed time seconds")
    elevation_gain: Optional[float] = Field(None, description="Total elevation gain meters")
    achievement_count: Optional[int] = Field(None, description="Total achievements")


class ActivityStats(BaseModel):
    """Rolled-up athlete statistics (recent 4 weeks, YTD, all-time)."""

    biggest_ride_distance: Optional[float] = Field(None, description="Longest ride in meters")
    biggest_climb_elevation_gain: Optional[float] = Field(
        None, description="Biggest single climb elevation gain (m)"
    )
    recent_ride_totals: Optional[ActivityTotal] = Field(None, description="Last 4 weeks rides")
    recent_run_totals: Optional[ActivityTotal] = Field(None, description="Last 4 weeks runs")
    recent_swim_totals: Optional[ActivityTotal] = Field(None, description="Last 4 weeks swims")
    ytd_ride_totals: Optional[ActivityTotal] = Field(None, description="Year-to-date rides")
    ytd_run_totals: Optional[ActivityTotal] = Field(None, description="Year-to-date runs")
    ytd_swim_totals: Optional[ActivityTotal] = Field(None, description="Year-to-date swims")
    all_ride_totals: Optional[ActivityTotal] = Field(None, description="All-time rides")
    all_run_totals: Optional[ActivityTotal] = Field(None, description="All-time runs")
    all_swim_totals: Optional[ActivityTotal] = Field(None, description="All-time swims")


# ---------------------------------------------------------------------------
# Gear
# ---------------------------------------------------------------------------


class DetailedGear(SummaryGear):
    """Full gear details."""

    brand_name: Optional[str] = None
    model_name: Optional[str] = None
    frame_type: Optional[int] = Field(
        None, description="Frame type (bikes): 1=MTB, 2=Cross, 3=Road, 4=TT"
    )
    description: Optional[str] = None
    nickname: Optional[str] = None


# ---------------------------------------------------------------------------
# Club
# ---------------------------------------------------------------------------


class ClubActivity(BaseModel):
    """Activity in a club feed."""

    athlete: Optional[SummaryAthlete] = None
    name: Optional[str] = None
    distance: Optional[float] = None
    moving_time: Optional[int] = None
    elapsed_time: Optional[int] = None
    total_elevation_gain: Optional[float] = None
    sport_type: Optional[str] = None
    workout_type: Optional[int] = None


class DetailedClub(SummaryClub):
    """Full club representation."""

    description: Optional[str] = None
    club_type: Optional[str] = None
    membership: Optional[str] = Field(None, description="'member', 'pending', or null")
    admin: Optional[bool] = None
    owner: Optional[bool] = None
    following_count: Optional[int] = Field(
        None, description="Followers who are also club members"
    )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


class Waypoint(BaseModel):
    """Named waypoint on a route."""

    latlng: Optional[LatLng] = None
    title: Optional[str] = None
    description: Optional[str] = None
    distance_into_route: Optional[float] = None


class MapUrls(BaseModel):
    """Static map image URLs."""

    url: Optional[str] = None
    retina_url: Optional[str] = None


class Route(BaseModel):
    """A saved route."""

    id: int = Field(..., description="Route identifier")
    id_str: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    athlete: Optional[SummaryAthlete] = None
    distance: Optional[float] = Field(None, description="Total distance in meters")
    elevation_gain: Optional[float] = Field(None, description="Elevation gain in meters")
    map: Optional[PolylineMap] = None
    map_urls: Optional[MapUrls] = None
    type: Optional[int] = Field(None, description="1=cycling, 2=running")
    sub_type: Optional[int] = Field(
        None, description="1=road, 2=MTB, 3=CX, 4=trail, 5=mixed"
    )
    private: Optional[bool] = None
    starred: Optional[bool] = None
    timestamp: Optional[int] = None
    waypoints: Optional[List[Waypoint]] = None
    segments: Optional[List[SummarySegment]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    resource_state: int = Field(default=2)


# ---------------------------------------------------------------------------
# Streams
# ---------------------------------------------------------------------------


class BaseStream(BaseModel):
    """Common fields for all stream types."""

    original_size: Optional[int] = Field(None, description="Total data points before resampling")
    resolution: Optional[str] = Field(None, description="'low', 'medium', or 'high'")
    series_type: Optional[str] = Field(None, description="'time' or 'distance'")


class TimeStream(BaseStream):
    """Elapsed seconds from activity start."""
    data: List[int] = Field(default_factory=list)


class DistanceStream(BaseStream):
    """Distance from start in meters."""
    data: List[float] = Field(default_factory=list)


class LatLngStream(BaseStream):
    """GPS coordinate pairs [latitude, longitude]."""
    data: List[List[float]] = Field(default_factory=list)


class AltitudeStream(BaseStream):
    """Altitude above sea level in meters."""
    data: List[float] = Field(default_factory=list)


class SmoothVelocityStream(BaseStream):
    """Smoothed speed in m/s."""
    data: List[float] = Field(default_factory=list)


class HeartrateStream(BaseStream):
    """Heart rate in bpm."""
    data: List[int] = Field(default_factory=list)


class CadenceStream(BaseStream):
    """Cadence in rpm (cycling) or steps/min (running)."""
    data: List[int] = Field(default_factory=list)


class PowerStream(BaseStream):
    """Power output in watts."""
    data: List[int] = Field(default_factory=list)


class TemperatureStream(BaseStream):
    """Temperature in Celsius."""
    data: List[int] = Field(default_factory=list)


class MovingStream(BaseStream):
    """Boolean moving flags."""
    data: List[bool] = Field(default_factory=list)


class SmoothGradeStream(BaseStream):
    """Smoothed gradient percentage."""
    data: List[float] = Field(default_factory=list)


class StreamSet(BaseModel):
    """Set of time-series streams keyed by stream type."""

    time: Optional[TimeStream] = None
    distance: Optional[DistanceStream] = None
    latlng: Optional[LatLngStream] = None
    altitude: Optional[AltitudeStream] = None
    velocity_smooth: Optional[SmoothVelocityStream] = None
    heartrate: Optional[HeartrateStream] = None
    cadence: Optional[CadenceStream] = None
    watts: Optional[PowerStream] = None
    temp: Optional[TemperatureStream] = None
    moving: Optional[MovingStream] = None
    grade_smooth: Optional[SmoothGradeStream] = None


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class Upload(BaseModel):
    """Status of an activity upload."""

    id: Optional[int] = None
    id_str: Optional[str] = None
    external_id: Optional[str] = None
    error: Optional[str] = None
    status: Optional[str] = None
    activity_id: Optional[int] = Field(None, description="Created activity ID (null while processing)")


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


class TimeRangePreset(str, Enum):
    """Pre-defined time range options for filtering activities."""

    TODAY = "today"
    LAST_7_DAYS = "last_7_days"
    LAST_14_DAYS = "last_14_days"
    LAST_30_DAYS = "last_30_days"
    LAST_3_MONTHS = "last_3_months"
    LAST_6_MONTHS = "last_6_months"
    LAST_YEAR = "last_year"
    THIS_YEAR = "this_year"
    ALL_TIME = "all_time"
    CUSTOM = "custom"


class ActivityFilter(BaseModel):
    """Filter options for listing activities."""

    preset: TimeRangePreset = Field(
        TimeRangePreset.LAST_30_DAYS,
        description="Pre-defined time range preset",
    )
    after_date: Optional[datetime] = Field(
        None, description="Custom start date (used when preset=custom)"
    )
    before_date: Optional[datetime] = Field(
        None, description="Custom end date (used when preset=custom)"
    )
    sport_type: Optional[str] = Field(
        None, description="Filter by sport type (e.g. Run, Ride, Swim)"
    )
    per_page: int = Field(
        default=30, ge=1, le=200, description="Items per page (max 200)"
    )
    page: int = Field(default=1, ge=1, description="Page number")

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
