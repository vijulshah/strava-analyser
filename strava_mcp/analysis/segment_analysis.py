"""Segment effort analysis – compare efforts on a single segment.

Ranks all efforts chronologically and by elapsed time, identifies PRs,
and surfaces key metrics for cross-questioning in Claude.
"""

from __future__ import annotations

from typing import List, Optional

from strava_mcp.models.segment import DetailedSegmentEffort
from strava_mcp.models.responses import (
    SegmentComparisonResponse,
    SegmentEffortSummary,
)


def _format_time(seconds: int) -> str:
    """Format elapsed seconds as MM:SS or H:MM:SS.

    Args:
        seconds: Elapsed time in seconds.

    Returns:
        Formatted time string.
    """
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def compare_segment_efforts(
    efforts: List[DetailedSegmentEffort],
    segment_id: int,
    segment_name: Optional[str] = None,
    segment_distance_m: Optional[float] = None,
) -> SegmentComparisonResponse:
    """Compare all efforts on a segment and rank them.

    Args:
        efforts: List of :class:`DetailedSegmentEffort` objects for one segment.
        segment_id: Strava segment identifier.
        segment_name: Segment display name.
        segment_distance_m: Segment distance in metres.

    Returns:
        :class:`SegmentComparisonResponse` with ranked efforts.
    """
    if not efforts:
        return SegmentComparisonResponse(
            segment_id=segment_id,
            segment_name=segment_name,
            distance_m=segment_distance_m,
            total_efforts=0,
        )

    # Sort by elapsed_time ascending (fastest first = rank 1)
    sorted_efforts = sorted(
        efforts,
        key=lambda e: e.elapsed_time if e.elapsed_time is not None else 999999,
    )

    pr_elapsed = sorted_efforts[0].elapsed_time if sorted_efforts else None
    pr_date = sorted_efforts[0].start_date if sorted_efforts else None

    summaries: List[SegmentEffortSummary] = []
    for rank, effort in enumerate(sorted_efforts, start=1):
        elapsed = effort.elapsed_time or 0
        summaries.append(
            SegmentEffortSummary(
                effort_id=effort.id,
                activity_id=effort.activity_id,
                date=effort.start_date,
                elapsed_time_s=elapsed,
                elapsed_time_formatted=_format_time(elapsed),
                rank=rank,
                is_pr=(rank == 1),
                is_kom=effort.is_kom or False,
                avg_watts=effort.average_watts,
                avg_heartrate=effort.average_heartrate,
            )
        )

    return SegmentComparisonResponse(
        segment_id=segment_id,
        segment_name=segment_name,
        distance_m=segment_distance_m,
        total_efforts=len(efforts),
        pr_elapsed_time_s=pr_elapsed,
        pr_elapsed_time_formatted=_format_time(pr_elapsed) if pr_elapsed else None,
        pr_date=pr_date,
        efforts=summaries,
    )


def find_personal_records_from_activities(
    activities: List,  # List[SummaryActivity] – using Any to avoid circular import
) -> dict:
    """Find personal records (longest run, fastest, etc.) across activities.

    Args:
        activities: List of SummaryActivity objects.

    Returns:
        Dict keyed by sport type → dict of metric → best value + activity.
    """
    from collections import defaultdict

    records: dict = defaultdict(dict)

    for act in activities:
        sport = (
            (act.sport_type.value if act.sport_type else None)
            or (act.type.value if act.type else "Unknown")
        )
        dist = act.distance or 0
        speed = act.average_speed or 0
        elev = act.total_elevation_gain or 0

        # Longest distance
        if "longest_distance" not in records[sport] or dist > records[sport]["longest_distance"]["value"]:
            records[sport]["longest_distance"] = {"value": dist, "activity_id": act.id, "name": act.name, "date": act.start_date}

        # Highest average speed
        if speed and (
            "fastest_avg_speed" not in records[sport]
            or speed > records[sport]["fastest_avg_speed"]["value"]
        ):
            records[sport]["fastest_avg_speed"] = {"value": speed, "activity_id": act.id, "name": act.name, "date": act.start_date}

        # Most elevation
        if "most_elevation" not in records[sport] or elev > records[sport]["most_elevation"]["value"]:
            records[sport]["most_elevation"] = {"value": elev, "activity_id": act.id, "name": act.name, "date": act.start_date}

    return dict(records)
