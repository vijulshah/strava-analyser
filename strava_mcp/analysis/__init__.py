"""Analysis package – all cross-activity analysis functions."""

from strava_mcp.analysis.aggregator import aggregate_activities
from strava_mcp.analysis.performance import analyse_performance_trend
from strava_mcp.analysis.heart_rate import analyse_hr_zones
from strava_mcp.analysis.power import analyse_power_zones
from strava_mcp.analysis.segment_analysis import compare_segment_efforts
from strava_mcp.analysis.cross_query import compare_periods, analyse_weekly_breakdown

__all__ = [
    "aggregate_activities",
    "analyse_performance_trend",
    "analyse_hr_zones",
    "analyse_power_zones",
    "compare_segment_efforts",
    "compare_periods",
    "analyse_weekly_breakdown",
]
