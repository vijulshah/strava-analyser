"""Power zone analysis.

Computes time-in-power-zone distribution and key power metrics from a list
of activities. Power zones follow the Coggan 7-zone model relative to FTP.

Zone  | Name                | % FTP
------|---------------------|-------
1     | Active Recovery     | < 55
2     | Endurance           | 55–75
3     | Tempo               | 75–90
4     | Lactate Threshold   | 90–105
5     | VO2 Max             | 105–120
6     | Anaerobic Capacity  | 120–150
7     | Neuromuscular       | > 150
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from strava_mcp.models.activity import SummaryActivity
from strava_mcp.models.filters import ActivityFilter, human_label
from strava_mcp.models.responses import (
    PowerAnalysisResponse,
    PowerZoneBucket,
    PeriodLabel,
)

_DEFAULT_FTP: int = 200
_ZONE_NAMES: List[str] = [
    "Zone 1 – Active Recovery",
    "Zone 2 – Endurance",
    "Zone 3 – Tempo",
    "Zone 4 – Lactate Threshold",
    "Zone 5 – VO2 Max",
    "Zone 6 – Anaerobic Capacity",
    "Zone 7 – Neuromuscular",
]
_ZONE_FTP_PCTS: List[float] = [0.0, 0.55, 0.75, 0.90, 1.05, 1.20, 1.50, 9999.0]


def _format_hm(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    if h:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def _power_zone_ranges(ftp: int) -> List[Tuple[int, int]]:
    """Compute 7 power zone boundaries from FTP.

    Args:
        ftp: Functional Threshold Power in watts.

    Returns:
        List of ``(min_watts, max_watts)`` for each zone.
    """
    boundaries = [int(ftp * pct) for pct in _ZONE_FTP_PCTS]
    return [(boundaries[i], boundaries[i + 1] - 1) for i in range(7)]


def _zone_for_watts(watts: int, zone_ranges: List[Tuple[int, int]]) -> int:
    for i, (lo, hi) in enumerate(zone_ranges):
        if lo <= watts <= hi:
            return i
    return len(zone_ranges) - 1


def analyse_power_zones(
    activities: List[SummaryActivity],
    activity_zones_data: Optional[List[List[Dict]]] = None,
    ftp: int = _DEFAULT_FTP,
    sport_type: Optional[str] = None,
    activity_filter: Optional[ActivityFilter] = None,
    preset_label: str = "Selected period",
    after_epoch: Optional[int] = None,
    before_epoch: Optional[int] = None,
) -> PowerAnalysisResponse:
    """Compute power zone distribution across a list of activities.

    Args:
        activities: Fetched SummaryActivity objects.
        activity_zones_data: Optional per-activity Strava zone payloads.
        ftp: Athlete's FTP for zone boundary calculation.
        sport_type: Optional sport filter.
        activity_filter: Filter for label generation.
        preset_label: Fallback period label.
        after_epoch: Start epoch.
        before_epoch: End epoch.

    Returns:
        :class:`PowerAnalysisResponse`.
    """
    if activity_filter is not None:
        label = human_label(activity_filter.preset)
        after_epoch, before_epoch = activity_filter.to_epoch_range()
    else:
        label = preset_label

    period = PeriodLabel(label=label, after=after_epoch, before=before_epoch)
    zone_ranges = _power_zone_ranges(ftp)

    filtered = [
        a for a in activities
        if sport_type is None
        or (a.sport_type and a.sport_type.value == sport_type)
        or (a.type and a.type.value == sport_type)
    ]

    zone_seconds: List[int] = [0] * 7
    acts_with_power = 0
    total_tracked = 0
    power_sum = 0.0
    norm_power_sum = 0.0
    max_power_recorded = 0.0
    total_kj = 0.0

    for i, act in enumerate(filtered):
        if not act.average_watts and not act.weighted_average_watts:
            continue
        acts_with_power += 1
        moving_s = act.moving_time or 0
        avg_w = act.average_watts or 0.0
        norm_w = act.weighted_average_watts or 0.0
        power_sum += avg_w
        norm_power_sum += norm_w
        if act.kilojoules:
            total_kj += act.kilojoules
        if act.max_watts and act.max_watts > max_power_recorded:
            max_power_recorded = float(act.max_watts)

        zone_payload: Optional[List[Dict]] = None
        if activity_zones_data and i < len(activity_zones_data):
            zone_payload = activity_zones_data[i]

        if zone_payload:
            for zone_entry in zone_payload:
                if zone_entry.get("type") == "power":
                    buckets = zone_entry.get("distribution_buckets", [])
                    for j, bucket in enumerate(buckets[:7]):
                        t = bucket.get("time", 0)
                        zone_seconds[j] += t
                        total_tracked += t
            continue

        # Estimation: place whole activity in zone for its average watts
        if avg_w:
            z = _zone_for_watts(int(avg_w), zone_ranges)
            zone_seconds[z] += moving_s
            total_tracked += moving_s

    zones: List[PowerZoneBucket] = []
    for j in range(7):
        lo, hi = zone_ranges[j]
        pct = (
            round(zone_seconds[j] / total_tracked * 100, 1) if total_tracked else 0.0
        )
        zones.append(
            PowerZoneBucket(
                zone=j + 1,
                label=_ZONE_NAMES[j],
                min_watts=lo,
                max_watts=hi,
                seconds=zone_seconds[j],
                percentage=pct,
                formatted_time=_format_hm(zone_seconds[j]),
            )
        )

    return PowerAnalysisResponse(
        period=period,
        sport_type=sport_type,
        activities_with_power=acts_with_power,
        ftp=ftp,
        zones=zones,
        avg_power=round(power_sum / acts_with_power, 1) if acts_with_power else None,
        avg_weighted_power=round(norm_power_sum / acts_with_power, 1) if acts_with_power else None,
        max_power_recorded=max_power_recorded if max_power_recorded else None,
        total_kilojoules=round(total_kj, 1) if total_kj else None,
    )
