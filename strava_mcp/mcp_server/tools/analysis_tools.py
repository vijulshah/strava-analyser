"""MCP tools – all cross-activity analysis functions.

These tools enable Claude to answer complex questions about training data:
- Aggregate stats for any time period
- Performance trends over time
- HR zone distribution
- Power zone analysis
- Personal records
- Segment effort comparison
- Period-vs-period comparison
- Weekly breakdown
- Single activity deep insight
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.types import TextContent, Tool

from strava_mcp.analysis.aggregator import aggregate_activities
from strava_mcp.analysis.cross_query import analyse_weekly_breakdown, compare_periods
from strava_mcp.analysis.heart_rate import analyse_hr_zones
from strava_mcp.analysis.performance import analyse_performance_trend
from strava_mcp.analysis.power import analyse_power_zones
from strava_mcp.analysis.segment_analysis import (
    compare_segment_efforts,
    find_personal_records_from_activities,
)
from strava_mcp.client.base import StravaClient
from strava_mcp.models.activity import DetailedActivity, SummaryActivity
from strava_mcp.models.filters import (
    ActivityFilter,
    TimeRangePreset,
    human_label,
    preset_to_epoch_range,
)
from strava_mcp.models.responses import (
    PeriodLabel,
    PersonalRecord,
    PersonalRecordsResponse,
)
from strava_mcp.models.segment import DetailedSegmentEffort


_PRESET_SCHEMA = {
    "type": "string",
    "enum": [
        "today",
        "last_7_days",
        "last_14_days",
        "last_30_days",
        "last_3_months",
        "last_6_months",
        "last_year",
        "this_year",
        "all_time",
        "custom",
    ],
    "default": "last_30_days",
    "description": "Pre-defined time range preset.",
}

ANALYSIS_TOOLS: list[Tool] = [
    Tool(
        name="analyze_period_summary",
        description=(
            "Aggregate total distance, moving time, elevation gain, and per-sport breakdown "
            "for a specified time period. "
            "Answers: 'How much did I run last month?', 'What are my YTD totals?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset": _PRESET_SCHEMA,
                "after_date": {
                    "type": "string",
                    "description": "ISO 8601 start date (preset='custom').",
                },
                "before_date": {
                    "type": "string",
                    "description": "ISO 8601 end date (preset='custom').",
                },
                "sport_type": {
                    "type": "string",
                    "description": "Restrict to this sport, e.g. 'Run'.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="analyze_performance_trend",
        description=(
            "Compute performance trend over time – pace, speed, distance per activity. "
            "Returns linear trend slopes to show if you're improving or declining. "
            "Answers: 'Am I getting faster?', 'Is my training volume increasing?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset": _PRESET_SCHEMA,
                "after_date": {"type": "string"},
                "before_date": {"type": "string"},
                "sport_type": {"type": "string", "description": "e.g. 'Run', 'Ride'"},
            },
            "required": [],
        },
    ),
    Tool(
        name="analyze_hr_zones",
        description=(
            "Show how much time was spent in each of 5 heart rate zones (Z1–Z5) "
            "across all activities in a period. "
            "Answers: 'How much Zone 2 training did I do?', 'What is my aerobic base percentage?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset": _PRESET_SCHEMA,
                "after_date": {"type": "string"},
                "before_date": {"type": "string"},
                "sport_type": {"type": "string"},
                "max_hr": {
                    "type": "integer",
                    "default": 190,
                    "minimum": 100,
                    "maximum": 220,
                    "description": "Athlete maximum HR for zone calculation.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="analyze_power_zones",
        description=(
            "Show time distribution across 7 Coggan power zones for cycling activities. "
            "Requires FTP to calculate zone boundaries. "
            "Answers: 'How much threshold riding did I do?', 'What is my training polarisation?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset": _PRESET_SCHEMA,
                "after_date": {"type": "string"},
                "before_date": {"type": "string"},
                "sport_type": {"type": "string", "default": "Ride"},
                "ftp": {
                    "type": "integer",
                    "default": 200,
                    "minimum": 50,
                    "maximum": 600,
                    "description": "Athlete FTP in watts.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="find_personal_records",
        description=(
            "Find personal records: longest distance, highest average speed, "
            "most elevation gain, by sport type. "
            "Answers: 'What is my longest run?', 'What was my best cycling day?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset": _PRESET_SCHEMA,
                "after_date": {"type": "string"},
                "before_date": {"type": "string"},
                "sport_type": {"type": "string"},
            },
            "required": [],
        },
    ),
    Tool(
        name="compare_segment_efforts",
        description=(
            "Compare all of the athlete's efforts on a specific segment, ranked fastest to slowest. "
            "Shows PR, KOM status, HR and power data per effort. "
            "Answers: 'How do my hill repeat times compare?', 'When was my PR on this segment?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "segment_id": {
                    "type": "integer",
                    "description": "Strava segment ID to compare efforts on.",
                },
                "after_date": {
                    "type": "string",
                    "description": "Only include efforts after this date.",
                },
                "before_date": {
                    "type": "string",
                    "description": "Only include efforts before this date.",
                },
            },
            "required": ["segment_id"],
        },
    ),
    Tool(
        name="compare_periods",
        description=(
            "Compare training volume and intensity between two time periods side-by-side. "
            "Shows % change in distance, activity count, elevation, and pace. "
            "Answers: 'Did I train more this month vs last month?', 'How does this year compare?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset_a": {**_PRESET_SCHEMA, "description": "First period preset."},
                "after_a": {
                    "type": "string",
                    "description": "Custom start for period A.",
                },
                "before_a": {
                    "type": "string",
                    "description": "Custom end for period A.",
                },
                "preset_b": {
                    **_PRESET_SCHEMA,
                    "default": "last_year",
                    "description": "Second period preset.",
                },
                "after_b": {
                    "type": "string",
                    "description": "Custom start for period B.",
                },
                "before_b": {
                    "type": "string",
                    "description": "Custom end for period B.",
                },
                "sport_type": {"type": "string"},
            },
            "required": [],
        },
    ),
    Tool(
        name="analyze_weekly_breakdown",
        description=(
            "Break down training by calendar week: distance, time, elevation per week. "
            "Identifies the busiest and quietest weeks. "
            "Answers: 'Which was my biggest training week?', 'How has my weekly mileage changed?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "preset": _PRESET_SCHEMA,
                "after_date": {"type": "string"},
                "before_date": {"type": "string"},
                "sport_type": {"type": "string"},
            },
            "required": [],
        },
    ),
    Tool(
        name="get_activity_insights",
        description=(
            "Get a deep analytical summary of a single activity. "
            "Includes pace, HR/power zone distribution, gear, device, highlights, and all key metrics. "
            "Answers: 'Analyse my Sunday run in detail.', 'What were my power zones for yesterday's ride?'"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "activity_id": {
                    "type": "integer",
                    "description": "Strava activity ID.",
                },
                "max_hr": {
                    "type": "integer",
                    "default": 190,
                    "minimum": 100,
                    "maximum": 220,
                    "description": "Athlete max HR for zone analysis.",
                },
                "ftp": {
                    "type": "integer",
                    "default": 200,
                    "minimum": 50,
                    "maximum": 600,
                    "description": "Athlete FTP for power zone analysis.",
                },
            },
            "required": ["activity_id"],
        },
    ),
]


# ---------------------------------------------------------------------------
# Helper: fetch activities for a preset
# ---------------------------------------------------------------------------


async def _fetch_activities(
    client: StravaClient,
    preset: TimeRangePreset,
    after_epoch: Optional[int],
    before_epoch: Optional[int],
    sport_type: Optional[str] = None,
    max_activities: int = 200,
) -> List[SummaryActivity]:
    raw: List[Dict[str, Any]] = await client.list_activities(
        after=after_epoch,
        before=before_epoch,
        per_page=max_activities,
        page=1,
    )
    activities = [SummaryActivity.model_validate(a) for a in raw]
    if sport_type:
        activities = [
            a
            for a in activities
            if (a.sport_type and a.sport_type.value == sport_type)
            or (a.type and a.type.value == sport_type)
        ]
    return activities


def _parse_args_common(args: Dict[str, Any]):
    preset_str: str = args.get("preset", "last_30_days")
    preset = TimeRangePreset(preset_str)
    after_str: Optional[str] = args.get("after_date")
    before_str: Optional[str] = args.get("before_date")
    after_dt = datetime.fromisoformat(after_str) if after_str else None
    before_dt = datetime.fromisoformat(before_str) if before_str else None
    after_epoch, before_epoch = preset_to_epoch_range(preset, after_dt, before_dt)
    sport_type: Optional[str] = args.get("sport_type")
    return preset, after_epoch, before_epoch, sport_type


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def handle_analyze_period_summary(args: Dict[str, Any]) -> list[TextContent]:
    preset, after_epoch, before_epoch, sport_type = _parse_args_common(args)
    async with StravaClient() as client:
        activities = await _fetch_activities(
            client, preset, after_epoch, before_epoch, sport_type
        )
    result = aggregate_activities(
        activities,
        preset_label=human_label(preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_analyze_performance_trend(args: Dict[str, Any]) -> list[TextContent]:
    preset, after_epoch, before_epoch, sport_type = _parse_args_common(args)
    async with StravaClient() as client:
        activities = await _fetch_activities(
            client, preset, after_epoch, before_epoch, sport_type
        )
    result = analyse_performance_trend(
        activities,
        sport_type=sport_type,
        preset_label=human_label(preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_analyze_hr_zones(args: Dict[str, Any]) -> list[TextContent]:
    preset, after_epoch, before_epoch, sport_type = _parse_args_common(args)
    max_hr: int = int(args.get("max_hr", 190))
    async with StravaClient() as client:
        activities = await _fetch_activities(
            client, preset, after_epoch, before_epoch, sport_type
        )
    result = analyse_hr_zones(
        activities,
        max_hr=max_hr,
        sport_type=sport_type,
        preset_label=human_label(preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_analyze_power_zones(args: Dict[str, Any]) -> list[TextContent]:
    preset, after_epoch, before_epoch, sport_type = _parse_args_common(args)
    ftp: int = int(args.get("ftp", 200))
    async with StravaClient() as client:
        activities = await _fetch_activities(
            client, preset, after_epoch, before_epoch, sport_type
        )
    result = analyse_power_zones(
        activities,
        ftp=ftp,
        sport_type=sport_type,
        preset_label=human_label(preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_find_personal_records(args: Dict[str, Any]) -> list[TextContent]:
    preset, after_epoch, before_epoch, sport_type = _parse_args_common(args)
    async with StravaClient() as client:
        activities = await _fetch_activities(
            client, preset, after_epoch, before_epoch, sport_type
        )
    pr_data = find_personal_records_from_activities(activities)
    records: List[PersonalRecord] = []
    for sport, metrics in pr_data.items():
        for metric, info in metrics.items():
            if metric == "longest_distance":
                val_f = round(info["value"] / 1000, 3)
                unit = "km"
            elif metric == "fastest_avg_speed":
                val_f = round(info["value"] * 3.6, 2)
                unit = "km/h"
            else:
                val_f = round(info["value"], 1)
                unit = "m"
            records.append(
                PersonalRecord(
                    sport_type=sport,
                    metric=metric,
                    value=val_f,
                    unit=unit,
                    value_formatted=f"{val_f} {unit}",
                    activity_id=info["activity_id"],
                    activity_name=info["name"],
                    date=info["date"],
                )
            )
    period = PeriodLabel(
        label=human_label(preset), after=after_epoch, before=before_epoch
    )
    result = PersonalRecordsResponse(
        period=period,
        sport_type=sport_type,
        records=records,
        total_activities_analysed=len(activities),
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_compare_segment_efforts(args: Dict[str, Any]) -> list[TextContent]:
    segment_id: int = int(args["segment_id"])
    after_str: Optional[str] = args.get("after_date")
    before_str: Optional[str] = args.get("before_date")
    async with StravaClient() as client:
        seg_data = await client.get_segment(segment_id)
        efforts_raw: List[Dict[str, Any]] = await client.get_segment_efforts(
            segment_id=segment_id,
            start_date_local=after_str,
            end_date_local=before_str,
            per_page=200,
        )
    from strava_mcp.models.segment import DetailedSegment

    seg = DetailedSegment.model_validate(seg_data)
    efforts = [DetailedSegmentEffort.model_validate(e) for e in efforts_raw]
    result = compare_segment_efforts(
        efforts=efforts,
        segment_id=segment_id,
        segment_name=seg.name,
        segment_distance_m=seg.distance,
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_compare_periods(args: Dict[str, Any]) -> list[TextContent]:
    preset_a = TimeRangePreset(args.get("preset_a", "last_30_days"))
    preset_b = TimeRangePreset(args.get("preset_b", "last_year"))
    after_a = datetime.fromisoformat(args["after_a"]) if args.get("after_a") else None
    before_a = (
        datetime.fromisoformat(args["before_a"]) if args.get("before_a") else None
    )
    after_b = datetime.fromisoformat(args["after_b"]) if args.get("after_b") else None
    before_b = (
        datetime.fromisoformat(args["before_b"]) if args.get("before_b") else None
    )
    sport_type: Optional[str] = args.get("sport_type")

    ea_a, eb_a = preset_to_epoch_range(preset_a, after_a, before_a)
    ea_b, eb_b = preset_to_epoch_range(preset_b, after_b, before_b)
    overall_after = min((x for x in [ea_a, ea_b] if x is not None), default=None)
    overall_before = max((x for x in [eb_a, eb_b] if x is not None), default=None)

    async with StravaClient() as client:
        raw: List[Dict[str, Any]] = await client.list_activities(
            after=overall_after, before=overall_before, per_page=200, page=1
        )
    all_activities = [SummaryActivity.model_validate(a) for a in raw]
    filter_a = ActivityFilter(preset=preset_a, after_date=after_a, before_date=before_a)
    filter_b = ActivityFilter(preset=preset_b, after_date=after_b, before_date=before_b)
    result = compare_periods(
        all_activities=all_activities,
        filter_a=filter_a,
        filter_b=filter_b,
        sport_type=sport_type,
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_analyze_weekly_breakdown(args: Dict[str, Any]) -> list[TextContent]:
    preset, after_epoch, before_epoch, sport_type = _parse_args_common(args)
    async with StravaClient() as client:
        activities = await _fetch_activities(
            client, preset, after_epoch, before_epoch, sport_type
        )
    result = analyse_weekly_breakdown(
        activities=activities,
        sport_type=sport_type,
        preset_label=human_label(preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]


async def handle_get_activity_insights(args: Dict[str, Any]) -> list[TextContent]:
    """Deep analytical summary of a single activity."""
    from strava_mcp.analysis.heart_rate import (
        _default_zone_ranges,
        _format_hm,
        _ZONE_LABELS,
    )
    from strava_mcp.analysis.power import _power_zone_ranges, _ZONE_NAMES
    from strava_mcp.models.responses import (
        ActivityInsightResponse,
        HRZoneBucket,
        PowerZoneBucket,
    )

    activity_id: int = int(args["activity_id"])
    max_hr: int = int(args.get("max_hr", 190))
    ftp: int = int(args.get("ftp", 200))

    async with StravaClient() as client:
        act_data = await client.get_activity(activity_id, include_all_efforts=True)
        zone_data: List[Dict[str, Any]] = []
        try:
            zone_data = await client.get_activity_zones(activity_id)
        except Exception:
            pass

    act = DetailedActivity.model_validate(act_data)
    hr_zone_ranges = _default_zone_ranges(max_hr)
    pw_zone_ranges = _power_zone_ranges(ftp)

    hr_zones = None
    pw_zones = None
    if zone_data:
        hr_sec = [0] * 5
        pw_sec = [0] * 7
        total_hr_t = total_pw_t = 0
        for ze in zone_data:
            if ze.get("type") == "heartrate":
                for j, b in enumerate(ze.get("distribution_buckets", [])[:5]):
                    t = b.get("time", 0)
                    hr_sec[j] += t
                    total_hr_t += t
            elif ze.get("type") == "power":
                for j, b in enumerate(ze.get("distribution_buckets", [])[:7]):
                    t = b.get("time", 0)
                    pw_sec[j] += t
                    total_pw_t += t
        if total_hr_t:
            hr_zones = [
                HRZoneBucket(
                    zone=j + 1,
                    label=_ZONE_LABELS[j],
                    min_hr=hr_zone_ranges[j][0],
                    max_hr=hr_zone_ranges[j][1],
                    seconds=hr_sec[j],
                    percentage=round(hr_sec[j] / total_hr_t * 100, 1),
                    formatted_time=_format_hm(hr_sec[j]),
                )
                for j in range(5)
            ]
        if total_pw_t:
            pw_zones = [
                PowerZoneBucket(
                    zone=j + 1,
                    label=_ZONE_NAMES[j],
                    min_watts=pw_zone_ranges[j][0],
                    max_watts=pw_zone_ranges[j][1],
                    seconds=pw_sec[j],
                    percentage=round(pw_sec[j] / total_pw_t * 100, 1),
                    formatted_time=_format_hm(pw_sec[j]),
                )
                for j in range(7)
            ]

    highlights: List[str] = []
    if act.distance:
        highlights.append(f"Distance: {round(act.distance/1000, 2)} km")
    if act.moving_time:
        h, rem = divmod(act.moving_time, 3600)
        m, s = divmod(rem, 60)
        highlights.append(f"Moving time: {h:02d}:{m:02d}:{s:02d}")
    if act.average_heartrate:
        highlights.append(f"Average HR: {act.average_heartrate:.0f} bpm")
    if act.average_watts:
        highlights.append(f"Average power: {act.average_watts:.0f} W")
    if act.total_elevation_gain:
        highlights.append(f"Elevation gain: {act.total_elevation_gain:.0f} m")
    if act.achievement_count:
        highlights.append(f"Achievements: {act.achievement_count}")
    if act.pr_count:
        highlights.append(f"PRs: {act.pr_count}")

    avg_speed_ms = act.average_speed
    avg_speed_kmh = round(avg_speed_ms * 3.6, 2) if avg_speed_ms else None
    avg_pace = round(1000 / (avg_speed_ms * 60), 3) if avg_speed_ms else None
    moving_t_fmt = None
    if act.moving_time:
        h, rem = divmod(act.moving_time, 3600)
        m, s = divmod(rem, 60)
        moving_t_fmt = f"{h:02d}:{m:02d}:{s:02d}"

    result = ActivityInsightResponse(
        activity_id=act.id,
        name=act.name,
        sport_type=(act.sport_type.value if act.sport_type else None)
        or (act.type.value if act.type else None),
        date=act.start_date,
        distance_km=round(act.distance / 1000, 3) if act.distance else None,
        moving_time_formatted=moving_t_fmt,
        avg_speed_kmh=avg_speed_kmh,
        avg_pace_min_per_km=avg_pace,
        avg_heartrate=act.average_heartrate,
        max_heartrate=act.max_heartrate,
        avg_watts=act.average_watts,
        weighted_avg_watts=(
            float(act.weighted_average_watts) if act.weighted_average_watts else None
        ),
        elevation_gain_m=act.total_elevation_gain,
        calories=getattr(act, "calories", None),
        suffer_score=act.suffer_score,
        perceived_exertion=getattr(act, "perceived_exertion", None),
        achievements=act.achievement_count,
        kudos=act.kudos_count,
        pr_count=act.pr_count,
        hr_zone_distribution=hr_zones,
        power_zone_distribution=pw_zones,
        lap_count=len(act.laps) if act.laps else None,
        highlights=highlights,
        gear_name=act.gear.name if act.gear else None,
        device_name=getattr(act, "device_name", None),
    )
    return [TextContent(type="text", text=result.model_dump_json(indent=2))]
