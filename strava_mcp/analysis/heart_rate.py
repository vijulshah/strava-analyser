"""Heart rate zone analysis.

Distributes total activity time across 5 HR zones using either the
athlete's custom zones (from Strava) or a default 5-zone model based on
max HR.

HR zone labels follow the classic 5-zone Coggan/British Cycling model:
  - Zone 1: Active Recovery  (<60% max HR)
  - Zone 2: Aerobic Base     (60–70%)
  - Zone 3: Tempo            (70–80%)
  - Zone 4: Threshold        (80–90%)
  - Zone 5: Neuromuscular    (>90%)
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from strava_mcp.models.activity import SummaryActivity
from strava_mcp.models.filters import ActivityFilter, human_label
from strava_mcp.models.responses import (
    HRZoneAnalysisResponse,
    HRZoneBucket,
    PeriodLabel,
)

_DEFAULT_MAX_HR: int = 190
_ZONE_LABELS: List[str] = [
    "Zone 1 – Active Recovery",
    "Zone 2 – Aerobic Base",
    "Zone 3 – Tempo",
    "Zone 4 – Threshold",
    "Zone 5 – Neuromuscular",
]
_ZONE_PCT_BOUNDARIES: List[float] = [0.0, 0.60, 0.70, 0.80, 0.90, 1.01]


def _format_hm(seconds: int) -> str:
    """Format seconds as a compact ``'Xh Ym'`` string.

    Args:
        seconds: Duration in seconds.

    Returns:
        String like ``'1h 23m'`` or ``'45m'``.
    """
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def _default_zone_ranges(max_hr: int) -> List[Tuple[int, int]]:
    """Compute default 5-zone HR boundaries from max HR.

    Args:
        max_hr: Maximum heart rate in bpm.

    Returns:
        List of ``(min_hr, max_hr)`` tuples for each zone.
    """
    boundaries = [int(max_hr * pct) for pct in _ZONE_PCT_BOUNDARIES]
    return [(boundaries[i], boundaries[i + 1] - 1) for i in range(5)]


def _zone_for_hr(hr: int, zone_ranges: List[Tuple[int, int]]) -> int:
    """Return 0-indexed zone index for a given HR value.

    Args:
        hr: Heart rate in bpm.
        zone_ranges: List of ``(min, max)`` pairs.

    Returns:
        Zone index (0–4).
    """
    for i, (lo, hi) in enumerate(zone_ranges):
        if lo <= hr <= hi:
            return i
    return len(zone_ranges) - 1  # clamp to top zone


def analyse_hr_zones(
    activities: List[SummaryActivity],
    activity_zones_data: Optional[List[List[Dict]]] = None,
    max_hr: int = _DEFAULT_MAX_HR,
    sport_type: Optional[str] = None,
    activity_filter: Optional[ActivityFilter] = None,
    preset_label: str = "Selected period",
    after_epoch: Optional[int] = None,
    before_epoch: Optional[int] = None,
) -> HRZoneAnalysisResponse:
    """Compute HR zone distribution across a list of activities.

    Uses ``activity_zones_data`` (raw Strava zone responses) when available,
    falling back to average HR estimation per activity otherwise.

    Args:
        activities: Fetched SummaryActivity objects.
        activity_zones_data: Optional list of per-activity zone payloads
            (each is the JSON from ``GET /activities/{id}/zones``).
        max_hr: Athlete's maximum HR for default zone calculation.
        sport_type: Optional sport filter.
        activity_filter: Filter for label generation.
        preset_label: Fallback period label.
        after_epoch: Start epoch.
        before_epoch: End epoch.

    Returns:
        :class:`HRZoneAnalysisResponse` with per-zone breakdowns.
    """
    if activity_filter is not None:
        label = human_label(activity_filter.preset)
        after_epoch, before_epoch = activity_filter.to_epoch_range()
    else:
        label = preset_label

    period = PeriodLabel(label=label, after=after_epoch, before=before_epoch)
    zone_ranges = _default_zone_ranges(max_hr)

    # Filter by sport
    filtered = [
        a for a in activities
        if sport_type is None
        or (a.sport_type and a.sport_type.value == sport_type)
        or (a.type and a.type.value == sport_type)
    ]

    zone_seconds: List[int] = [0, 0, 0, 0, 0]
    activities_with_hr = 0
    total_hr_sum = 0.0
    max_hr_recorded = 0.0
    total_tracked_seconds = 0

    for i, act in enumerate(filtered):
        if not act.has_heartrate:
            continue
        activities_with_hr += 1
        moving_s = act.moving_time or 0

        if act.average_heartrate:
            total_hr_sum += act.average_heartrate
        if act.max_heartrate and act.max_heartrate > max_hr_recorded:
            max_hr_recorded = act.max_heartrate

        # Try to use detailed zone distribution if provided
        zone_payload: Optional[List[Dict]] = None
        if activity_zones_data and i < len(activity_zones_data):
            zone_payload = activity_zones_data[i]

        if zone_payload:
            for zone_entry in zone_payload:
                if zone_entry.get("type") == "heartrate":
                    buckets = zone_entry.get("distribution_buckets", [])
                    for j, bucket in enumerate(buckets[:5]):
                        t = bucket.get("time", 0)
                        zone_seconds[j] += t
                        total_tracked_seconds += t
            continue  # detailed data used; skip estimation

        # Estimation fallback: assume average HR represents the whole activity
        avg_hr = act.average_heartrate
        if avg_hr:
            z = _zone_for_hr(int(avg_hr), zone_ranges)
            zone_seconds[z] += moving_s
            total_tracked_seconds += moving_s

    avg_hr_overall = (
        round(total_hr_sum / activities_with_hr, 1) if activities_with_hr else None
    )

    zones: List[HRZoneBucket] = []
    for j in range(5):
        lo, hi = zone_ranges[j]
        pct = (
            round(zone_seconds[j] / total_tracked_seconds * 100, 1)
            if total_tracked_seconds
            else 0.0
        )
        zones.append(
            HRZoneBucket(
                zone=j + 1,
                label=_ZONE_LABELS[j],
                min_hr=lo,
                max_hr=hi,
                seconds=zone_seconds[j],
                percentage=pct,
                formatted_time=_format_hm(zone_seconds[j]),
            )
        )

    return HRZoneAnalysisResponse(
        period=period,
        sport_type=sport_type,
        activities_with_hr=activities_with_hr,
        total_tracked_seconds=total_tracked_seconds,
        zones=zones,
        avg_heartrate=avg_hr_overall,
        max_heartrate_recorded=max_hr_recorded if max_hr_recorded else None,
    )
