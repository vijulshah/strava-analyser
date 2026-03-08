"""Analysis router – all cross-activity analysis endpoints.

Every endpoint accepts a Pydantic request body and returns a typed
Pydantic response model so the Swagger UI shows full request/response
schemas.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from strava_mcp.analysis.aggregator import aggregate_activities
from strava_mcp.analysis.cross_query import analyse_weekly_breakdown, compare_periods
from strava_mcp.analysis.heart_rate import analyse_hr_zones
from strava_mcp.analysis.performance import analyse_performance_trend
from strava_mcp.analysis.power import analyse_power_zones
from strava_mcp.analysis.segment_analysis import (
    compare_segment_efforts,
    find_personal_records_from_activities,
)
from strava_mcp.api.dependencies import get_client
from strava_mcp.api.schemas.analysis_schemas import (
    ActivityInsightRequest,
    ComparePeriodRequest,
    HRZoneRequest,
    PersonalRecordsRequest,
    PerformanceTrendRequest,
    PowerZoneRequest,
    SegmentComparisonRequest,
    SummaryRequest,
    WeeklyBreakdownRequest,
)
from strava_mcp.client.base import StravaClient
from strava_mcp.models.activity import DetailedActivity, SummaryActivity
from strava_mcp.models.filters import (
    ActivityFilter,
    TimeRangePreset,
    preset_to_epoch_range,
)
from strava_mcp.models.responses import (
    ActivityInsightResponse,
    AggregatedStatsResponse,
    HRZoneAnalysisResponse,
    PeriodComparisonResponse,
    PerformanceTrendResponse,
    PersonalRecord,
    PersonalRecordsResponse,
    PowerAnalysisResponse,
    SegmentComparisonResponse,
    WeeklyBreakdownResponse,
    PeriodLabel,
)
from strava_mcp.models.segment import DetailedSegmentEffort
from strava_mcp.analysis.heart_rate import _format_hm

router = APIRouter(prefix="/analysis", tags=["Analysis"])

ClientDep = Annotated[StravaClient, Depends(get_client)]

_MAX_FETCH = 200  # Max activities fetched for analysis


async def _fetch_activities(
    client: StravaClient,
    preset: TimeRangePreset,
    after_epoch: Optional[int],
    before_epoch: Optional[int],
    sport_type: Optional[str] = None,
    max_activities: int = _MAX_FETCH,
) -> List[SummaryActivity]:
    """Fetch up to ``max_activities`` from Strava and optionally filter by sport."""
    raw: List[Dict[str, Any]] = await client.list_activities(
        after=after_epoch, before=before_epoch, per_page=max_activities, page=1
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


@router.post(
    "/summary",
    response_model=AggregatedStatsResponse,
    summary="Aggregate activity statistics for a period",
    response_description="Totals and per-sport breakdown for the selected period.",
)
async def analysis_summary(
    body: SummaryRequest, client: ClientDep
) -> AggregatedStatsResponse:
    """Return distance, time, elevation, and per-sport totals for a time range.

    Useful for questions like *"How much did I run last month?"* or
    *"What are my totals for this year?"*.
    """
    after_epoch, before_epoch = preset_to_epoch_range(
        body.preset, body.after_date, body.before_date
    )
    activities = await _fetch_activities(
        client, body.preset, after_epoch, before_epoch, body.sport_type
    )
    from strava_mcp.models.filters import human_label

    return aggregate_activities(
        activities,
        preset_label=human_label(body.preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )


@router.post(
    "/performance-trend",
    response_model=PerformanceTrendResponse,
    summary="Analyse performance trend over time",
    response_description="Per-activity data points with linear trend slopes.",
)
async def analysis_performance_trend(
    body: PerformanceTrendRequest, client: ClientDep
) -> PerformanceTrendResponse:
    """Return performance trend analysis – pace, speed, and volume over time.

    Answers questions like *"Am I getting faster?"* or
    *"Is my weekly mileage increasing?"*.
    """
    after_epoch, before_epoch = preset_to_epoch_range(
        body.preset, body.after_date, body.before_date
    )
    activities = await _fetch_activities(
        client, body.preset, after_epoch, before_epoch, body.sport_type
    )
    from strava_mcp.models.filters import human_label

    return analyse_performance_trend(
        activities,
        sport_type=body.sport_type,
        preset_label=human_label(body.preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )


@router.post(
    "/hr-zones",
    response_model=HRZoneAnalysisResponse,
    summary="Analyse heart rate zone distribution",
    response_description="Time spent in each of 5 HR zones.",
)
async def analysis_hr_zones(
    body: HRZoneRequest, client: ClientDep
) -> HRZoneAnalysisResponse:
    """Return heart rate zone distribution for a period.

    Answers *"How much time did I spend in Zone 2?"* or
    *"What is my aerobic base training breakdown?"*.
    """
    after_epoch, before_epoch = preset_to_epoch_range(
        body.preset, body.after_date, body.before_date
    )
    activities = await _fetch_activities(
        client, body.preset, after_epoch, before_epoch, body.sport_type
    )
    from strava_mcp.models.filters import human_label

    return analyse_hr_zones(
        activities,
        max_hr=body.max_hr,
        sport_type=body.sport_type,
        preset_label=human_label(body.preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )


@router.post(
    "/power",
    response_model=PowerAnalysisResponse,
    summary="Analyse power zone distribution",
    response_description="Time spent in each of 7 Coggan power zones.",
)
async def analysis_power_zones(
    body: PowerZoneRequest, client: ClientDep
) -> PowerAnalysisResponse:
    """Return power zone distribution for cycling activities in a period.

    Answers *"How much time did I ride at threshold power?"* or
    *"What is my training polarisation?"*.
    """
    after_epoch, before_epoch = preset_to_epoch_range(
        body.preset, body.after_date, body.before_date
    )
    activities = await _fetch_activities(
        client, body.preset, after_epoch, before_epoch, body.sport_type
    )
    from strava_mcp.models.filters import human_label

    return analyse_power_zones(
        activities,
        ftp=body.ftp,
        sport_type=body.sport_type,
        preset_label=human_label(body.preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )


@router.post(
    "/personal-records",
    response_model=PersonalRecordsResponse,
    summary="Find personal records",
    response_description="Best performances by sport type.",
)
async def analysis_personal_records(
    body: PersonalRecordsRequest, client: ClientDep
) -> PersonalRecordsResponse:
    """Find personal records (longest distance, fastest speed, most elevation) across activities.

    Answers *"What is my longest run ever?"* or *"What was my best cycling day?"*.
    """
    after_epoch, before_epoch = preset_to_epoch_range(
        body.preset, body.after_date, body.before_date
    )
    activities = await _fetch_activities(
        client, body.preset, after_epoch, before_epoch, body.sport_type
    )
    from strava_mcp.models.filters import human_label

    pr_data = find_personal_records_from_activities(activities)

    records: List[PersonalRecord] = []
    for sport, metrics in pr_data.items():
        for metric, info in metrics.items():
            unit_map = {
                "longest_distance": ("m", "km"),
                "fastest_avg_speed": ("m/s", "km/h"),
                "most_elevation": ("m", "m"),
            }
            if metric in unit_map:
                _, display_unit = unit_map[metric]
                val = info["value"]
                if metric == "longest_distance":
                    val_f = round(val / 1000, 3)
                    unit = "km"
                elif metric == "fastest_avg_speed":
                    val_f = round(val * 3.6, 2)
                    unit = "km/h"
                else:
                    val_f = round(val, 1)
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
        label=human_label(body.preset), after=after_epoch, before=before_epoch
    )
    return PersonalRecordsResponse(
        period=period,
        sport_type=body.sport_type,
        records=records,
        total_activities_analysed=len(activities),
    )


@router.post(
    "/segment-comparison",
    response_model=SegmentComparisonResponse,
    summary="Compare efforts on a segment",
    response_description="All efforts on a segment ranked fastest to slowest.",
)
async def analysis_segment_comparison(
    body: SegmentComparisonRequest, client: ClientDep
) -> SegmentComparisonResponse:
    """Return all efforts on a segment, ranked by elapsed time.

    Answers *"How do my efforts on this climb compare?"* or
    *"When was my PR on this segment?"*.
    """
    from strava_mcp.models.segment import DetailedSegment

    # Fetch segment info
    seg_data: Dict[str, Any] = await client.get_segment(body.segment_id)
    seg = DetailedSegment.model_validate(seg_data)

    after_str = body.after_date.isoformat() if body.after_date else None
    before_str = body.before_date.isoformat() if body.before_date else None

    efforts_raw: List[Dict[str, Any]] = await client.get_segment_efforts(
        segment_id=body.segment_id,
        start_date_local=after_str,
        end_date_local=before_str,
        per_page=200,
    )
    efforts = [DetailedSegmentEffort.model_validate(e) for e in efforts_raw]

    return compare_segment_efforts(
        efforts=efforts,
        segment_id=body.segment_id,
        segment_name=seg.name,
        segment_distance_m=seg.distance,
    )


@router.post(
    "/compare-periods",
    response_model=PeriodComparisonResponse,
    summary="Compare two time periods",
    response_description="Side-by-side metrics for two time periods.",
)
async def analysis_compare_periods(
    body: ComparePeriodRequest, client: ClientDep
) -> PeriodComparisonResponse:
    """Compare your training across two distinct time periods.

    Answers *"Did I train more this month vs last month?"* or
    *"How does this year compare to last year?"*.
    """
    after_a, before_a = preset_to_epoch_range(
        body.preset_a, body.after_a, body.before_a
    )
    after_b, before_b = preset_to_epoch_range(
        body.preset_b, body.after_b, body.before_b
    )

    # Determine the broadest range to fetch all activities at once
    overall_after = min((x for x in [after_a, after_b] if x is not None), default=None)
    overall_before = max(
        (x for x in [before_a, before_b] if x is not None), default=None
    )

    all_raw: List[Dict[str, Any]] = await client.list_activities(
        after=overall_after,
        before=overall_before,
        per_page=200,
        page=1,
    )
    all_activities = [SummaryActivity.model_validate(a) for a in all_raw]

    filter_a = ActivityFilter(
        preset=body.preset_a, after_date=body.after_a, before_date=body.before_a
    )
    filter_b = ActivityFilter(
        preset=body.preset_b, after_date=body.after_b, before_date=body.before_b
    )

    return compare_periods(
        all_activities=all_activities,
        filter_a=filter_a,
        filter_b=filter_b,
        sport_type=body.sport_type,
    )


@router.post(
    "/weekly-breakdown",
    response_model=WeeklyBreakdownResponse,
    summary="Week-over-week breakdown",
    response_description="Activity metrics broken down by calendar week.",
)
async def analysis_weekly_breakdown(
    body: WeeklyBreakdownRequest, client: ClientDep
) -> WeeklyBreakdownResponse:
    """Return a week-by-week breakdown of training volume.

    Answers *"How has my weekly mileage changed?"* or
    *"Which was my biggest training week this year?"*.
    """
    after_epoch, before_epoch = preset_to_epoch_range(
        body.preset, body.after_date, body.before_date
    )
    activities = await _fetch_activities(
        client, body.preset, after_epoch, before_epoch, body.sport_type
    )
    from strava_mcp.models.filters import human_label

    return analyse_weekly_breakdown(
        activities=activities,
        sport_type=body.sport_type,
        preset_label=human_label(body.preset),
        after_epoch=after_epoch,
        before_epoch=before_epoch,
    )


@router.post(
    "/activity-insight",
    response_model=ActivityInsightResponse,
    summary="Get deep insight on a single activity",
    response_description="Analytical summary with HR zones, highlights, and key metrics.",
)
async def analysis_activity_insight(
    body: ActivityInsightRequest, client: ClientDep
) -> ActivityInsightResponse:
    """Return a rich analytical summary of a single activity.

    Includes pace, HR/power zone distribution, gear, highlights, and key metrics.
    Answers *"Give me a detailed analysis of my Sunday run."*.
    """
    from strava_mcp.analysis.heart_rate import (
        analyse_hr_zones as _hr_zones,
        _default_zone_ranges,
        _zone_for_hr,
        _ZONE_LABELS,
    )
    from strava_mcp.analysis.power import (
        analyse_power_zones as _pw_zones,
        _power_zone_ranges,
        _zone_for_watts,
        _ZONE_NAMES,
    )
    from strava_mcp.models.responses import HRZoneBucket, PowerZoneBucket

    act_data: Dict[str, Any] = await client.get_activity(
        body.activity_id, include_all_efforts=True
    )
    act = DetailedActivity.model_validate(act_data)

    # Fetch zones if available
    zone_data: List[Dict[str, Any]] = []
    try:
        zone_data = await client.get_activity_zones(body.activity_id)
    except Exception:
        pass

    # Build HR zone distribution
    hr_zones: Optional[List[HRZoneBucket]] = None
    pw_zones: Optional[List[PowerZoneBucket]] = None

    hr_zone_ranges = _default_zone_ranges(body.max_hr)
    pw_zone_ranges = _power_zone_ranges(body.ftp)

    if zone_data:
        hr_sec = [0] * 5
        pw_sec = [0] * 7
        total_hr_t = 0
        total_pw_t = 0
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

    # Build highlights
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
    if act.suffer_score:
        highlights.append(f"Suffer score: {act.suffer_score:.0f}")

    avg_speed_ms = act.average_speed
    avg_pace = None
    avg_speed_kmh = None
    if avg_speed_ms:
        avg_speed_kmh = round(avg_speed_ms * 3.6, 2)
        if avg_speed_ms > 0:
            avg_pace = round(1000 / (avg_speed_ms * 60), 3)

    moving_t_fmt = None
    if act.moving_time:
        h, rem = divmod(act.moving_time, 3600)
        m, s = divmod(rem, 60)
        moving_t_fmt = f"{h:02d}:{m:02d}:{s:02d}"

    return ActivityInsightResponse(
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
        calories=act.calories,  # type: ignore[attr-defined]
        suffer_score=act.suffer_score,
        perceived_exertion=act.perceived_exertion,  # type: ignore[attr-defined]
        achievements=act.achievement_count,
        kudos=act.kudos_count,
        pr_count=act.pr_count,
        hr_zone_distribution=hr_zones,
        power_zone_distribution=pw_zones,
        lap_count=len(act.laps) if act.laps else None,
        highlights=highlights,
        gear_name=act.gear.name if act.gear else None,
        device_name=act.device_name,  # type: ignore[attr-defined]
    )
