"""Cross-query analysis – period comparison and weekly breakdown.

Provides:
- :func:`compare_periods`: side-by-side comparison of two time periods.
- :func:`analyse_weekly_breakdown`: week-over-week summary of activities.
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from strava_mcp.models.activity import SummaryActivity
from strava_mcp.models.filters import (
    ActivityFilter,
    TimeRangePreset,
    human_label,
    preset_to_epoch_range,
)
from strava_mcp.models.responses import (
    PeriodComparisonResponse,
    PeriodLabel,
    PeriodMetrics,
    SportBreakdown,
    WeeklyBreakdownResponse,
    WeekSummary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_seconds(s: int) -> str:
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _pace(avg_speed_ms: Optional[float]) -> Optional[float]:
    if not avg_speed_ms:
        return None
    return round(1000 / (avg_speed_ms * 60), 3)


def _split_activities_by_epoch(
    activities: List[SummaryActivity],
    after_a: Optional[int],
    before_a: Optional[int],
    after_b: Optional[int],
    before_b: Optional[int],
) -> Tuple[List[SummaryActivity], List[SummaryActivity]]:
    """Partition activities into two buckets by date range."""
    bucket_a: List[SummaryActivity] = []
    bucket_b: List[SummaryActivity] = []
    for act in activities:
        if act.start_date is None:
            continue
        ts = int(act.start_date.timestamp())
        if (after_a is None or ts >= after_a) and (before_a is None or ts < before_a):
            bucket_a.append(act)
        elif (after_b is None or ts >= after_b) and (before_b is None or ts < before_b):
            bucket_b.append(act)
    return bucket_a, bucket_b


def _metrics_for_activities(
    activities: List[SummaryActivity],
    period: PeriodLabel,
) -> PeriodMetrics:
    """Compute PeriodMetrics for a list of activities.

    Args:
        activities: Filtered activity list.
        period: Period label for display.

    Returns:
        :class:`PeriodMetrics`.
    """
    count = len(activities)
    total_dist_m = sum(a.distance or 0 for a in activities)
    total_time_s = sum(a.moving_time or 0 for a in activities)
    total_elev_m = sum(a.total_elevation_gain or 0 for a in activities)
    total_hr = sum(a.average_heartrate for a in activities if a.average_heartrate)
    hr_count = sum(1 for a in activities if a.average_heartrate)
    avg_speed_ms_list = [a.average_speed for a in activities if a.average_speed]
    avg_speed_ms = sum(avg_speed_ms_list) / len(avg_speed_ms_list) if avg_speed_ms_list else None

    return PeriodMetrics(
        period=period,
        total_activities=count,
        total_distance_km=round(total_dist_m / 1000, 3),
        total_moving_time_s=total_time_s,
        total_elevation_gain_m=round(total_elev_m, 2),
        avg_distance_km=round(total_dist_m / 1000 / count, 3) if count else 0.0,
        avg_pace_min_per_km=_pace(avg_speed_ms),
        avg_heartrate=round(total_hr / hr_count, 1) if hr_count else None,
    )


# ---------------------------------------------------------------------------
# Period Comparison
# ---------------------------------------------------------------------------


def compare_periods(
    all_activities: List[SummaryActivity],
    filter_a: ActivityFilter,
    filter_b: ActivityFilter,
    sport_type: Optional[str] = None,
) -> PeriodComparisonResponse:
    """Compare two time periods side-by-side.

    Args:
        all_activities: All fetched activities (both periods combined).
        filter_a: Filter defining the first period.
        filter_b: Filter defining the second period.
        sport_type: Optional sport type to restrict comparison.

    Returns:
        :class:`PeriodComparisonResponse` with metrics for each period.
    """
    after_a, before_a = filter_a.to_epoch_range()
    after_b, before_b = filter_b.to_epoch_range()

    def _in_range(act: SummaryActivity, after: Optional[int], before: Optional[int]) -> bool:
        if act.start_date is None:
            return False
        ts = int(act.start_date.timestamp())
        return (after is None or ts >= after) and (before is None or ts < before)

    def _sport_ok(act: SummaryActivity) -> bool:
        if sport_type is None:
            return True
        return (
            (act.sport_type and act.sport_type.value == sport_type)
            or (act.type and act.type.value == sport_type)
        )

    acts_a = [a for a in all_activities if _in_range(a, after_a, before_a) and _sport_ok(a)]
    acts_b = [a for a in all_activities if _in_range(a, after_b, before_b) and _sport_ok(a)]

    period_a = PeriodLabel(label=human_label(filter_a.preset), after=after_a, before=before_a)
    period_b = PeriodLabel(label=human_label(filter_b.preset), after=after_b, before=before_b)

    metrics_a = _metrics_for_activities(acts_a, period_a)
    metrics_b = _metrics_for_activities(acts_b, period_b)

    def _pct_change(a: float, b: float) -> Optional[float]:
        if a == 0:
            return None
        return round((b - a) / a * 100, 1)

    dist_change = _pct_change(metrics_a.total_distance_km, metrics_b.total_distance_km)
    count_change = _pct_change(metrics_a.total_activities, metrics_b.total_activities)
    elev_change = _pct_change(metrics_a.total_elevation_gain_m, metrics_b.total_elevation_gain_m)
    pace_change: Optional[float] = None
    if metrics_a.avg_pace_min_per_km and metrics_b.avg_pace_min_per_km:
        # Lower pace = faster; negative pct = improvement
        pace_change = _pct_change(metrics_a.avg_pace_min_per_km, metrics_b.avg_pace_min_per_km)

    # Build human summary
    parts: List[str] = []
    if dist_change is not None:
        direction = "up" if dist_change >= 0 else "down"
        parts.append(f"Distance {direction} {abs(dist_change)}%")
    if count_change is not None:
        direction = "more" if count_change >= 0 else "fewer"
        parts.append(f"{abs(count_change)}% {direction} activities")
    if pace_change is not None:
        adj = "faster" if pace_change < 0 else "slower"
        parts.append(f"Avg pace {abs(pace_change)}% {adj}")
    summary = ". ".join(parts) + "." if parts else "No significant changes."

    return PeriodComparisonResponse(
        period_a=metrics_a,
        period_b=metrics_b,
        distance_change_pct=dist_change,
        activity_count_change_pct=count_change,
        elevation_change_pct=elev_change,
        pace_change_pct=pace_change,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Weekly Breakdown
# ---------------------------------------------------------------------------


def _monday_of(dt: datetime) -> datetime:
    """Return the Monday (UTC midnight) of the week containing ``dt``."""
    days_since_monday = dt.weekday()  # 0=Mon
    monday = dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc) - timedelta(days=days_since_monday)
    return monday


def analyse_weekly_breakdown(
    activities: List[SummaryActivity],
    sport_type: Optional[str] = None,
    activity_filter: Optional[ActivityFilter] = None,
    preset_label: str = "Selected period",
    after_epoch: Optional[int] = None,
    before_epoch: Optional[int] = None,
) -> WeeklyBreakdownResponse:
    """Build a week-over-week breakdown of activities.

    Args:
        activities: Fetched activity list.
        sport_type: Optional sport filter.
        activity_filter: Filter for label generation.
        preset_label: Fallback period label.
        after_epoch: Start epoch.
        before_epoch: End epoch.

    Returns:
        :class:`WeeklyBreakdownResponse` with per-week metrics.
    """
    if activity_filter is not None:
        label = human_label(activity_filter.preset)
        after_epoch, before_epoch = activity_filter.to_epoch_range()
    else:
        label = preset_label

    period = PeriodLabel(label=label, after=after_epoch, before=before_epoch)

    # Filter sport
    filtered = [
        a for a in activities
        if sport_type is None
        or (a.sport_type and a.sport_type.value == sport_type)
        or (a.type and a.type.value == sport_type)
    ]

    # Bucket by week start
    week_data: Dict[datetime, Dict] = defaultdict(
        lambda: {"count": 0, "distance": 0.0, "time": 0, "elevation": 0.0, "sports": defaultdict(lambda: {"count": 0, "dist": 0.0, "time": 0, "elev": 0.0})}
    )

    for act in filtered:
        if act.start_date is None:
            continue
        monday = _monday_of(act.start_date)
        sport = (act.sport_type.value if act.sport_type else None) or (act.type.value if act.type else "Unknown")
        dist = act.distance or 0.0
        move_t = act.moving_time or 0
        elev = act.total_elevation_gain or 0.0

        week_data[monday]["count"] += 1
        week_data[monday]["distance"] += dist
        week_data[monday]["time"] += move_t
        week_data[monday]["elevation"] += elev

        sd = week_data[monday]["sports"][sport]
        sd["count"] += 1
        sd["dist"] += dist
        sd["time"] += move_t
        sd["elev"] += elev

    weeks: List[WeekSummary] = []
    for week_start in sorted(week_data.keys()):
        wd = week_data[week_start]
        week_end = week_start + timedelta(days=6)
        week_label = f"{week_start.strftime('%b %-d')}–{week_end.strftime('%-d')}"
        sport_breakdown = [
            SportBreakdown(
                sport_type=sp,
                count=wd["sports"][sp]["count"],
                total_distance_m=wd["sports"][sp]["dist"],
                total_moving_time_s=wd["sports"][sp]["time"],
                total_elevation_gain_m=wd["sports"][sp]["elev"],
                avg_distance_m=wd["sports"][sp]["dist"] / wd["sports"][sp]["count"] if wd["sports"][sp]["count"] else 0.0,
                avg_moving_time_s=wd["sports"][sp]["time"] / wd["sports"][sp]["count"] if wd["sports"][sp]["count"] else 0.0,
            )
            for sp in sorted(wd["sports"].keys())
        ]
        weeks.append(
            WeekSummary(
                week_start=week_start,
                week_label=week_label,
                count=wd["count"],
                total_distance_km=round(wd["distance"] / 1000, 3),
                total_moving_time_s=wd["time"],
                total_elevation_gain_m=round(wd["elevation"], 2),
                sport_breakdown=sport_breakdown,
            )
        )

    if weeks:
        busiest = max(weeks, key=lambda w: w.total_distance_km)
        quietest = min(weeks, key=lambda w: w.total_distance_km)
        avg_weekly_km = round(sum(w.total_distance_km for w in weeks) / len(weeks), 3)
    else:
        busiest = quietest = None  # type: ignore[assignment]
        avg_weekly_km = None

    return WeeklyBreakdownResponse(
        period=period,
        sport_type=sport_type,
        weeks=weeks,
        total_weeks=len(weeks),
        busiest_week_label=busiest.week_label if busiest else None,
        busiest_week_distance_km=busiest.total_distance_km if busiest else None,
        quietest_week_label=quietest.week_label if quietest else None,
        avg_weekly_distance_km=avg_weekly_km,
    )
