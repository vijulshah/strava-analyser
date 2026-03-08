"""Strava activity filters – time range presets and utility helpers.

Provides :class:`TimeRangePreset`, :class:`ActivityFilter`, and the
helper :func:`preset_to_epoch_range` that converts a preset to a
``(after, before)`` tuple of Unix epoch timestamps suitable for the
Strava API ``/athlete/activities`` endpoint.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TimeRangePreset(str, Enum):
    """Pre-defined time range options for filtering activities.

    Each preset maps to a concrete ``(after, before)`` epoch range that is
    computed at request time (i.e. *relative to now*), except for
    :attr:`CUSTOM` which requires explicit ``after_date`` / ``before_date``.
    """

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECONDS_PER_DAY: int = 86_400


def preset_to_epoch_range(
    preset: TimeRangePreset,
    after_date: Optional[datetime] = None,
    before_date: Optional[datetime] = None,
) -> Tuple[Optional[int], Optional[int]]:
    """Convert a :class:`TimeRangePreset` to ``(after_epoch, before_epoch)``.

    Args:
        preset: The selected time range preset.
        after_date: Required when ``preset=custom`` — custom start date.
        before_date: Optional custom end date (defaults to now for custom).

    Returns:
        Tuple of ``(after_epoch, before_epoch)`` where either value may be
        ``None`` (meaning no lower / upper bound).

    Raises:
        ValueError: If ``preset=CUSTOM`` but ``after_date`` is not provided.
    """
    now: float = time.time()

    if preset == TimeRangePreset.CUSTOM:
        if after_date is None:
            raise ValueError("after_date is required when preset='custom'")
        after_ts = int(after_date.timestamp())
        before_ts = int(before_date.timestamp()) if before_date else int(now)
        return after_ts, before_ts

    if preset == TimeRangePreset.ALL_TIME:
        return None, None

    if preset == TimeRangePreset.TODAY:
        # Midnight UTC today
        today_start = datetime.now(tz=timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return int(today_start.timestamp()), None

    if preset == TimeRangePreset.THIS_YEAR:
        year_start = datetime.now(tz=timezone.utc).replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return int(year_start.timestamp()), None

    # Rolling day-based presets
    days_map: dict[TimeRangePreset, int] = {
        TimeRangePreset.LAST_7_DAYS: 7,
        TimeRangePreset.LAST_14_DAYS: 14,
        TimeRangePreset.LAST_30_DAYS: 30,
        TimeRangePreset.LAST_3_MONTHS: 90,
        TimeRangePreset.LAST_6_MONTHS: 182,
        TimeRangePreset.LAST_YEAR: 365,
    }
    days = days_map[preset]
    after_ts = int(now) - days * _SECONDS_PER_DAY
    return after_ts, None


def human_label(preset: TimeRangePreset) -> str:
    """Return a human-readable label for a preset.

    Args:
        preset: The time range preset.

    Returns:
        Human-readable string such as ``'Last 7 days'``.
    """
    labels: dict[TimeRangePreset, str] = {
        TimeRangePreset.TODAY: "Today",
        TimeRangePreset.LAST_7_DAYS: "Last 7 days",
        TimeRangePreset.LAST_14_DAYS: "Last 14 days",
        TimeRangePreset.LAST_30_DAYS: "Last 30 days",
        TimeRangePreset.LAST_3_MONTHS: "Last 3 months",
        TimeRangePreset.LAST_6_MONTHS: "Last 6 months",
        TimeRangePreset.LAST_YEAR: "Last year",
        TimeRangePreset.THIS_YEAR: "This year",
        TimeRangePreset.ALL_TIME: "All time",
        TimeRangePreset.CUSTOM: "Custom range",
    }
    return labels[preset]


# ---------------------------------------------------------------------------
# Filter models
# ---------------------------------------------------------------------------


class ActivityFilter(BaseModel):
    """Full filter specification for listing activities.

    Supports both pre-defined presets and fully custom date ranges.

    Example::

        filter = ActivityFilter(preset=TimeRangePreset.LAST_7_DAYS, sport_type="Run")
        after, before = filter.to_epoch_range()
    """

    preset: TimeRangePreset = Field(
        TimeRangePreset.LAST_30_DAYS,
        description="Pre-defined time range. Use 'custom' together with after_date/before_date.",
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
        description="Filter by sport type (e.g. 'Run', 'Ride', 'Swim'). Case-sensitive.",
    )
    per_page: int = Field(
        default=30,
        ge=1,
        le=200,
        description="Number of activities per page (1–200).",
    )
    page: int = Field(default=1, ge=1, description="Page number (1-based).")

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

    @model_validator(mode="after")
    def validate_custom_range(self) -> "ActivityFilter":
        """Ensure after_date is provided when preset is CUSTOM."""
        if self.preset == TimeRangePreset.CUSTOM and self.after_date is None:
            raise ValueError("after_date is required when preset='custom'")
        return self

    def to_epoch_range(self) -> Tuple[Optional[int], Optional[int]]:
        """Return ``(after_epoch, before_epoch)`` for this filter.

        Returns:
            Tuple of Unix epoch ints (or None for open-ended bounds).
        """
        return preset_to_epoch_range(self.preset, self.after_date, self.before_date)


class AnalysisFilter(BaseModel):
    """Filter for analysis endpoints – allows specifying a period and sport."""

    preset: TimeRangePreset = Field(
        TimeRangePreset.LAST_30_DAYS,
        description="Pre-defined time range for the analysis.",
    )
    after_date: Optional[datetime] = Field(None, description="Custom start (preset='custom')")
    before_date: Optional[datetime] = Field(None, description="Custom end (preset='custom')")
    sport_type: Optional[str] = Field(
        None, description="Limit analysis to this sport type (e.g. 'Run')"
    )
    include_manual: bool = Field(default=True, description="Include manually entered activities")

    model_config = {
        "json_schema_extra": {
            "example": {
                "preset": "last_30_days",
                "sport_type": "Run",
                "include_manual": True,
            }
        }
    }

    def to_epoch_range(self) -> Tuple[Optional[int], Optional[int]]:
        """Return ``(after_epoch, before_epoch)`` for this filter."""
        return preset_to_epoch_range(self.preset, self.after_date, self.before_date)
