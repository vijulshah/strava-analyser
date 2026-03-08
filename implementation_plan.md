# Strava MCP Server – Implementation Plan

## Overview

Build a full-featured **Model Context Protocol (MCP) server** for Claude Desktop that exposes all Strava API v3 capabilities. Additionally expose a **FastAPI** application with rich Swagger docs (Pydantic-typed request/response models) so every capability can be accessed and tested independently via REST endpoints.

### Tech Stack
- **Python 3.11+** with full type hints & Google docstrings
- **`mcp`** (Anthropic MCP SDK) for the MCP server
- **FastAPI + Uvicorn** for REST endpoints
- **Pydantic v2** for all models, request/response schemas
- **`httpx`** (async) as the Strava HTTP client
- **`python-dotenv`** for secrets management
- OAuth2 (bearer token with refresh-token flow)

---

## User Review Required

> [!IMPORTANT]
> **Strava OAuth Credentials Required**: You must create an API app at https://www.strava.com/settings/api to get `CLIENT_ID`, `CLIENT_SECRET`, and generate a `REFRESH_TOKEN` with scopes: `activity:read_all`, `profile:read_all`, `read_all`. We will generate a `.env.example` file with all required keys.

> [!IMPORTANT]
> **MCP SDK**: We will use the official `mcp` Python package from Anthropic (`pip install mcp`). The server runs using `stdio` transport, which is the standard for Claude Desktop. The Claude Desktop `claude_desktop_config.json` snippet will be generated.

> [!WARNING]
> **Two Separate Processes**: The MCP server and the FastAPI server are two separate entry points. Claude Desktop connects to MCP; the FastAPI runs independently for testing/REST access. You start them separately.

---

## Proposed Changes

### Project Root: `c:\Projects\strava-mcp`

```
strava-mcp/
├── .env.example
├── .env                        # (not committed)
├── requirements.txt
├── pyproject.toml
├── README.md
├── claude_desktop_config.json  # snippet for Claude Desktop
│
├── strava_mcp/
│   ├── __init__.py
│   ├── config.py               # Settings via pydantic-settings
│   │
│   ├── models/                 # All Pydantic models
│   │   ├── __init__.py
│   │   ├── athlete.py          # DetailedAthlete, SummaryAthlete, Zones
│   │   ├── activity.py         # DetailedActivity, SummaryActivity, Lap, ActivityZone
│   │   ├── segment.py          # DetailedSegment, SummarySegment, SegmentEffort, ExplorerSegment
│   │   ├── club.py             # DetailedClub, SummaryClub, ClubActivity
│   │   ├── gear.py             # DetailedGear, SummaryGear
│   │   ├── route.py            # Route model
│   │   ├── stream.py           # StreamSet, all stream types
│   │   ├── stats.py            # ActivityStats, ActivityTotal
│   │   ├── filters.py          # TimeRangeFilter, ActivityFilter, AnalysisFilter
│   │   └── responses.py        # Analysis response models (Pydantic)
│   │
│   ├── client/                 # Strava API HTTP client
│   │   ├── __init__.py
│   │   ├── auth.py             # OAuth2 token manager (refresh flow)
│   │   ├── base.py             # Base async httpx client with auth
│   │   ├── athletes.py         # Athlete API calls
│   │   ├── activities.py       # Activities API calls
│   │   ├── segments.py         # Segments + SegmentEfforts API calls
│   │   ├── clubs.py            # Clubs API calls
│   │   ├── routes.py           # Routes API calls
│   │   ├── gear.py             # Gear API calls
│   │   └── streams.py          # Streams API calls
│   │
│   ├── analysis/               # Cross-analysis + aggregation
│   │   ├── __init__.py
│   │   ├── performance.py      # Pace/speed trends, personal records
│   │   ├── aggregator.py       # Totals, weekly/monthly/yearly summaries
│   │   ├── heart_rate.py       # HR zone distribution analysis
│   │   ├── power.py            # Power zone analysis
│   │   ├── segment_analysis.py # Segment effort comparison
│   │   └── cross_query.py      # Multi-activity cross comparisons
│   │
│   ├── api/                    # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app, lifespan, global router
│   │   ├── dependencies.py     # Shared deps (get_strava_client)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── athlete.py      # GET /athlete, /athlete/zones, /athlete/stats
│   │   │   ├── activities.py   # GET /activities, /activities/{id}, filters
│   │   │   ├── segments.py     # GET /segments, /segments/{id}, efforts
│   │   │   ├── clubs.py        # GET /clubs, /clubs/{id}
│   │   │   ├── routes.py       # GET /routes, /routes/{id}
│   │   │   ├── gear.py         # GET /gear/{id}
│   │   │   ├── streams.py      # GET /activities/{id}/streams
│   │   │   └── analysis.py     # POST /analysis/* endpoints
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── activity_schemas.py  # Request/response schemas with examples
│   │       ├── analysis_schemas.py  # Analysis request/response schemas
│   │       └── filter_schemas.py    # Filter query schemas
│   │
│   └── mcp_server/             # MCP server
│       ├── __init__.py
│       ├── server.py           # MCP Server entry point (stdio)
│       └── tools/
│           ├── __init__.py
│           ├── athlete_tools.py      # MCP tools: get_profile, get_stats, get_zones
│           ├── activity_tools.py     # MCP tools: get_activities_* (all filters)
│           ├── segment_tools.py      # MCP tools: get_segment, get_efforts
│           ├── club_tools.py         # MCP tools: get_clubs, get_club_members
│           ├── route_tools.py        # MCP tools: list_routes, get_route
│           ├── stream_tools.py       # MCP tools: get_activity_streams
│           └── analysis_tools.py     # MCP tools: all analysis functions
│
└── scripts/
    └── get_refresh_token.py    # Helper script to get OAuth refresh token
```

---

### Component 1: Config & Auth

#### [NEW] `strava_mcp/config.py`
- `StravaSettings` (pydantic-settings) reads `.env`: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REFRESH_TOKEN`, `STRAVA_ACCESS_TOKEN`, `STRAVA_TOKEN_EXPIRY`

#### [NEW] `strava_mcp/client/auth.py`
- `TokenManager` class: stores access token, checks expiry, auto-refreshes using refresh token
- Writes refreshed token back to `.env` so it persists between runs

---

### Component 2: Pydantic Models

#### [NEW] `strava_mcp/models/activity.py`
All Strava activity models: `SportType` enum (40+ values), `ActivityType` enum, `SummaryActivity`, `DetailedActivity`, `Lap`, `ActivityZone`, `TimedZoneDistribution`, `PhotosSummary`

#### [NEW] `strava_mcp/models/athlete.py`
`SummaryAthlete`, `DetailedAthlete`, `Zones`, `HeartRateZoneRanges`, `PowerZoneRanges`, `ZoneRange`

#### [NEW] `strava_mcp/models/segment.py`
`SummarySegment`, `DetailedSegment`, `DetailedSegmentEffort`, `ExplorerSegment`, `ExplorerResponse`

#### [NEW] `strava_mcp/models/filters.py`
`TimeRangePreset` enum: `TODAY`, `LAST_7_DAYS`, `LAST_14_DAYS`, `LAST_30_DAYS`, `LAST_3_MONTHS`, `LAST_6_MONTHS`, `LAST_1_YEAR`, `THIS_YEAR`, `CUSTOM`
`ActivityFilter`: preset + optional before/after timestamps + activity type + per_page

#### [NEW] `strava_mcp/models/responses.py`
`PerformanceTrendResponse`, `ActivitySummaryResponse`, `HRZoneAnalysisResponse`, `PowerAnalysisResponse`, `SegmentComparisonResponse`, `PersonalRecordsResponse`, `AggregatedStatsResponse`

---

### Component 3: FastAPI Application

#### [NEW] `strava_mcp/api/main.py`
- FastAPI app with `title="Strava MCP API"`, OpenAPI tags, lifespan context manager
- All routers included with prefixes

#### [NEW] `strava_mcp/api/routers/activities.py`
Key endpoints:
- `GET /activities` – list with full filter (preset: today/week/month/year/custom, activity type, pagination)
- `GET /activities/{id}` – detailed activity
- `GET /activities/{id}/laps` – laps
- `GET /activities/{id}/comments` – comments
- `GET /activities/{id}/kudoers` – kudoers  
- `GET /activities/{id}/zones` – activity HR/power zones
- `GET /activities/{id}/streams` – raw telemetry streams

#### [NEW] `strava_mcp/api/routers/analysis.py`
- `POST /analysis/summary` – aggregate stats for a time period
- `POST /analysis/performance-trend` – pace/speed over time
- `POST /analysis/hr-zones` – HR zone distribution
- `POST /analysis/personal-records` – PRs by activity type
- `POST /analysis/segment-comparison` – compare efforts on a segment
- `POST /analysis/cross-compare` – compare two date ranges
- `POST /analysis/weekly-breakdown` – week by week summary

---

### Component 4: MCP Server Tools

#### [NEW] `strava_mcp/mcp_server/server.py`
MCP server using `stdio` transport with all tools registered

#### [NEW] MCP Tools (all LLM-usable tools with JSON schema descriptions):

**Athlete Tools:**
- `get_my_profile` – get full authenticated athlete profile
- `get_my_zones` – get HR/power training zones
- `get_my_stats` – get lifetime activity stats

**Activity Tools (with rich filtering):**
- `get_activities` – params: `preset` (today/last_7_days/last_14_days/last_30_days/last_3_months/last_6_months/last_year/this_year/all_time), `after_date`, `before_date`, `activity_type`, `per_page`
- `get_activity_detail` – full detailed activity by ID
- `get_activity_laps` – lap data
- `get_activity_zones` – HR/power zones for activity
- `get_activity_streams` – raw sensor streams (GPS, HR, cadence, power, speed, altitude)

**Segment Tools:**
- `get_starred_segments` – starred segments list
- `get_segment` – segment detail by ID
- `get_segment_efforts` – efforts on a segment (filterable by date)
- `explore_segments` – find segments in a lat/lng bounding box

**Club Tools:**
- `get_my_clubs` – clubs athlete belongs to
- `get_club` – club details
- `get_club_activities` – recent club activities
- `get_club_members` – club membership list

**Route Tools:**
- `list_my_routes` – athlete's saved routes
- `get_route` – route detail

**Gear Tools:**
- `get_gear` – gear details by ID

**Analysis Tools:**
- `analyze_period_summary` – distance/elevation/time totals for any period
- `analyze_performance_trend` – show improvement/decline trends over time
- `analyze_hr_zones` – how much time spent in each HR zone
- `find_personal_records` – best times/distances by sport type
- `compare_segment_efforts` – compare all efforts on a segment
- `compare_periods` – compare two time periods side by side
- `analyze_weekly_breakdown` – week-over-week breakdown
- `get_activity_insights` – smart summary of a single activity

---

### Component 5: Supporting Files

#### [NEW] `.env.example`
```
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REFRESH_TOKEN=your_refresh_token
```

#### [NEW] `claude_desktop_config.json` (snippet)
```json
{
  "mcpServers": {
    "strava": {
      "command": "python",
      "args": ["-m", "strava_mcp.mcp_server.server"],
      "cwd": "c:\\Projects\\strava-mcp",
      "env": {}
    }
  }
}
```

#### [NEW] `requirements.txt`
```
mcp>=1.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
httpx>=0.27.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-dotenv>=1.0.0
python-dateutil>=2.9.0
```

#### [NEW] `scripts/get_refresh_token.py`
Interactive helper to obtain the OAuth refresh token via browser redirect.

---

## Verification Plan

### Step 1 – Install dependencies
```bash
cd c:\Projects\strava-mcp
pip install -r requirements.txt
```

### Step 2 – Configure environment
```bash
copy .env.example .env
# Edit .env with your STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, REFRESH_TOKEN
python scripts/get_refresh_token.py   # to obtain refresh token if needed
```

### Step 3 – Start FastAPI server
```bash
cd c:\Projects\strava-mcp
python -m uvicorn strava_mcp.api.main:app --reload --port 8000
```
Open http://localhost:8000/docs → Swagger UI must show all routes with Pydantic schemas.

### Step 4 – Test key API endpoints via Swagger
- `GET /athlete` → should return your athlete profile
- `GET /activities?preset=last_7_days` → should return last week's activities
- `POST /analysis/summary` with `{"preset": "last_30_days"}` → should return aggregate stats

### Step 5 – Test MCP server
```bash
cd c:\Projects\strava-mcp
python -m strava_mcp.mcp_server.server
```
Should start without errors (it waits for stdio input from MCP host).

### Step 6 – Claude Desktop integration
Add the MCP server config to Claude Desktop's config file and restart Claude Desktop. Then ask Claude:
- "What did I do on Strava this week?"
- "Show me my profile"
- "Compare my running this month vs last month"
