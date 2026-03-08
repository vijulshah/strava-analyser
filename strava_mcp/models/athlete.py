"""Strava API models – Athlete & zones."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from strava_mcp.models.activity import SummaryGear


class ZoneRange(BaseModel):
    """One training zone range."""

    min: int = Field(..., description="Minimum value")
    max: int = Field(..., description="Maximum value (-1 = no limit)")


class ZoneRanges(BaseModel):
    """Set of training zone ranges."""

    zones: List[ZoneRange] = Field(default_factory=list)


class HeartRateZoneRanges(BaseModel):
    """Heart rate training zones."""

    custom_zones: bool = Field(default=False, description="Whether custom zones are used")
    zones: List[ZoneRange] = Field(default_factory=list, description="5 HR zones")


class PowerZoneRanges(BaseModel):
    """Power training zones (requires FTP)."""

    zones: List[ZoneRange] = Field(default_factory=list, description="7 power zones")


class Zones(BaseModel):
    """Athlete training zones (HR and power)."""

    heart_rate: Optional[HeartRateZoneRanges] = Field(None, description="Heart rate zones")
    power: Optional[PowerZoneRanges] = Field(None, description="Power zones")


class SummaryAthlete(BaseModel):
    """Summary representation of a Strava athlete."""

    id: int = Field(..., description="Athlete identifier")
    username: Optional[str] = None
    resource_state: int = Field(default=2)
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    sex: Optional[str] = None
    premium: Optional[bool] = None
    summit: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    badge_type_id: Optional[int] = None
    profile_medium: Optional[str] = Field(None, description="62×62 pixel profile picture URL")
    profile: Optional[str] = Field(None, description="Full profile picture URL")
    friend: Optional[str] = None
    follower: Optional[str] = None


class SummaryClub(BaseModel):
    """Summary representation of a Strava club."""

    id: int = Field(..., description="Club identifier")
    resource_state: int = Field(default=2)
    name: Optional[str] = None
    profile_medium: Optional[str] = None
    cover_photo: Optional[str] = None
    cover_photo_small: Optional[str] = None
    sport_type: Optional[str] = None
    activity_types: Optional[List[str]] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    private: Optional[bool] = None
    member_count: Optional[int] = None
    featured: Optional[bool] = None
    verified: Optional[bool] = None
    url: Optional[str] = None


class DetailedAthlete(SummaryAthlete):
    """Full representation of the authenticated Strava athlete."""

    follower_count: Optional[int] = Field(None, description="Number of followers")
    friend_count: Optional[int] = Field(None, description="Number of friends")
    mutual_friend_count: Optional[int] = None
    athlete_type: Optional[int] = Field(None, description="0=cyclist, 1=runner")
    date_preference: Optional[str] = None
    measurement_preference: Optional[str] = Field(
        None, description="'feet' or 'meters'"
    )
    ftp: Optional[int] = Field(None, description="Functional Threshold Power (watts)")
    weight: Optional[float] = Field(None, description="Weight in kg")
    clubs: Optional[List[SummaryClub]] = Field(None, description="Athlete's clubs")
    bikes: Optional[List[SummaryGear]] = Field(None, description="Athlete's bikes")
    shoes: Optional[List[SummaryGear]] = Field(None, description="Athlete's shoes")
