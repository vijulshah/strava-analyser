"""Activity aggregator – totals, per-sport breakdown, and summary stats.

This module operates on a list of :class:`~strava_mcp.models.SummaryActivity`
objects (already fetched from Strava) and produces an
:class:`~strava_mcp.models.responses.AggregatedStatsResponse`.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from strava_mcp.models.activity import SummaryActivity
from strava_mcp.models.filters import ActivityFilter, TimeRangePreset, human_label
from strava_mcp.models.responses import (
    AggregatedStatsResponse,
    PeriodLabel,
    SportBreakdown,
)


def _format_seconds(total: int) -> str:
    """Convert seconds to HH:MM:SS string.

    Args:
        total: Total seconds.

    Returns:
        String formatted as ``'HH:MM:SS'``.
    """
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def aggregate_activities(
    activities: List[SummaryActivity],
    activity_filter: Optional[ActivityFilter] = None,
    preset_label: str = "Selected period",
    after_epoch: Optional[int] = None,
    before_epoch: Optional[int] = None,
) -> AggregatedStatsResponse:
    """Aggregate a list of activities into summary statistics.

    Args:
        activities: List of :class:`SummaryActivity` objects.
        activity_filter: Optional filter that was used to retrieve activities
            (used for label generation).
        preset_label: Human-readable period label fallback.
        after_epoch: Unix epoch of the range start (for display only).
        before_epoch: Unix epoch of the range end (for display only).

    Returns:
        :class:`AggregatedStatsResponse` with totals and sport breakdown.
    """
    if activity_filter is not None:
        label = human_label(activity_filter.preset)
        after_epoch, before_epoch = activity_filter.to_epoch_range()
    else:
        label = preset_label

    period = PeriodLabel(label=label, after=after_epoch, before=before_epoch)

    total_distance: float = 0.0
    total_moving_time: int = 0
    total_elevation: float = 0.0
    total_calories: float = 0.0
    total_kudos: int = 0
    total_achievements: int = 0

    sport_counts: Dict[str, int] = defaultdict(int)
    sport_distance: Dict[str, float] = defaultdict(float)
    sport_time: Dict[str, int] = defaultdict(int)
    sport_elevation: Dict[str, float] = defaultdict(float)

    has_calories = False

    for act in activities:
        sport = (act.sport_type.value if act.sport_type else None) or (
            act.type.value if act.type else "Unknown"
        )
        dist = act.distance or 0.0
        move_t = act.moving_time or 0
        elev = act.total_elevation_gain or 0.0
        cals = act.calories if hasattr(act, "calories") and act.calories else 0.0  # type: ignore[union-attr]

        total_distance += dist
        total_moving_time += move_t
        total_elevation += elev
        total_calories += cals
        if cals:
            has_calories = True
        total_kudos += act.kudos_count or 0
        total_achievements += act.achievement_count or 0

        sport_counts[sport] += 1
        sport_distance[sport] += dist
        sport_time[sport] += move_t
        sport_elevation[sport] += elev

    count = len(activities)

    sport_breakdown: List[SportBreakdown] = [
        SportBreakdown(
            sport_type=sport,
            count=sport_counts[sport],
            total_distance_m=sport_distance[sport],
            total_moving_time_s=sport_time[sport],
            total_elevation_gain_m=sport_elevation[sport],
            avg_distance_m=sport_distance[sport] / sport_counts[sport] if sport_counts[sport] else 0.0,
            avg_moving_time_s=sport_time[sport] / sport_counts[sport] if sport_counts[sport] else 0.0,
        )
        for sport in sorted(sport_counts.keys())
    ]

    return AggregatedStatsResponse(
        period=period,
        total_activities=count,
        total_distance_m=round(total_distance, 2),
        total_distance_km=round(total_distance / 1000, 3),
        total_moving_time_s=total_moving_time,
        total_moving_time_formatted=_format_seconds(total_moving_time),
        total_elevation_gain_m=round(total_elevation, 2),
        total_calories=round(total_calories, 1) if has_calories else None,
        avg_distance_km=round(total_distance / 1000 / count, 3) if count else 0.0,
        avg_moving_time_s=round(total_moving_time / count, 1) if count else 0.0,
        avg_elevation_gain_m=round(total_elevation / count, 2) if count else 0.0,
        sport_breakdown=sport_breakdown,
        total_kudos=total_kudos,
        total_achievements=total_achievements,
    )
