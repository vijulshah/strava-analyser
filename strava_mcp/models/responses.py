"""Pydantic response models for analysis endpoints and MCP tool outputs.

Every analysis function returns one of these typed response objects so that
both the FastAPI Swagger UI and the MCP tool layer have rich, structured
output definitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared building-blocks
# ---------------------------------------------------------------------------


class PeriodLabel(BaseModel):
    """Human-readable label + epoch bounds for a time period."""

    label: str = Field(..., description="Human-readable label, e.g. 'Last 30 days'")
    after: Optional[int] = Field(None, description="Unix epoch start (inclusive)")
    before: Optional[int] = Field(None, description="Unix epoch end (exclusive)")


class SportBreakdown(BaseModel):
    """Per-sport aggregated metrics."""

    sport_type: str = Field(..., description="Sport type name, e.g. 'Run'")
    count: int = Field(..., description="Number of activities")
    total_distance_m: float = Field(..., description="Total distance in metres")
    total_moving_time_s: int = Field(..., description="Total moving time in seconds")
    total_elevation_gain_m: float = Field(..., description="Total elevation gain in metres")
    avg_distance_m: float = Field(..., description="Average distance per activity in metres")
    avg_moving_time_s: float = Field(..., description="Average moving time per activity in seconds")


# ---------------------------------------------------------------------------
# Activity Summary / Aggregation
# ---------------------------------------------------------------------------


class AggregatedStatsResponse(BaseModel):
    """Aggregated statistics across a set of activities.

    Returned by ``POST /analysis/summary`` and the
    ``analyze_period_summary`` MCP tool.
    """

    period: PeriodLabel
    total_activities: int = Field(..., description="Total number of activities in period")
    total_distance_m: float = Field(..., description="Total distance in metres")
    total_distance_km: float = Field(..., description="Total distance in kilometres")
    total_moving_time_s: int = Field(..., description="Total moving time in seconds")
    total_moving_time_formatted: str = Field(..., description="Moving time as HH:MM:SS")
    total_elevation_gain_m: float = Field(..., description="Total elevation gain in metres")
    total_calories: Optional[float] = Field(None, description="Total estimated calories")
    avg_distance_km: float = Field(..., description="Average distance per activity in km")
    avg_moving_time_s: float = Field(..., description="Average moving time per activity")
    avg_elevation_gain_m: float = Field(..., description="Average elevation gain per activity")
    sport_breakdown: List[SportBreakdown] = Field(
        default_factory=list, description="Breakdown by sport type"
    )
    total_kudos: int = Field(default=0, description="Total kudos received")
    total_achievements: int = Field(default=0, description="Total achievements earned")

    model_config = {
        "json_schema_extra": {
            "example": {
                "period": {"label": "Last 30 days", "after": 1700000000, "before": None},
                "total_activities": 12,
                "total_distance_m": 98000,
                "total_distance_km": 98.0,
                "total_moving_time_s": 36000,
                "total_moving_time_formatted": "10:00:00",
                "total_elevation_gain_m": 1200,
                "total_calories": 5800,
                "avg_distance_km": 8.17,
                "avg_moving_time_s": 3000,
                "avg_elevation_gain_m": 100,
                "sport_breakdown": [],
            }
        }
    }


# ---------------------------------------------------------------------------
# Performance Trend
# ---------------------------------------------------------------------------


class ActivityDataPoint(BaseModel):
    """One activity represented as a trend data point."""

    activity_id: int
    name: str
    date: datetime
    sport_type: Optional[str] = None
    distance_km: Optional[float] = None
    moving_time_s: Optional[int] = None
    avg_speed_kmh: Optional[float] = None
    avg_pace_min_per_km: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    avg_heartrate: Optional[float] = None
    avg_watts: Optional[float] = None
    suffer_score: Optional[float] = None


class PerformanceTrendResponse(BaseModel):
    """Performance trend across a series of activities.

    Returned by ``POST /analysis/performance-trend`` and the
    ``analyze_performance_trend`` MCP tool.
    """

    period: PeriodLabel
    sport_type: Optional[str] = Field(None, description="Sport type filtered, or None for all")
    data_points: List[ActivityDataPoint] = Field(
        default_factory=list, description="Ordered list of activity data points"
    )
    trend_distance_km: Optional[float] = Field(
        None, description="Linear trend slope (km per week). Positive = improving volume."
    )
    trend_avg_speed_kmh: Optional[float] = Field(
        None, description="Linear trend slope (km/h per week). Positive = getting faster."
    )
    trend_avg_heartrate: Optional[float] = Field(
        None, description="Linear trend slope (bpm per week). Negative = improving efficiency."
    )
    best_distance_km: Optional[float] = None
    worst_distance_km: Optional[float] = None
    best_avg_speed_kmh: Optional[float] = None
    worst_avg_speed_kmh: Optional[float] = None
    total_activities: int = Field(default=0)


# ---------------------------------------------------------------------------
# Heart Rate Zone Analysis
# ---------------------------------------------------------------------------


class HRZoneBucket(BaseModel):
    """Seconds spent in a single HR zone."""

    zone: int = Field(..., description="Zone number (1–5)")
    label: str = Field(..., description="Zone label, e.g. 'Zone 2 – Aerobic'")
    min_hr: Optional[int] = Field(None, description="Minimum HR for this zone")
    max_hr: Optional[int] = Field(None, description="Maximum HR for this zone (-1=unlimited)")
    seconds: int = Field(..., description="Total seconds in zone")
    percentage: float = Field(..., description="Percentage of total tracked time")
    formatted_time: str = Field(..., description="Human-readable time string, e.g. '1h 23m'")


class HRZoneAnalysisResponse(BaseModel):
    """Heart rate zone distribution across a period or a single activity.

    Returned by ``POST /analysis/hr-zones`` and the
    ``analyze_hr_zones`` MCP tool.
    """

    period: PeriodLabel
    sport_type: Optional[str] = None
    activities_with_hr: int = Field(..., description="Number of activities with HR data")
    total_tracked_seconds: int = Field(..., description="Total seconds with HR data")
    zones: List[HRZoneBucket] = Field(default_factory=list, description="5 HR zones")
    avg_heartrate: Optional[float] = Field(None, description="Overall average HR")
    max_heartrate_recorded: Optional[float] = Field(None, description="Highest HR recorded")


# ---------------------------------------------------------------------------
# Power Analysis
# ---------------------------------------------------------------------------


class PowerZoneBucket(BaseModel):
    """Time spent in a single power zone."""

    zone: int
    label: str
    min_watts: Optional[int] = None
    max_watts: Optional[int] = None
    seconds: int
    percentage: float
    formatted_time: str


class PowerAnalysisResponse(BaseModel):
    """Power zone distribution and key power metrics.

    Returned by ``POST /analysis/power`` and the
    ``analyze_power_zones`` MCP tool.
    """

    period: PeriodLabel
    sport_type: Optional[str] = None
    activities_with_power: int
    ftp: Optional[int] = Field(None, description="Athlete FTP used for zone calculation")
    zones: List[PowerZoneBucket] = Field(default_factory=list)
    avg_weighted_power: Optional[float] = Field(None, description="Average normalised power (W)")
    avg_power: Optional[float] = Field(None, description="Simple average power (W)")
    max_power_recorded: Optional[float] = None
    total_kilojoules: Optional[float] = None


# ---------------------------------------------------------------------------
# Personal Records
# ---------------------------------------------------------------------------


class PersonalRecord(BaseModel):
    """A single personal record entry."""

    sport_type: str
    metric: str = Field(..., description="e.g. 'longest_distance', 'fastest_pace', 'best_5k'")
    value: float
    unit: str = Field(..., description="Unit of the value, e.g. 'km', 'min/km', 's'")
    value_formatted: str = Field(..., description="Human-readable formatted value")
    activity_id: int
    activity_name: str
    date: datetime


class PersonalRecordsResponse(BaseModel):
    """Personal records across all activities or within a period.

    Returned by ``POST /analysis/personal-records`` and the
    ``find_personal_records`` MCP tool.
    """

    period: PeriodLabel
    sport_type: Optional[str] = None
    records: List[PersonalRecord] = Field(default_factory=list)
    total_activities_analysed: int = Field(default=0)


# ---------------------------------------------------------------------------
# Segment Comparison
# ---------------------------------------------------------------------------


class SegmentEffortSummary(BaseModel):
    """One effort on a segment."""

    effort_id: int
    activity_id: Optional[int] = None
    date: Optional[datetime] = None
    elapsed_time_s: int
    elapsed_time_formatted: str
    rank: int = Field(..., description="1 = fastest effort (PR)")
    is_pr: bool = False
    is_kom: bool = False
    avg_watts: Optional[float] = None
    avg_heartrate: Optional[float] = None


class SegmentComparisonResponse(BaseModel):
    """All efforts on a segment, ranked fastest to slowest.

    Returned by ``POST /analysis/segment-comparison`` and the
    ``compare_segment_efforts`` MCP tool.
    """

    segment_id: int
    segment_name: Optional[str] = None
    distance_m: Optional[float] = None
    total_efforts: int
    pr_elapsed_time_s: Optional[int] = None
    pr_elapsed_time_formatted: Optional[str] = None
    pr_date: Optional[datetime] = None
    efforts: List[SegmentEffortSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Weekly / Monthly Breakdown
# ---------------------------------------------------------------------------


class WeekSummary(BaseModel):
    """Metrics for one calendar week."""

    week_start: datetime = Field(..., description="Monday of the week (UTC midnight)")
    week_label: str = Field(..., description="e.g. 'W1 – Jan 1–7'")
    count: int
    total_distance_km: float
    total_moving_time_s: int
    total_elevation_gain_m: float
    sport_breakdown: List[SportBreakdown] = Field(default_factory=list)


class WeeklyBreakdownResponse(BaseModel):
    """Week-over-week breakdown for a given period.

    Returned by ``POST /analysis/weekly-breakdown`` and the
    ``analyze_weekly_breakdown`` MCP tool.
    """

    period: PeriodLabel
    sport_type: Optional[str] = None
    weeks: List[WeekSummary] = Field(default_factory=list)
    total_weeks: int
    busiest_week_label: Optional[str] = None
    busiest_week_distance_km: Optional[float] = None
    quietest_week_label: Optional[str] = None
    avg_weekly_distance_km: Optional[float] = None


# ---------------------------------------------------------------------------
# Period Comparison
# ---------------------------------------------------------------------------


class PeriodMetrics(BaseModel):
    """Key aggregate metrics for one period."""

    period: PeriodLabel
    total_activities: int
    total_distance_km: float
    total_moving_time_s: int
    total_elevation_gain_m: float
    avg_distance_km: float
    avg_pace_min_per_km: Optional[float] = None
    avg_heartrate: Optional[float] = None


class PeriodComparisonResponse(BaseModel):
    """Side-by-side comparison of two time periods.

    Returned by ``POST /analysis/compare-periods`` and the
    ``compare_periods`` MCP tool.
    """

    period_a: PeriodMetrics
    period_b: PeriodMetrics
    distance_change_pct: Optional[float] = Field(
        None, description="% change in total distance from A to B"
    )
    activity_count_change_pct: Optional[float] = None
    elevation_change_pct: Optional[float] = None
    pace_change_pct: Optional[float] = None
    summary: str = Field(
        default="", description="Human-readable summary of the comparison"
    )


# ---------------------------------------------------------------------------
# Single Activity Insight
# ---------------------------------------------------------------------------


class ActivityInsightResponse(BaseModel):
    """Smart analytical summary of a single activity.

    Returned by ``POST /analysis/activity-insight`` and the
    ``get_activity_insights`` MCP tool.
    """

    activity_id: int
    name: str
    sport_type: Optional[str] = None
    date: Optional[datetime] = None
    distance_km: Optional[float] = None
    moving_time_formatted: Optional[str] = None
    avg_speed_kmh: Optional[float] = None
    avg_pace_min_per_km: Optional[float] = None
    avg_heartrate: Optional[float] = None
    max_heartrate: Optional[float] = None
    avg_watts: Optional[float] = None
    weighted_avg_watts: Optional[float] = None
    elevation_gain_m: Optional[float] = None
    calories: Optional[float] = None
    suffer_score: Optional[float] = None
    perceived_exertion: Optional[float] = None
    achievements: Optional[int] = None
    kudos: Optional[int] = None
    pr_count: Optional[int] = None
    hr_zone_distribution: Optional[List[HRZoneBucket]] = None
    power_zone_distribution: Optional[List[PowerZoneBucket]] = None
    lap_count: Optional[int] = None
    highlights: List[str] = Field(
        default_factory=list,
        description="Key highlights about this activity as bullet strings",
    )
    gear_name: Optional[str] = None
    device_name: Optional[str] = None
