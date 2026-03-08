"""Strava API models – Activity & related types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SportType(str, Enum):
    """Strava sport types (preferred over ActivityType)."""

    ALPINE_SKI = "AlpineSki"
    BACKCOUNTRY_SKI = "BackcountrySki"
    BADMINTON = "Badminton"
    CANOEING = "Canoeing"
    CROSSFIT = "Crossfit"
    E_BIKE_RIDE = "EBikeRide"
    ELLIPTICAL = "Elliptical"
    E_MOUNTAIN_BIKE_RIDE = "EMountainBikeRide"
    GOLF = "Golf"
    GRAVEL_RIDE = "GravelRide"
    HANDCYCLE = "Handcycle"
    HIIT = "HighIntensityIntervalTraining"
    HIKE = "Hike"
    ICE_SKATE = "IceSkate"
    INLINE_SKATE = "InlineSkate"
    KAYAKING = "Kayaking"
    KITESURF = "Kitesurf"
    MOUNTAIN_BIKE_RIDE = "MountainBikeRide"
    NORDIC_SKI = "NordicSki"
    PICKLEBALL = "Pickleball"
    PILATES = "Pilates"
    RACQUETBALL = "Racquetball"
    RIDE = "Ride"
    ROCK_CLIMBING = "RockClimbing"
    ROLLER_SKI = "RollerSki"
    ROWING = "Rowing"
    RUN = "Run"
    SAIL = "Sail"
    SKATEBOARD = "Skateboard"
    SNOWBOARD = "Snowboard"
    SNOWSHOE = "Snowshoe"
    SOCCER = "Soccer"
    SQUASH = "Squash"
    STAIR_STEPPER = "StairStepper"
    STAND_UP_PADDLING = "StandUpPaddling"
    SURFING = "Surfing"
    SWIM = "Swim"
    TABLE_TENNIS = "TableTennis"
    TENNIS = "Tennis"
    TRAIL_RUN = "TrailRun"
    VELOMOBILE = "Velomobile"
    VIRTUAL_RIDE = "VirtualRide"
    VIRTUAL_ROW = "VirtualRow"
    VIRTUAL_RUN = "VirtualRun"
    WALK = "Walk"
    WEIGHT_TRAINING = "WeightTraining"
    WHEELCHAIR = "Wheelchair"
    WINDSURF = "Windsurf"
    WORKOUT = "Workout"
    YOGA = "Yoga"


class ActivityType(str, Enum):
    """Deprecated Strava activity type enum. Use SportType instead."""

    ALPINE_SKI = "AlpineSki"
    BACKCOUNTRY_SKI = "BackcountrySki"
    CANOEING = "Canoeing"
    CROSSFIT = "Crossfit"
    E_BIKE_RIDE = "EBikeRide"
    ELLIPTICAL = "Elliptical"
    GOLF = "Golf"
    HANDCYCLE = "Handcycle"
    HIKE = "Hike"
    ICE_SKATE = "IceSkate"
    INLINE_SKATE = "InlineSkate"
    KAYAKING = "Kayaking"
    KITESURF = "Kitesurf"
    NORDIC_SKI = "NordicSki"
    RIDE = "Ride"
    ROCK_CLIMBING = "RockClimbing"
    ROLLER_SKI = "RollerSki"
    ROWING = "Rowing"
    RUN = "Run"
    SAIL = "Sail"
    SKATEBOARD = "Skateboard"
    SNOWBOARD = "Snowboard"
    SNOWSHOE = "Snowshoe"
    SOCCER = "Soccer"
    STAIR_STEPPER = "StairStepper"
    STAND_UP_PADDLING = "StandUpPaddling"
    SURFING = "Surfing"
    SWIM = "Swim"
    VELOMOBILE = "Velomobile"
    VIRTUAL_RIDE = "VirtualRide"
    VIRTUAL_RUN = "VirtualRun"
    WALK = "Walk"
    WEIGHT_TRAINING = "WeightTraining"
    WHEELCHAIR = "Wheelchair"
    WINDSURF = "Windsurf"
    WORKOUT = "Workout"
    YOGA = "Yoga"


class ActivityVisibility(str, Enum):
    """Activity visibility settings."""

    EVERYONE = "everyone"
    FOLLOWERS_ONLY = "followers_only"
    ONLY_ME = "only_me"


# ---------------------------------------------------------------------------
# Supporting models
# ---------------------------------------------------------------------------


LatLng = List[float]  # [latitude, longitude]


class PolylineMap(BaseModel):
    """Encoded polyline map for an activity or segment."""

    id: str = Field(..., description="Map identifier")
    polyline: Optional[str] = Field(None, description="Full-resolution encoded polyline")
    summary_polyline: Optional[str] = Field(None, description="Low-resolution encoded polyline")


class MetaAthlete(BaseModel):
    """Minimal athlete reference."""

    id: int = Field(..., description="Athlete identifier")
    resource_state: int = Field(default=1)


class MetaActivity(BaseModel):
    """Minimal activity reference."""

    id: int = Field(..., description="Activity identifier")
    resource_state: int = Field(default=1)


class PhotosSummaryPrimary(BaseModel):
    """Primary photo details."""

    id: Optional[int] = None
    unique_id: Optional[str] = None
    urls: Optional[Dict[str, str]] = None
    source: Optional[int] = None


class PhotosSummary(BaseModel):
    """Summary of photos for an activity."""

    count: int = Field(default=0)
    primary: Optional[PhotosSummaryPrimary] = None


class TimedZoneRange(BaseModel):
    """One bucket of a timed zone distribution."""

    min: int = Field(..., description="Minimum value for this zone")
    max: int = Field(..., description="Maximum value for this zone (-1 = unlimited)")
    time: int = Field(..., description="Seconds spent in this zone")


class ActivityZone(BaseModel):
    """Heart rate or power distribution zones for an activity."""

    score: Optional[int] = Field(None, description="Zone score")
    distribution_buckets: Optional[List[TimedZoneRange]] = Field(
        None, description="Time distribution across zones"
    )
    type: str = Field(..., description="'heartrate' or 'power'")
    sensor_based: bool = Field(default=False, description="Data from sensor")
    custom_zones: bool = Field(default=False, description="Custom zones used")
    max: Optional[int] = Field(None, description="Max HR or power value recorded")


class SummaryGear(BaseModel):
    """Summary gear (bike or shoes)."""

    id: str = Field(..., description="Gear identifier")
    primary: bool = Field(default=False, description="Primary gear")
    name: str = Field(..., description="Gear name")
    distance: float = Field(default=0.0, description="Total distance in meters")
    resource_state: int = Field(default=2)


# ---------------------------------------------------------------------------
# Lap
# ---------------------------------------------------------------------------


class Lap(BaseModel):
    """One lap of an activity."""

    id: int = Field(..., description="Lap identifier")
    activity: Optional[MetaActivity] = None
    athlete: Optional[MetaAthlete] = None
    average_cadence: Optional[float] = Field(None, description="Average cadence rpm")
    average_speed: Optional[float] = Field(None, description="Average speed m/s")
    distance: Optional[float] = Field(None, description="Lap distance meters")
    elapsed_time: Optional[int] = Field(None, description="Elapsed time seconds")
    end_index: Optional[int] = None
    lap_index: Optional[int] = Field(None, description="1-based lap index")
    max_speed: Optional[float] = Field(None, description="Max speed m/s")
    moving_time: Optional[int] = Field(None, description="Moving time seconds")
    name: Optional[str] = Field(None, description="Lap label")
    pace_zone: Optional[int] = None
    split: Optional[int] = None
    start_date: Optional[datetime] = None
    start_date_local: Optional[datetime] = None
    start_index: Optional[int] = None
    total_elevation_gain: Optional[float] = Field(None, description="Elevation gain meters")
    average_watts: Optional[float] = Field(None, description="Average power watts")
    average_heartrate: Optional[float] = Field(None, description="Average HR bpm")
    max_heartrate: Optional[float] = Field(None, description="Max HR bpm")
    resource_state: int = Field(default=2)


# ---------------------------------------------------------------------------
# Comment / Kudoer
# ---------------------------------------------------------------------------


class Comment(BaseModel):
    """Activity comment."""

    id: int = Field(..., description="Comment ID")
    activity_id: int = Field(..., description="Parent activity ID")
    text: str = Field(..., description="Comment text")
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Summary Activity
# ---------------------------------------------------------------------------


class SummaryActivity(BaseModel):
    """Summary representation of a Strava activity (used in list responses)."""

    id: int = Field(..., description="Unique activity identifier")
    name: str = Field(..., description="Activity name")
    distance: Optional[float] = Field(None, description="Distance in meters")
    moving_time: Optional[int] = Field(None, description="Moving time in seconds")
    elapsed_time: Optional[int] = Field(None, description="Elapsed time in seconds")
    total_elevation_gain: Optional[float] = Field(None, description="Elevation gain in meters")
    type: Optional[ActivityType] = Field(None, description="Deprecated activity type")
    sport_type: Optional[SportType] = Field(None, description="Sport type (preferred)")
    start_date: Optional[datetime] = Field(None, description="UTC start time")
    start_date_local: Optional[datetime] = Field(None, description="Local start time")
    timezone: Optional[str] = None
    utc_offset: Optional[float] = None
    start_latlng: Optional[LatLng] = None
    end_latlng: Optional[LatLng] = None
    achievement_count: Optional[int] = Field(None, description="Number of achievements")
    kudos_count: Optional[int] = None
    comment_count: Optional[int] = None
    athlete_count: Optional[int] = None
    photo_count: Optional[int] = None
    map: Optional[PolylineMap] = None
    trainer: Optional[bool] = Field(None, description="Trainer/indoor activity")
    commute: Optional[bool] = None
    manual: Optional[bool] = None
    private: Optional[bool] = None
    visibility: Optional[ActivityVisibility] = None
    flagged: Optional[bool] = None
    gear_id: Optional[str] = None
    average_speed: Optional[float] = Field(None, description="Average speed m/s")
    max_speed: Optional[float] = Field(None, description="Max speed m/s")
    average_cadence: Optional[float] = None
    average_watts: Optional[float] = None
    max_watts: Optional[int] = None
    weighted_average_watts: Optional[int] = None
    kilojoules: Optional[float] = None
    device_watts: Optional[bool] = None
    has_heartrate: Optional[bool] = None
    average_heartrate: Optional[float] = Field(None, description="Average HR bpm")
    max_heartrate: Optional[float] = None
    heartrate_opt_out: Optional[bool] = None
    display_hide_heartrate_option: Optional[bool] = None
    elev_high: Optional[float] = None
    elev_low: Optional[float] = None
    upload_id: Optional[int] = None
    upload_id_str: Optional[str] = None
    external_id: Optional[str] = None
    from_accepted_tag: Optional[bool] = None
    pr_count: Optional[int] = None
    total_photo_count: Optional[int] = None
    has_kudoed: Optional[bool] = None
    suffer_score: Optional[float] = None
    athlete: Optional[MetaAthlete] = None
    resource_state: int = Field(default=2)


# ---------------------------------------------------------------------------
# Detailed Activity
# ---------------------------------------------------------------------------


class DetailedActivity(SummaryActivity):
    """Full representation of a Strava activity including all sub-resources."""

    description: Optional[str] = Field(None, description="Activity description")
    calories: Optional[float] = Field(None, description="Estimated calories")
    perceived_exertion: Optional[float] = Field(None, description="Perceived exertion 1-10")
    prefer_perceived_exertion: Optional[bool] = None
    segment_efforts: Optional[List[Any]] = Field(None, description="Segment efforts")
    splits_metric: Optional[List[Any]] = Field(None, description="Metric splits (1 km)")
    splits_standard: Optional[List[Any]] = Field(None, description="Standard splits (1 mile)")
    laps: Optional[List[Lap]] = Field(None, description="Laps")
    best_efforts: Optional[List[Any]] = Field(None, description="Best efforts")
    gear: Optional[SummaryGear] = None
    photos: Optional[PhotosSummary] = None
    device_name: Optional[str] = Field(None, description="Recording device name")
    embed_token: Optional[str] = None
    similar_activities: Optional[Any] = None
    available_zones: Optional[List[str]] = None
    hide_from_home: Optional[bool] = None


# ---------------------------------------------------------------------------
# Updatable Activity (for PUT /activities/{id})
# ---------------------------------------------------------------------------


class UpdatableActivity(BaseModel):
    """Fields that can be updated on an activity."""

    commute: Optional[bool] = Field(None, description="Mark as commute")
    trainer: Optional[bool] = Field(None, description="Mark as trainer activity")
    hide_from_home: Optional[bool] = Field(None, description="Hide from home feed")
    description: Optional[str] = Field(None, description="Activity description")
    name: Optional[str] = Field(None, description="Activity name")
    sport_type: Optional[SportType] = Field(None, description="Sport type")
    gear_id: Optional[str] = Field(None, description="Gear ID ('none' to unset)")


# ---------------------------------------------------------------------------
# Create Activity (for POST /activities)
# ---------------------------------------------------------------------------


class CreateActivityRequest(BaseModel):
    """Request body for creating a manual activity."""

    name: str = Field(..., description="Activity name")
    sport_type: SportType = Field(..., description="Sport type")
    start_date_local: datetime = Field(..., description="ISO 8601 local start time")
    elapsed_time: int = Field(..., ge=1, description="Elapsed time in seconds")
    description: Optional[str] = None
    distance: Optional[float] = Field(None, ge=0, description="Distance in meters")
    trainer: Optional[int] = Field(None, description="1 if trainer activity")
    commute: Optional[int] = Field(None, description="1 if commute")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Morning Run",
                "sport_type": "Run",
                "start_date_local": "2024-01-15T07:30:00Z",
                "elapsed_time": 3600,
                "distance": 10000,
                "description": "Great 10k run",
            }
        }
    }
