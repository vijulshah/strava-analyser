"""Performance trend analysis – pace, speed, and volume over time.

Analyses a list of activities and computes linear regression slopes so
Claude can answer questions like *"Am I getting faster?"* or
*"Is my training volume increasing?"*.
"""

from __future__ import annotations

import math
from typing import List, Optional

from strava_mcp.models.activity import SummaryActivity
from strava_mcp.models.filters import ActivityFilter, human_label
from strava_mcp.models.responses import (
    ActivityDataPoint,
    PerformanceTrendResponse,
    PeriodLabel,
)


def _pace_min_per_km(avg_speed_ms: Optional[float]) -> Optional[float]:
    """Convert m/s speed to min/km pace.

    Args:
        avg_speed_ms: Speed in metres per second.

    Returns:
        Pace in minutes per kilometre, or None if speed is zero/None.
    """
    if not avg_speed_ms:
        return None
    return round(1000 / (avg_speed_ms * 60), 3)


def _linear_slope(xs: List[float], ys: List[float]) -> Optional[float]:
    """Compute ordinary least-squares slope of y on x.

    Args:
        xs: Independent variable values.
        ys: Dependent variable values.

    Returns:
        OLS slope, or None if fewer than two points.
    """
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return None
    return round(num / den, 6)


def analyse_performance_trend(
    activities: List[SummaryActivity],
    sport_type: Optional[str] = None,
    activity_filter: Optional[ActivityFilter] = None,
    preset_label: str = "Selected period",
    after_epoch: Optional[int] = None,
    before_epoch: Optional[int] = None,
) -> PerformanceTrendResponse:
    """Compute performance trend from a list of activities.

    Optionally filtered to a single sport type. Returns per-activity data
    points and linear trend slopes for distance, speed, and heart rate.

    Args:
        activities: List of :class:`SummaryActivity` objects.
        sport_type: Optional sport type to filter (e.g. ``'Run'``).
        activity_filter: The filter used to fetch activities (for labels).
        preset_label: Fallback label when no filter is given.
        after_epoch: Start epoch for display.
        before_epoch: End epoch for display.

    Returns:
        :class:`PerformanceTrendResponse` with data points and trend slopes.
    """
    if activity_filter is not None:
        label = human_label(activity_filter.preset)
        after_epoch, before_epoch = activity_filter.to_epoch_range()
    else:
        label = preset_label

    period = PeriodLabel(label=label, after=after_epoch, before=before_epoch)

    # Filter by sport type if specified
    filtered = [
        a for a in activities
        if sport_type is None
        or (a.sport_type and a.sport_type.value == sport_type)
        or (a.type and a.type.value == sport_type)
    ]

    data_points: List[ActivityDataPoint] = []
    for act in filtered:
        if act.start_date is None:
            continue
        dist_km = round(act.distance / 1000, 3) if act.distance else None
        speed_ms = act.average_speed
        speed_kmh = round(speed_ms * 3.6, 3) if speed_ms else None
        pace = _pace_min_per_km(speed_ms)

        data_points.append(
            ActivityDataPoint(
                activity_id=act.id,
                name=act.name,
                date=act.start_date,
                sport_type=(act.sport_type.value if act.sport_type else None)
                or (act.type.value if act.type else None),
                distance_km=dist_km,
                moving_time_s=act.moving_time,
                avg_speed_kmh=speed_kmh,
                avg_pace_min_per_km=pace,
                elevation_gain_m=act.total_elevation_gain,
                avg_heartrate=act.average_heartrate,
                avg_watts=act.average_watts,
                suffer_score=act.suffer_score,
            )
        )

    # Sort chronologically
    data_points.sort(key=lambda d: d.date)

    # Build index series (weeks from first activity) for trend slopes
    if data_points:
        t0 = data_points[0].date.timestamp()
        xs = [(dp.date.timestamp() - t0) / (7 * 86400) for dp in data_points]
    else:
        xs = []

    dist_ys = [dp.distance_km for dp in data_points if dp.distance_km is not None]
    speed_ys = [dp.avg_speed_kmh for dp in data_points if dp.avg_speed_kmh is not None]
    hr_ys = [dp.avg_heartrate for dp in data_points if dp.avg_heartrate is not None]

    # Slopes (per week)
    trend_dist = _linear_slope(xs[: len(dist_ys)], dist_ys)
    trend_speed = _linear_slope(xs[: len(speed_ys)], speed_ys)
    trend_hr = _linear_slope(xs[: len(hr_ys)], hr_ys)

    best_dist = max(dist_ys) if dist_ys else None
    worst_dist = min(dist_ys) if dist_ys else None
    best_speed = max(speed_ys) if speed_ys else None
    worst_speed = min(speed_ys) if speed_ys else None

    return PerformanceTrendResponse(
        period=period,
        sport_type=sport_type,
        data_points=data_points,
        trend_distance_km=trend_dist,
        trend_avg_speed_kmh=trend_speed,
        trend_avg_heartrate=trend_hr,
        best_distance_km=best_dist,
        worst_distance_km=worst_dist,
        best_avg_speed_kmh=best_speed,
        worst_avg_speed_kmh=worst_speed,
        total_activities=len(data_points),
    )
