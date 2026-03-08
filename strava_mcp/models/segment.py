"""Strava API models – Segments & SegmentEfforts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from strava_mcp.models.activity import LatLng, MetaActivity, MetaAthlete, PolylineMap


class SummarySegment(BaseModel):
    """Summary representation of a Strava segment."""

    id: int = Field(..., description="Segment identifier")
    name: Optional[str] = None
    activity_type: Optional[str] = Field(None, description="'Ride' or 'Run'")
    distance: Optional[float] = Field(None, description="Distance in meters")
    average_grade: Optional[float] = Field(None, description="Average gradient %")
    maximum_grade: Optional[float] = None
    elevation_high: Optional[float] = None
    elevation_low: Optional[float] = None
    start_latlng: Optional[LatLng] = None
    end_latlng: Optional[LatLng] = None
    climb_category: Optional[int] = Field(None, description="0=NC, 1=Cat4 … 5=HC")
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    private: Optional[bool] = None
    hazardous: Optional[bool] = None
    starred: Optional[bool] = None
    resource_state: int = Field(default=2)


class Xoms(BaseModel):
    """KOM / QOM holder times."""

    kom: Optional[str] = Field(None, description="KOM time string")
    qom: Optional[str] = Field(None, description="QOM time string")
    destination: Optional[Any] = None


class LocalLegend(BaseModel):
    """Segment local legend info."""

    athlete_id: Optional[int] = None
    title: Optional[str] = None
    profile: Optional[str] = None
    effort_description: Optional[str] = None
    effort_count: Optional[str] = None
    effort_counts: Optional[Any] = None
    destination: Optional[Any] = None


class SummarySegmentEffort(BaseModel):
    """An athlete's best effort on a segment."""

    id: Optional[int] = None
    activity_id: Optional[int] = None
    elapsed_time: Optional[int] = None
    start_date: Optional[datetime] = None
    start_date_local: Optional[datetime] = None
    distance: Optional[float] = None
    is_kom: Optional[bool] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None


class DetailedSegment(SummarySegment):
    """Full representation of a Strava segment."""

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    total_elevation_gain: Optional[float] = None
    map: Optional[PolylineMap] = None
    effort_count: Optional[int] = Field(None, description="Total efforts by all athletes")
    athlete_count: Optional[int] = Field(None, description="Unique athletes")
    star_count: Optional[int] = None
    athlete_segment_stats: Optional[SummarySegmentEffort] = Field(
        None, description="Authenticated athlete's best effort"
    )
    xoms: Optional[Xoms] = Field(None, description="KOM/QOM holder times")
    local_legend: Optional[LocalLegend] = None


class DetailedSegmentEffort(BaseModel):
    """A recorded effort on a segment."""

    id: int = Field(..., description="Effort identifier")
    activity_id: Optional[int] = Field(None, description="Parent activity ID")
    elapsed_time: Optional[int] = Field(None, description="Elapsed time in seconds")
    start_date: Optional[datetime] = None
    start_date_local: Optional[datetime] = None
    distance: Optional[float] = Field(None, description="Effort distance in meters")
    is_kom: Optional[bool] = None
    name: Optional[str] = Field(None, description="Segment name")
    activity: Optional[MetaActivity] = None
    athlete: Optional[MetaAthlete] = None
    moving_time: Optional[int] = None
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    average_cadence: Optional[float] = None
    average_watts: Optional[float] = None
    device_watts: Optional[bool] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[float] = None
    segment: Optional[SummarySegment] = None
    kom_rank: Optional[int] = Field(None, description="KOM rank (null if not top 10)")
    pr_rank: Optional[int] = Field(None, description="PR rank (null if not top 3)")
    hidden: Optional[bool] = None
    resource_state: int = Field(default=2)


class ExplorerSegment(BaseModel):
    """Segment returned from the explore endpoint."""

    id: int
    name: Optional[str] = None
    climb_category: Optional[int] = None
    climb_category_desc: Optional[str] = None
    avg_grade: Optional[float] = None
    start_latlng: Optional[LatLng] = None
    end_latlng: Optional[LatLng] = None
    elev_difference: Optional[float] = None
    distance: Optional[float] = None
    points: Optional[str] = Field(None, description="Encoded polyline")
    starred: Optional[bool] = None


class ExplorerResponse(BaseModel):
    """Response from the segment explorer endpoint."""

    segments: List[ExplorerSegment] = Field(default_factory=list)
