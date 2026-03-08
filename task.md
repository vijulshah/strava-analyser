# Strava MCP Project Tasks

## Phase 1: Research & API Documentation
- [x] Scrape Strava API reference from https://developers.strava.com/docs/reference
- [x] Analyze and categorize all API endpoints
- [x] Save API docs data to reference files (docs/api/*.md)

## Phase 2: Planning
- [x] Create implementation_plan.md
- [x] Scraper added to scripts/scrape_strava_docs.py

## Phase 3: Project Setup
- [ ] Create project structure at c:\Projects\strava-mcp
- [ ] Create pyproject.toml / requirements.txt with all dependencies
- [ ] Create configuration files (.env.example, config.py)

## Phase 4: Core Models (Pydantic)
- [ ] Athlete / Profile models
- [ ] Activity models (summary + detailed)
- [ ] Segment models
- [ ] Gear models
- [ ] Stats models
- [ ] Lap / Split models
- [ ] Club models
- [ ] Route models
- [ ] Filter / Query parameter models

## Phase 5: Strava API Client
- [ ] OAuth2 token management (access + refresh)
- [ ] Base HTTP client with auth headers
- [ ] Athlete endpoints client
- [ ] Activity endpoints client
- [ ] Segment endpoints client
- [ ] Club endpoints client
- [ ] Route endpoints client
- [ ] Gear endpoints client

## Phase 6: Analysis Functions
- [ ] Activity statistics aggregation (distance, time, elevation)
- [ ] Performance trend analysis (pace, speed over time)
- [ ] Heart rate zone analysis
- [ ] Segment performance comparison
- [ ] Weekly/monthly/yearly summaries
- [ ] Personal records detection
- [ ] Cross-activity comparisons

## Phase 7: FastAPI Application
- [ ] Main app with lifespan events
- [ ] Router structure (athletes, activities, segments, clubs, analysis)
- [ ] Filter endpoints with all time range options
- [ ] Pydantic request/response schemas for all endpoints
- [ ] Swagger/OpenAPI enriched documentation
- [ ] Error handling middleware

## Phase 8: MCP Server
- [ ] MCP server setup using mcp Python SDK
- [ ] Tool definitions for all MCP capabilities
- [ ] Activity filter tools (today, 1 week, 2 weeks, 1 month, 1 year, custom range)
- [ ] Profile tools
- [ ] Detailed activity analysis tools
- [ ] Analysis / cross-query tools
- [ ] Claude Desktop config snippet

## Phase 9: Verification
- [ ] Test FastAPI endpoints via Swagger UI
- [ ] Test MCP server with Claude Desktop
- [ ] Validate all Pydantic models
- [ ] Check filter functionality
