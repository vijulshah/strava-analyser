# Strava MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes your Strava data to **Claude Desktop** as a set of intelligent tools. Ask Claude natural-language questions about your training, and it will query the Strava API and run analysis for you in real time.

---

## Features

| Category | Tools |
|---|---|
| **Athlete** | Profile, HR/power zones, career stats |
| **Activities** | List (with time-range presets), detail, laps, zones, streams |
| **Segments** | Starred, explore by bounding box, efforts leaderboard |
| **Clubs** | List, detail, feed, members |
| **Routes** | List, detail |
| **Streams** | Raw GPS/HR/power/cadence data for activities & segments |
| **Analysis** | Period summary, performance trend, HR zones, power zones, personal records, segment comparison, period-over-period, weekly breakdown, activity insights |

### Time-range presets (all analysis tools)
`today` · `last_7_days` · `last_14_days` · `last_30_days` · `last_3_months` · `last_6_months` · `last_year` · `this_year` · `all_time` · `custom` (supply `after` / `before` Unix timestamps)

---

## Requirements

- Python 3.11+
- A Strava account
- [Claude Desktop](https://claude.ai/download)

---

## Installation

### 1 – Clone & install dependencies

```bash
git clone https://github.com/yourname/strava-mcp.git
cd strava-mcp
pip install -r requirements.txt
# or, using pyproject.toml:
pip install -e .
```

### 2 – Create your `.env` file

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and fill in your Strava app credentials (see below).

### 3 – Get a Strava API application

1. Go to <https://www.strava.com/settings/api>
2. Create an app (any name). Set "Authorization Callback Domain" to `localhost`.
3. Copy **Client ID** and **Client Secret** into `.env`.

### 4 – Obtain a refresh token

```bash
python scripts/get_refresh_token.py
```

Follow the prompts. The script will write `STRAVA_REFRESH_TOKEN` (and the initial access token) into `.env` automatically.

Required Strava OAuth scopes: `activity:read_all,read_all`

---

## Running the FastAPI server (optional)

The REST API with Swagger docs is useful for exploration and debugging:

```bash
uvicorn strava_mcp.api.main:app --reload --host 127.0.0.1 --port 8000
```

Open <http://localhost:8000/docs> in your browser.

---

## Claude Desktop integration

### 1 – Configure Claude Desktop

Locate your Claude Desktop config file:

| OS | Path |
|---|---|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

Add the `strava` block to the `mcpServers` section:

```json
{
  "mcpServers": {
    "strava": {
      "command": "python",
      "args": ["-m", "strava_mcp.mcp_server.server"],
      "cwd": "C:\\Projects\\strava-mcp"
    }
  }
}
```

> **Windows note**: Use double backslashes (`\\`) in the `cwd` value, or switch to forward slashes (`/`).

A ready-made snippet is available in [`claude_desktop_config.json`](claude_desktop_config.json) at the project root.

### 2 – Restart Claude Desktop

After saving the config, quit and relaunch Claude Desktop. You should see a 🔌 plug icon in the chat input area confirming the MCP server connected.

---

## Example Claude prompts

```
How many kilometres have I run in the last 30 days?
Show me my heart-rate zone distribution for all rides this year.
What's my average pace trend over the last 3 months of running?
Which of my starred segments have I improved on this year?
Compare my training volume from last month vs the month before.
What are my all-time personal records for running and cycling?
Give me a weekly breakdown of my training for the last 6 weeks.
```

---

## Project structure

```
strava_mcp/
├── config.py                  # pydantic-settings (reads .env)
├── client/
│   ├── auth.py                # OAuth2 token manager (auto-refresh)
│   └── base.py                # Async Strava HTTP client
├── models/
│   ├── activity.py            # Activity Pydantic models
│   ├── athlete.py             # Athlete / zone models
│   ├── segment.py             # Segment / effort models
│   ├── misc.py                # Stats, streams, gear, clubs, routes
│   ├── filters.py             # TimeRangePreset, ActivityFilter helpers
│   └── responses.py           # Analysis response models
├── analysis/
│   ├── aggregator.py          # Aggregate activity stats
│   ├── performance.py         # Linear trend regression
│   ├── heart_rate.py          # 5-zone HR analysis
│   ├── power.py               # 7-zone Coggan power analysis
│   ├── segment_analysis.py    # Segment comparison & PRs
│   └── cross_query.py         # Period comparison & weekly breakdown
├── api/
│   ├── main.py                # FastAPI application
│   ├── dependencies.py        # Shared get_client() dependency
│   ├── schemas/               # Request / query-param schemas
│   └── routers/               # One router per resource group
└── mcp_server/
    ├── server.py              # MCP entry point (stdio transport)
    └── tools/                 # One file of tools per resource group
scripts/
└── get_refresh_token.py       # Interactive OAuth2 token helper
docs/api/                      # Scraped Strava API reference
```

---

## Development

```bash
# Lint
ruff check .

# Type check
mypy strava_mcp

# Tests (add your own under tests/)
pytest
```

---

## Licence

MIT
