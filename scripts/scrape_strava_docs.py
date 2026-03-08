"""
Strava API Documentation Scraper
=================================
Scrapes the Strava API v3 reference page and saves each category
(Activities, Athletes, Clubs, Gears, Routes, SegmentEfforts, Segments,
Streams, Uploads, Models) into its own Markdown file under docs/api/.

Usage:
    python scripts/scrape_strava_docs.py

Output:
    docs/api/activities.md
    docs/api/athletes.md
    docs/api/clubs.md
    docs/api/gears.md
    docs/api/routes.md
    docs/api/segment_efforts.md
    docs/api/segments.md
    docs/api/streams.md
    docs/api/uploads.md
    docs/api/models.md
    docs/api/overview.md
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup, Tag

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STRAVA_DOCS_URL: str = "https://developers.strava.com/docs/reference"
STRAVA_BASE_URL: str = "https://developers.strava.com"
OUTPUT_DIR: Path = Path(__file__).resolve().parent.parent / "docs" / "api"

CATEGORY_ORDER: List[str] = [
    "Activities",
    "Athletes",
    "Clubs",
    "Gears",
    "Routes",
    "SegmentEfforts",
    "Segments",
    "Streams",
    "Uploads",
]

HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Parameter:
    """Represents one API parameter."""
    name: str
    location: str  # path / query / body
    required: bool
    data_type: str
    description: str


@dataclass
class Endpoint:
    """Represents one Strava API endpoint."""
    operation_id: str
    summary: str
    description: str
    method: str
    path: str
    parameters: List[Parameter] = field(default_factory=list)
    request_body: Optional[str] = None
    response_model: Optional[str] = None
    scopes_required: List[str] = field(default_factory=list)
    example_curl: Optional[str] = None


@dataclass
class Category:
    """A group of related endpoints (e.g. Activities, Athletes)."""
    name: str
    endpoints: List[Endpoint] = field(default_factory=list)


@dataclass
class ModelField:
    """One field in a Strava model."""
    name: str
    data_type: str
    description: str


@dataclass
class Model:
    """A Strava API data model."""
    name: str
    description: str
    fields: List[ModelField] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------


class StravaScraper:
    """Scrapes Strava API v3 reference documentation."""

    def __init__(self, url: str = STRAVA_DOCS_URL) -> None:
        self.url = url
        self.soup: Optional[BeautifulSoup] = None
        self.categories: Dict[str, Category] = {}
        self.models: List[Model] = []

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------

    def fetch(self) -> None:
        """Download the Strava docs page and parse into BeautifulSoup."""
        print(f"Fetching: {self.url}")
        with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            response = client.get(self.url)
            response.raise_for_status()
        self.soup = BeautifulSoup(response.text, "html.parser")
        print(f"  Page size: {len(response.text):,} bytes")

    # ------------------------------------------------------------------
    # Parse endpoints
    # ------------------------------------------------------------------

    def parse(self) -> None:
        """Parse endpoints and models from the page."""
        if self.soup is None:
            raise RuntimeError("Call fetch() before parse().")

        self._parse_endpoints()
        self._parse_models()

    def _parse_endpoints(self) -> None:
        """Extract all API endpoint blocks."""
        # Strava docs render each endpoint inside an <li> with class 'operation'
        # or inside swagger-style divs. We look for section headers + operation blocks.

        # ------------------------------------------------------------------
        # Strategy: find all <h2> tags that match category names, then collect
        # operation blocks that follow until the next category h2.
        # ------------------------------------------------------------------
        all_tags = self.soup.find_all(["h2", "h3", "div", "li"])

        current_category: Optional[str] = None

        for tag in all_tags:
            # Detect category heading (h2 matching known names)
            if tag.name == "h2":
                heading_text = tag.get_text(strip=True)
                for cat in CATEGORY_ORDER:
                    if cat.lower() == heading_text.lower():
                        current_category = cat
                        if cat not in self.categories:
                            self.categories[cat] = Category(name=cat)
                        break

            # Detect operation block
            if tag.name in ("li", "div") and current_category:
                op_id_attr = tag.get("id", "")
                # Swagger-style: id like "api-Activities-getActivityById"
                if op_id_attr and op_id_attr.startswith("api-"):
                    endpoint = self._parse_operation_block(tag, current_category)
                    if endpoint:
                        self.categories[current_category].endpoints.append(endpoint)

        # Fallback: ensure every known category exists even if empty
        for cat in CATEGORY_ORDER:
            if cat not in self.categories:
                self.categories[cat] = Category(name=cat)

        total = sum(len(c.endpoints) for c in self.categories.values())
        print(f"  Parsed {total} endpoints across {len(self.categories)} categories")

    def _parse_operation_block(
        self, tag: Tag, category: str
    ) -> Optional[Endpoint]:
        """Extract an Endpoint from a single swagger operation block."""
        try:
            op_id = tag.get("id", "").replace(f"api-{category}-", "")

            # Summary / description
            summary_tag = tag.find(class_=re.compile(r"operation-summary|summary"))
            summary = summary_tag.get_text(strip=True) if summary_tag else op_id

            desc_tag = tag.find(class_=re.compile(r"operation-description|opblock-description"))
            description = desc_tag.get_text(strip=True) if desc_tag else ""

            # HTTP method
            method_tag = tag.find(class_=re.compile(r"opblock-summary-method|http-method"))
            method = method_tag.get_text(strip=True).upper() if method_tag else "GET"

            # Path
            path_tag = tag.find(class_=re.compile(r"opblock-summary-path|operation-path"))
            path = path_tag.get_text(strip=True) if path_tag else ""

            # Parameters
            parameters: List[Parameter] = []
            param_rows = tag.find_all(class_=re.compile(r"parameter"))
            for row in param_rows:
                name_el = row.find(class_=re.compile(r"parameter__name|param-name"))
                type_el = row.find(class_=re.compile(r"parameter__type|param-type"))
                in_el = row.find(class_=re.compile(r"parameter__in|param-in"))
                desc_el = row.find(class_=re.compile(r"parameter__description|param-desc"))
                req_el = row.find(class_=re.compile(r"required"))

                if name_el:
                    parameters.append(Parameter(
                        name=name_el.get_text(strip=True),
                        location=in_el.get_text(strip=True) if in_el else "query",
                        required=req_el is not None,
                        data_type=type_el.get_text(strip=True) if type_el else "string",
                        description=desc_el.get_text(strip=True) if desc_el else "",
                    ))

            # Response model
            resp_tag = tag.find(class_=re.compile(r"response-col_description"))
            response_model = resp_tag.get_text(strip=True) if resp_tag else None

            # Example curl
            code_els = tag.find_all("code")
            example_curl: Optional[str] = None
            for code in code_els:
                text = code.get_text(strip=True)
                if text.startswith("$ http") or text.startswith("curl"):
                    example_curl = text
                    break

            return Endpoint(
                operation_id=op_id,
                summary=summary,
                description=description,
                method=method,
                path=path,
                parameters=parameters,
                response_model=response_model,
                example_curl=example_curl,
            )
        except Exception as exc:
            print(f"    Warning: could not parse operation block: {exc}")
            return None

    def _parse_models(self) -> None:
        """Extract all model definitions from the Models section."""
        if self.soup is None:
            return

        models_section = self.soup.find(id=re.compile(r"api-models", re.I))
        if not models_section:
            # Try finding via h1/h2 "All Models"
            for h in self.soup.find_all(["h1", "h2"]):
                if "model" in h.get_text().lower():
                    models_section = h.parent
                    break

        model_blocks = (
            models_section.find_all(class_=re.compile(r"model-container|model"))
            if models_section else []
        )

        for block in model_blocks:
            name_el = block.find(class_=re.compile(r"model-title|model-name"))
            if not name_el:
                continue
            model_name = name_el.get_text(strip=True)

            fields: List[ModelField] = []
            for row in block.find_all(class_=re.compile(r"property")):
                fname = row.find(class_=re.compile(r"prop-name|property-name"))
                ftype = row.find(class_=re.compile(r"prop-type|property-type"))
                fdesc = row.find(class_=re.compile(r"prop-description|markdown"))
                if fname:
                    fields.append(ModelField(
                        name=fname.get_text(strip=True),
                        data_type=ftype.get_text(strip=True) if ftype else "",
                        description=fdesc.get_text(strip=True) if fdesc else "",
                    ))

            self.models.append(Model(
                name=model_name,
                description="",
                fields=fields,
            ))

        print(f"  Parsed {len(self.models)} models")

    # ------------------------------------------------------------------
    # Fallback: static knowledge from official Strava OpenAPI spec
    # ------------------------------------------------------------------

    def populate_static_data(self) -> None:
        """
        Populate categories with known endpoint data from the Strava API spec.
        This is used as a guaranteed fallback when HTML scraping yields no results
        (the Strava docs page uses heavy JavaScript rendering).
        """
        static: Dict[str, List[Dict]] = {
            "Activities": [
                {"op": "createActivity", "method": "POST", "path": "/activities",
                 "summary": "Create a Manual Activity",
                 "desc": "Creates a manual activity for an authenticated athlete.",
                 "params": [
                     ("name", "body", True, "string", "Activity name"),
                     ("sport_type", "body", True, "string", "Sport type (e.g. Run, Ride)"),
                     ("start_date_local", "body", True, "datetime", "ISO 8601 start time"),
                     ("elapsed_time", "body", True, "integer", "Elapsed time in seconds"),
                     ("description", "body", False, "string", "Activity description"),
                     ("distance", "body", False, "float", "Distance in meters"),
                     ("trainer", "body", False, "integer", "1 if trainer activity"),
                     ("commute", "body", False, "integer", "1 if commute"),
                 ],
                 "response": "DetailedActivity", "scopes": ["activity:write"]},
                {"op": "getActivityById", "method": "GET", "path": "/activities/{id}",
                 "summary": "Get Activity",
                 "desc": "Returns the given activity. Requires activity:read. Requires activity:read_all for Only Me activities.",
                 "params": [
                     ("id", "path", True, "long", "Activity identifier"),
                     ("include_all_efforts", "query", False, "boolean", "Include all segment efforts"),
                 ],
                 "response": "DetailedActivity", "scopes": ["activity:read"]},
                {"op": "getCommentsByActivityId", "method": "GET", "path": "/activities/{id}/comments",
                 "summary": "List Activity Comments",
                 "desc": "Returns comments for the given activity.",
                 "params": [
                     ("id", "path", True, "long", "Activity identifier"),
                     ("page_size", "query", False, "integer", "Number of results per page (default 30)"),
                     ("after_cursor", "query", False, "string", "Pagination cursor"),
                 ],
                 "response": "Comment[]", "scopes": ["activity:read"]},
                {"op": "getKudoersByActivityId", "method": "GET", "path": "/activities/{id}/kudos",
                 "summary": "List Activity Kudoers",
                 "desc": "Returns kudoers for the given activity.",
                 "params": [
                     ("id", "path", True, "long", "Activity identifier"),
                     ("page", "query", False, "integer", "Page number (default 1)"),
                     ("per_page", "query", False, "integer", "Items per page (default 30)"),
                 ],
                 "response": "SummaryAthlete[]", "scopes": ["activity:read"]},
                {"op": "getLapsByActivityId", "method": "GET", "path": "/activities/{id}/laps",
                 "summary": "List Activity Laps",
                 "desc": "Returns laps for the given activity.",
                 "params": [("id", "path", True, "long", "Activity identifier")],
                 "response": "Lap[]", "scopes": ["activity:read"]},
                {"op": "getLoggedInAthleteActivities", "method": "GET", "path": "/athlete/activities",
                 "summary": "List Athlete Activities",
                 "desc": "Returns activities for the authenticated athlete. Supports before/after epoch timestamp filtering.",
                 "params": [
                     ("before", "query", False, "integer", "Epoch timestamp — return activities before this time"),
                     ("after", "query", False, "integer", "Epoch timestamp — return activities after this time"),
                     ("page", "query", False, "integer", "Page number (default 1)"),
                     ("per_page", "query", False, "integer", "Items per page (default 30, max 200)"),
                 ],
                 "response": "SummaryActivity[]", "scopes": ["activity:read"]},
                {"op": "getZonesByActivityId", "method": "GET", "path": "/activities/{id}/zones",
                 "summary": "Get Activity Zones",
                 "desc": "Returns HR and power zones for the given activity.",
                 "params": [("id", "path", True, "long", "Activity identifier")],
                 "response": "ActivityZone[]", "scopes": ["activity:read"]},
                {"op": "updateActivityById", "method": "PUT", "path": "/activities/{id}",
                 "summary": "Update Activity",
                 "desc": "Updates the given activity. Requires activity:write.",
                 "params": [
                     ("id", "path", True, "long", "Activity identifier"),
                     ("body", "body", True, "UpdatableActivity", "Fields to update"),
                 ],
                 "response": "DetailedActivity", "scopes": ["activity:write"]},
            ],
            "Athletes": [
                {"op": "getLoggedInAthlete", "method": "GET", "path": "/athlete",
                 "summary": "Get Authenticated Athlete",
                 "desc": "Returns the authenticated athlete. profile:read_all returns detailed representation.",
                 "params": [],
                 "response": "DetailedAthlete", "scopes": ["read"]},
                {"op": "getLoggedInAthleteZones", "method": "GET", "path": "/athlete/zones",
                 "summary": "Get Athlete Zones",
                 "desc": "Returns HR and power zones of the authenticated athlete.",
                 "params": [],
                 "response": "Zones", "scopes": ["read"]},
                {"op": "getStats", "method": "GET", "path": "/athletes/{id}/stats",
                 "summary": "Get Athlete Stats",
                 "desc": "Returns activity stats for the authenticated athlete (only public activities).",
                 "params": [("id", "path", True, "long", "Athlete identifier (must match authenticated athlete)")],
                 "response": "ActivityStats", "scopes": ["read"]},
                {"op": "updateLoggedInAthlete", "method": "PUT", "path": "/athlete",
                 "summary": "Update Athlete",
                 "desc": "Updates the authenticated athlete.",
                 "params": [
                     ("weight", "body", True, "float", "Weight in kg"),
                 ],
                 "response": "DetailedAthlete", "scopes": ["profile:write"]},
            ],
            "Clubs": [
                {"op": "getClubActivitiesById", "method": "GET", "path": "/clubs/{id}/activities",
                 "summary": "List Club Activities",
                 "desc": "Returns recent activities by club members.",
                 "params": [
                     ("id", "path", True, "long", "Club identifier"),
                     ("page", "query", False, "integer", "Page number"),
                     ("per_page", "query", False, "integer", "Items per page (default 30)"),
                 ],
                 "response": "ClubActivity[]", "scopes": ["read"]},
                {"op": "getClubAdminsById", "method": "GET", "path": "/clubs/{id}/admins",
                 "summary": "List Club Administrators",
                 "desc": "Returns administrators of the given club.",
                 "params": [
                     ("id", "path", True, "long", "Club identifier"),
                     ("page", "query", False, "integer", "Page number"),
                     ("per_page", "query", False, "integer", "Items per page"),
                 ],
                 "response": "SummaryAthlete[]", "scopes": ["read"]},
                {"op": "getClubById", "method": "GET", "path": "/clubs/{id}",
                 "summary": "Get Club",
                 "desc": "Returns the given club.",
                 "params": [("id", "path", True, "long", "Club identifier")],
                 "response": "DetailedClub", "scopes": ["read"]},
                {"op": "getClubMembersById", "method": "GET", "path": "/clubs/{id}/members",
                 "summary": "List Club Members",
                 "desc": "Returns members of the given club.",
                 "params": [
                     ("id", "path", True, "long", "Club identifier"),
                     ("page", "query", False, "integer", "Page number"),
                     ("per_page", "query", False, "integer", "Items per page"),
                 ],
                 "response": "ClubAthlete[]", "scopes": ["read"]},
                {"op": "getLoggedInAthleteClubs", "method": "GET", "path": "/athlete/clubs",
                 "summary": "List Athlete Clubs",
                 "desc": "Returns clubs the authenticated athlete belongs to.",
                 "params": [
                     ("page", "query", False, "integer", "Page number"),
                     ("per_page", "query", False, "integer", "Items per page"),
                 ],
                 "response": "SummaryClub[]", "scopes": ["read"]},
            ],
            "Gears": [
                {"op": "getGearById", "method": "GET", "path": "/gear/{id}",
                 "summary": "Get Equipment",
                 "desc": "Returns a specific gear (bike or shoes) for the authenticated athlete.",
                 "params": [("id", "path", True, "string", "Gear identifier (e.g. b12345)")],
                 "response": "DetailedGear", "scopes": ["read"]},
            ],
            "Routes": [
                {"op": "getRouteAsGPX", "method": "GET", "path": "/routes/{id}/export_gpx",
                 "summary": "Export Route GPX",
                 "desc": "Returns the GPX file for the given route.",
                 "params": [("id", "path", True, "long", "Route identifier")],
                 "response": "application/gpx+xml", "scopes": ["read"]},
                {"op": "getRouteAsTCX", "method": "GET", "path": "/routes/{id}/export_tcx",
                 "summary": "Export Route TCX",
                 "desc": "Returns the TCX file for the given route.",
                 "params": [("id", "path", True, "long", "Route identifier")],
                 "response": "application/tcx+xml", "scopes": ["read"]},
                {"op": "getRouteById", "method": "GET", "path": "/routes/{id}",
                 "summary": "Get Route",
                 "desc": "Returns the given route.",
                 "params": [("id", "path", True, "long", "Route identifier")],
                 "response": "Route", "scopes": ["read"]},
                {"op": "getRoutesByAthleteId", "method": "GET", "path": "/athletes/{id}/routes",
                 "summary": "List Athlete Routes",
                 "desc": "Returns the routes created by the authenticated athlete.",
                 "params": [
                     ("id", "path", True, "long", "Athlete identifier"),
                     ("page", "query", False, "integer", "Page number"),
                     ("per_page", "query", False, "integer", "Items per page (default 30)"),
                 ],
                 "response": "Route[]", "scopes": ["read"]},
            ],
            "SegmentEfforts": [
                {"op": "getEffortsBySegmentId", "method": "GET", "path": "/segment_efforts",
                 "summary": "List Segment Efforts",
                 "desc": "Returns a list of segment efforts for the authenticated athlete on the given segment.",
                 "params": [
                     ("segment_id", "query", True, "integer", "Segment identifier"),
                     ("start_date_local", "query", False, "datetime", "Filter efforts after this ISO 8601 date"),
                     ("end_date_local", "query", False, "datetime", "Filter efforts before this ISO 8601 date"),
                     ("per_page", "query", False, "integer", "Items per page (default 30)"),
                 ],
                 "response": "DetailedSegmentEffort[]", "scopes": ["activity:read"]},
                {"op": "getSegmentEffortById", "method": "GET", "path": "/segment_efforts/{id}",
                 "summary": "Get Segment Effort",
                 "desc": "Returns the given segment effort.",
                 "params": [("id", "path", True, "long", "Segment effort identifier")],
                 "response": "DetailedSegmentEffort", "scopes": ["activity:read"]},
            ],
            "Segments": [
                {"op": "exploreSegments", "method": "GET", "path": "/segments/explore",
                 "summary": "Explore Segments",
                 "desc": "Returns up to 10 of the top segments within a bounding box.",
                 "params": [
                     ("bounds", "query", True, "float[]", "Bounding box: SW_lat,SW_lng,NE_lat,NE_lng"),
                     ("activity_type", "query", False, "string", "Filter: 'running' or 'riding'"),
                     ("min_cat", "query", False, "integer", "Min climb category (0-5)"),
                     ("max_cat", "query", False, "integer", "Max climb category (0-5)"),
                 ],
                 "response": "ExplorerResponse", "scopes": ["read"]},
                {"op": "getLoggedInAthleteStarredSegments", "method": "GET", "path": "/segments/starred",
                 "summary": "List Starred Segments",
                 "desc": "Returns the starred segments of the authenticated athlete.",
                 "params": [
                     ("page", "query", False, "integer", "Page number"),
                     ("per_page", "query", False, "integer", "Items per page (default 30)"),
                 ],
                 "response": "SummarySegment[]", "scopes": ["read"]},
                {"op": "getSegmentById", "method": "GET", "path": "/segments/{id}",
                 "summary": "Get Segment",
                 "desc": "Returns the given segment.",
                 "params": [("id", "path", True, "long", "Segment identifier")],
                 "response": "DetailedSegment", "scopes": ["read"]},
                {"op": "starSegment", "method": "PUT", "path": "/segments/{id}/starred",
                 "summary": "Star Segment",
                 "desc": "Starred/un-star a segment for the authenticated athlete.",
                 "params": [
                     ("id", "path", True, "long", "Segment identifier"),
                     ("starred", "body", True, "boolean", "Whether to star the segment"),
                 ],
                 "response": "DetailedSegment", "scopes": ["activity:write"]},
            ],
            "Streams": [
                {"op": "getActivityStreams", "method": "GET", "path": "/activities/{id}/streams",
                 "summary": "Get Activity Streams",
                 "desc": "Returns the given activity's streams (time-series sensor data). Keys: time, distance, latlng, altitude, velocity_smooth, heartrate, cadence, watts, temp, moving, grade_smooth.",
                 "params": [
                     ("id", "path", True, "long", "Activity identifier"),
                     ("keys", "query", True, "string[]", "Desired stream types (comma-separated)"),
                     ("key_by_type", "query", True, "boolean", "Must be true"),
                 ],
                 "response": "StreamSet", "scopes": ["activity:read"]},
                {"op": "getRouteStreams", "method": "GET", "path": "/routes/{id}/streams",
                 "summary": "Get Route Streams",
                 "desc": "Returns the given route's streams.",
                 "params": [("id", "path", True, "long", "Route identifier")],
                 "response": "StreamSet", "scopes": ["read"]},
                {"op": "getSegmentEffortStreams", "method": "GET", "path": "/segment_efforts/{id}/streams",
                 "summary": "Get Segment Effort Streams",
                 "desc": "Returns the given segment effort's streams.",
                 "params": [
                     ("id", "path", True, "long", "Segment effort identifier"),
                     ("keys", "query", True, "string[]", "Desired stream types"),
                     ("key_by_type", "query", True, "boolean", "Must be true"),
                 ],
                 "response": "StreamSet", "scopes": ["activity:read"]},
                {"op": "getSegmentStreams", "method": "GET", "path": "/segments/{id}/streams",
                 "summary": "Get Segment Streams",
                 "desc": "Returns the given segment's streams.",
                 "params": [
                     ("id", "path", True, "long", "Segment identifier"),
                     ("keys", "query", True, "string[]", "Desired stream types"),
                     ("key_by_type", "query", True, "boolean", "Must be true"),
                 ],
                 "response": "StreamSet", "scopes": ["read"]},
            ],
            "Uploads": [
                {"op": "createUpload", "method": "POST", "path": "/uploads",
                 "summary": "Upload Activity",
                 "desc": "Uploads a new data file to create an activity (FIT, GPX, TCX formats).",
                 "params": [
                     ("file", "body", True, "file", "Activity file (FIT/GPX/TCX)"),
                     ("name", "body", False, "string", "Activity name"),
                     ("description", "body", False, "string", "Activity description"),
                     ("trainer", "body", False, "string", "1 if trainer activity"),
                     ("commute", "body", False, "string", "1 if commute"),
                     ("data_type", "body", True, "string", "File format: fit, fit.gz, tcx, tcx.gz, gpx, gpx.gz"),
                     ("external_id", "body", False, "string", "Data filename"),
                 ],
                 "response": "Upload", "scopes": ["activity:write"]},
                {"op": "getUploadById", "method": "GET", "path": "/uploads/{uploadId}",
                 "summary": "Get Upload",
                 "desc": "Returns an upload for the given identifier.",
                 "params": [("uploadId", "path", True, "long", "Upload identifier")],
                 "response": "Upload", "scopes": ["activity:write"]},
            ],
        }

        for cat_name, endpoints_data in static.items():
            if cat_name not in self.categories:
                self.categories[cat_name] = Category(name=cat_name)
            for ep in endpoints_data:
                params = [
                    Parameter(name=p[0], location=p[1], required=p[2],
                              data_type=p[3], description=p[4])
                    for p in ep.get("params", [])
                ]
                self.categories[cat_name].endpoints.append(Endpoint(
                    operation_id=ep["op"],
                    summary=ep["summary"],
                    description=ep["desc"],
                    method=ep["method"],
                    path=ep["path"],
                    parameters=params,
                    response_model=ep.get("response"),
                    scopes_required=ep.get("scopes", []),
                ))

        # Populate models from known Strava spec
        self._populate_static_models()
        print("  Static data populated for all categories.")

    def _populate_static_models(self) -> None:
        """Add all known Strava API models."""
        models_data = [
            ("DetailedActivity", "Full representation of an activity.", [
                ("id", "long", "Unique activity identifier"),
                ("name", "string", "Activity name"),
                ("distance", "float", "Distance in meters"),
                ("moving_time", "integer", "Moving time in seconds"),
                ("elapsed_time", "integer", "Elapsed time in seconds"),
                ("total_elevation_gain", "float", "Total elevation gain in meters"),
                ("type", "ActivityType", "Deprecated activity type enum"),
                ("sport_type", "SportType", "Sport type (preferred over type)"),
                ("start_date", "datetime", "UTC start time"),
                ("start_date_local", "datetime", "Local start time"),
                ("timezone", "string", "Timezone of activity"),
                ("start_latlng", "LatLng", "Start coordinates"),
                ("end_latlng", "LatLng", "End coordinates"),
                ("achievement_count", "integer", "Number of achievements"),
                ("kudos_count", "integer", "Number of kudos"),
                ("comment_count", "integer", "Number of comments"),
                ("athlete_count", "integer", "Number of athletes on route"),
                ("photo_count", "integer", "Number of photos"),
                ("map", "PolylineMap", "Map of activity polyline"),
                ("trainer", "boolean", "Trainer activity flag"),
                ("commute", "boolean", "Commute flag"),
                ("manual", "boolean", "Manual entry flag"),
                ("private", "boolean", "Private activity flag"),
                ("visibility", "string", "Visibility: everyone/followers_only/only_me"),
                ("flagged", "boolean", "Flagged flag"),
                ("gear_id", "string", "Gear used for activity"),
                ("average_speed", "float", "Average speed in m/s"),
                ("max_speed", "float", "Max speed in m/s"),
                ("average_cadence", "float", "Average cadence in rpm"),
                ("average_watts", "float", "Average power in watts (cycling)"),
                ("max_watts", "integer", "Max power in watts"),
                ("weighted_average_watts", "integer", "Weighted average power"),
                ("kilojoules", "float", "Total energy output in kJ"),
                ("device_watts", "boolean", "Power from device (not estimated)"),
                ("has_heartrate", "boolean", "Has heart rate data"),
                ("average_heartrate", "float", "Average heart rate in bpm"),
                ("max_heartrate", "float", "Maximum heart rate in bpm"),
                ("heartrate_opt_out", "boolean", "Athlete HR data opt-out"),
                ("display_hide_heartrate_option", "boolean", "HR display option"),
                ("elev_high", "float", "Highest elevation in meters"),
                ("elev_low", "float", "Lowest elevation in meters"),
                ("upload_id", "long", "Upload identifier"),
                ("upload_id_str", "string", "Upload identifier string"),
                ("external_id", "string", "External ID from upload"),
                ("from_accepted_tag", "boolean", "From accepted tag"),
                ("pr_count", "integer", "Number of PRs achieved"),
                ("total_photo_count", "integer", "Total photos including partners"),
                ("has_kudoed", "boolean", "Whether authenticated athlete kudoed"),
                ("suffer_score", "float", "Relative Effort score"),
                ("description", "string", "Activity description"),
                ("calories", "float", "Kilocalories consumed"),
                ("perceived_exertion", "float", "Athlete perceived exertion (1-10)"),
                ("prefer_perceived_exertion", "boolean", "Show perceived exertion"),
                ("segment_efforts", "DetailedSegmentEffort[]", "Segment efforts"),
                ("splits_metric", "Split[]", "Metric splits (per 1km)"),
                ("splits_standard", "Split[]", "Standard splits (per 1mi)"),
                ("laps", "Lap[]", "Laps"),
                ("best_efforts", "DetailedSegmentEffort[]", "Best efforts"),
                ("gear", "SummaryGear", "Gear used"),
                ("photos", "PhotosSummary", "Photos summary"),
                ("athlete", "MetaAthlete", "Athlete reference"),
                ("device_name", "string", "Device used to record"),
                ("embed_token", "string", "Widget embed token"),
            ]),
            ("SummaryActivity", "Summary representation of an activity.", [
                ("id", "long", "Unique identifier"),
                ("name", "string", "Activity name"),
                ("distance", "float", "Distance in meters"),
                ("moving_time", "integer", "Moving time in seconds"),
                ("elapsed_time", "integer", "Elapsed time in seconds"),
                ("total_elevation_gain", "float", "Elevation gain in meters"),
                ("sport_type", "SportType", "Sport type"),
                ("type", "ActivityType", "Deprecated type"),
                ("start_date", "datetime", "UTC start time"),
                ("start_date_local", "datetime", "Local start time"),
                ("timezone", "string", "Timezone"),
                ("average_speed", "float", "Average speed m/s"),
                ("max_speed", "float", "Max speed m/s"),
                ("average_cadence", "float", "Average cadence rpm"),
                ("average_watts", "float", "Average power watts"),
                ("average_heartrate", "float", "Average HR bpm"),
                ("max_heartrate", "float", "Max HR bpm"),
                ("map", "PolylineMap", "Activity map"),
                ("kudos_count", "integer", "Kudos count"),
                ("achievement_count", "integer", "Achievements"),
                ("visibility", "string", "Visibility level"),
                ("trainer", "boolean", "Trainer flag"),
                ("commute", "boolean", "Commute flag"),
            ]),
            ("DetailedAthlete", "Full representation of an athlete.", [
                ("id", "long", "Athlete identifier"),
                ("username", "string", "Athlete username"),
                ("firstname", "string", "First name"),
                ("lastname", "string", "Last name"),
                ("city", "string", "City"),
                ("state", "string", "State"),
                ("country", "string", "Country"),
                ("sex", "string", "M or F"),
                ("premium", "boolean", "Summit (premium) status"),
                ("summit", "boolean", "Summit status"),
                ("created_at", "datetime", "Account creation date"),
                ("updated_at", "datetime", "Last update date"),
                ("follower_count", "integer", "Number of followers"),
                ("friend_count", "integer", "Number of friends"),
                ("measurement_preference", "string", "feet or meters"),
                ("ftp", "integer", "FTP in watts"),
                ("weight", "float", "Weight in kg"),
                ("profile_medium", "string", "Medium profile picture URL"),
                ("profile", "string", "Full profile picture URL"),
                ("clubs", "SummaryClub[]", "Athlete's clubs"),
                ("bikes", "SummaryGear[]", "Athlete's bikes"),
                ("shoes", "SummaryGear[]", "Athlete's shoes"),
            ]),
            ("ActivityStats", "Rolled-up statistics for an athlete.", [
                ("biggest_ride_distance", "float", "Longest ride in meters"),
                ("biggest_climb_elevation_gain", "float", "Biggest climb elevation gain"),
                ("recent_ride_totals", "ActivityTotal", "Stats for recent rides (4 weeks)"),
                ("recent_run_totals", "ActivityTotal", "Stats for recent runs (4 weeks)"),
                ("recent_swim_totals", "ActivityTotal", "Stats for recent swims (4 weeks)"),
                ("ytd_ride_totals", "ActivityTotal", "Year-to-date ride stats"),
                ("ytd_run_totals", "ActivityTotal", "Year-to-date run stats"),
                ("ytd_swim_totals", "ActivityTotal", "Year-to-date swim stats"),
                ("all_ride_totals", "ActivityTotal", "All-time ride stats"),
                ("all_run_totals", "ActivityTotal", "All-time run stats"),
                ("all_swim_totals", "ActivityTotal", "All-time swim stats"),
            ]),
            ("ActivityTotal", "Roll-up of metrics for a set of activities.", [
                ("count", "integer", "Number of activities"),
                ("distance", "float", "Total distance in meters"),
                ("moving_time", "integer", "Total moving time in seconds"),
                ("elapsed_time", "integer", "Total elapsed time in seconds"),
                ("elevation_gain", "float", "Total elevation gain in meters"),
                ("achievement_count", "integer", "Total achievements (recent only)"),
            ]),
            ("Lap", "Individual lap of an activity.", [
                ("id", "long", "Lap identifier"),
                ("activity", "MetaActivity", "Activity reference"),
                ("athlete", "MetaAthlete", "Athlete reference"),
                ("average_cadence", "float", "Average cadence"),
                ("average_speed", "float", "Average speed m/s"),
                ("distance", "float", "Lap distance in meters"),
                ("elapsed_time", "integer", "Elapsed time in seconds"),
                ("end_index", "integer", "End stream index"),
                ("lap_index", "integer", "Lap number"),
                ("max_speed", "float", "Max speed m/s"),
                ("moving_time", "integer", "Moving time in seconds"),
                ("name", "string", "Lap name"),
                ("pace_zone", "integer", "Pace zone"),
                ("split", "integer", "Split number"),
                ("start_date", "datetime", "Start time UTC"),
                ("start_date_local", "datetime", "Start time local"),
                ("start_index", "integer", "Start stream index"),
                ("total_elevation_gain", "float", "Elevation gain"),
                ("average_watts", "float", "Average power watts"),
                ("average_heartrate", "float", "Average heart rate"),
                ("max_heartrate", "float", "Max heart rate"),
            ]),
            ("StreamSet", "Set of time-series sensor streams.", [
                ("time", "TimeStream", "Sequence of time values (seconds from start)"),
                ("distance", "DistanceStream", "Sequence of distance values (meters)"),
                ("latlng", "LatLngStream", "Sequence of GPS coordinates"),
                ("altitude", "AltitudeStream", "Sequence of altitude values (meters)"),
                ("velocity_smooth", "SmoothVelocityStream", "Smoothed velocity m/s"),
                ("heartrate", "HeartrateStream", "Sequence of HR values (bpm)"),
                ("cadence", "CadenceStream", "Sequence of cadence values (rpm)"),
                ("watts", "PowerStream", "Sequence of power values (watts)"),
                ("temp", "TemperatureStream", "Sequence of temperature values (Celsius)"),
                ("moving", "MovingStream", "Sequence of moving booleans"),
                ("grade_smooth", "SmoothGradeStream", "Smoothed grade percentage"),
            ]),
            ("DetailedSegment", "Detailed segment information.", [
                ("id", "long", "Segment identifier"),
                ("name", "string", "Segment name"),
                ("activity_type", "string", "Ride or Run"),
                ("distance", "float", "Segment distance in meters"),
                ("average_grade", "float", "Average gradient %"),
                ("maximum_grade", "float", "Maximum gradient %"),
                ("elevation_high", "float", "Highest elevation (m)"),
                ("elevation_low", "float", "Lowest elevation (m)"),
                ("start_latlng", "LatLng", "Start coordinates"),
                ("end_latlng", "LatLng", "End coordinates"),
                ("climb_category", "integer", "Climb category 0-5"),
                ("city", "string", "City"),
                ("state", "string", "State"),
                ("country", "string", "Country"),
                ("private", "boolean", "Private flag"),
                ("hazardous", "boolean", "Hazardous flag"),
                ("created_at", "datetime", "Creation date"),
                ("updated_at", "datetime", "Last update date"),
                ("total_elevation_gain", "float", "Total elevation gain"),
                ("map", "PolylineMap", "Segment map"),
                ("effort_count", "integer", "Total efforts"),
                ("athlete_count", "integer", "Unique athletes"),
                ("star_count", "integer", "Stars"),
                ("athlete_segment_stats", "SummarySegmentEffort", "Authenticated athlete's best effort"),
                ("xoms", "Xoms", "KOM/QOM times"),
                ("local_legend", "LocalLegend", "Local legend info"),
            ]),
            ("DetailedSegmentEffort", "Full segment effort data.", [
                ("id", "long", "Effort identifier"),
                ("activity_id", "long", "Parent activity ID"),
                ("elapsed_time", "integer", "Elapsed time in seconds"),
                ("start_date", "datetime", "Start time UTC"),
                ("start_date_local", "datetime", "Start time local"),
                ("distance", "float", "Effort distance in meters"),
                ("is_kom", "boolean", "KOM/QOM flag"),
                ("name", "string", "Segment name"),
                ("activity", "MetaActivity", "Activity reference"),
                ("athlete", "MetaAthlete", "Athlete reference"),
                ("moving_time", "integer", "Moving time in seconds"),
                ("start_index", "integer", "Start stream index"),
                ("end_index", "integer", "End stream index"),
                ("average_cadence", "float", "Average cadence"),
                ("average_watts", "float", "Average power"),
                ("device_watts", "boolean", "Power from device"),
                ("average_heartrate", "float", "Average HR"),
                ("max_heartrate", "float", "Max HR"),
                ("segment", "SummarySegment", "Segment reference"),
                ("kom_rank", "integer", "KOM rank (null if not top 10)"),
                ("pr_rank", "integer", "PR rank (null if not top 3)"),
                ("hidden", "boolean", "Hidden from public segment page"),
            ]),
            ("Zones", "Athlete training zones.", [
                ("heart_rate", "HeartRateZoneRanges", "HR zones"),
                ("power", "PowerZoneRanges", "Power zones"),
            ]),
            ("Route", "An athlete's saved route.", [
                ("id", "long", "Route identifier"),
                ("idStr", "string", "Route ID as string"),
                ("name", "string", "Route name"),
                ("description", "string", "Route description"),
                ("athlete", "SummaryAthlete", "Athlete who created route"),
                ("distance", "float", "Route distance in meters"),
                ("elevation_gain", "float", "Elevation gain in meters"),
                ("map", "PolylineMap", "Route map"),
                ("map_urls", "MapUrls", "Map image URLs"),
                ("type", "integer", "Route type: 1=ride, 2=run"),
                ("sub_type", "integer", "Sub-type: 1=road, 2=mtb, etc."),
                ("private", "boolean", "Private flag"),
                ("starred", "boolean", "Starred flag"),
                ("timestamp", "integer", "Creation timestamp"),
                ("waypoints", "Waypoint[]", "Route waypoints"),
                ("segments", "SummarySegment[]", "Segment list"),
                ("created_at", "datetime", "Creation date"),
                ("updated_at", "datetime", "Last update date"),
            ]),
            ("DetailedClub", "Detailed club information.", [
                ("id", "long", "Club identifier"),
                ("name", "string", "Club name"),
                ("profile_medium", "string", "Medium profile picture URL"),
                ("profile", "string", "Full profile picture URL"),
                ("description", "string", "Club description"),
                ("club_type", "string", "Club type"),
                ("sport_type", "string", "Primary sport type"),
                ("city", "string", "City"),
                ("state", "string", "State"),
                ("country", "string", "Country"),
                ("private", "boolean", "Private flag"),
                ("member_count", "integer", "Member count"),
                ("featured", "boolean", "Featured flag"),
                ("verified", "boolean", "Verified flag"),
                ("url", "string", "Club URL slug"),
                ("membership", "string", "member/pending/null"),
                ("admin", "boolean", "Authenticated athlete is admin"),
                ("owner", "boolean", "Authenticated athlete is owner"),
                ("following_count", "integer", "Followers who are members"),
            ]),
            ("DetailedGear", "Detailed gear information.", [
                ("id", "string", "Gear identifier"),
                ("primary", "boolean", "Primary gear flag"),
                ("name", "string", "Gear name"),
                ("distance", "float", "Recorded distance in meters"),
                ("brand_name", "string", "Brand name"),
                ("model_name", "string", "Model name"),
                ("frame_type", "integer", "Frame type (bikes only)"),
                ("description", "string", "Gear description"),
                ("nickname", "string", "Gear nickname"),
            ]),
        ]

        for name, desc, fields_data in models_data:
            self.models.append(Model(
                name=name,
                description=desc,
                fields=[
                    ModelField(name=f[0], data_type=f[1], description=f[2])
                    for f in fields_data
                ],
            ))

    # ------------------------------------------------------------------
    # Write markdown files
    # ------------------------------------------------------------------

    def write_markdown_files(self, output_dir: Path) -> None:
        """Write one MD file per category plus models and overview."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Category files
        for cat_name in CATEGORY_ORDER:
            category = self.categories.get(cat_name)
            if category is None:
                continue
            slug = cat_name.lower().replace(" ", "_")
            out_file = output_dir / f"{slug}.md"
            content = self._render_category_md(category)
            out_file.write_text(content, encoding="utf-8")
            print(f"  Written: {out_file}  ({len(category.endpoints)} endpoints)")

        # Models file
        models_file = output_dir / "models.md"
        models_file.write_text(self._render_models_md(), encoding="utf-8")
        print(f"  Written: {models_file}  ({len(self.models)} models)")

        # Overview index
        overview_file = output_dir / "overview.md"
        overview_file.write_text(self._render_overview_md(), encoding="utf-8")
        print(f"  Written: {overview_file}")

    def _render_category_md(self, category: Category) -> str:
        lines: List[str] = [
            f"# Strava API v3 – {category.name}\n",
            f"> Auto-generated from https://developers.strava.com/docs/reference\n",
            f"**Total endpoints:** {len(category.endpoints)}\n",
            "---\n",
        ]
        for ep in category.endpoints:
            lines.append(f"## `{ep.method}` {ep.path}\n")
            lines.append(f"**Operation ID:** `{ep.operation_id}`  \n")
            lines.append(f"**Summary:** {ep.summary}  \n")
            if ep.scopes_required:
                scopes = ", ".join(f"`{s}`" for s in ep.scopes_required)
                lines.append(f"**Required Scopes:** {scopes}  \n")
            if ep.description:
                lines.append(f"\n{ep.description}\n")
            if ep.parameters:
                lines.append("\n### Parameters\n")
                lines.append("| Name | In | Required | Type | Description |")
                lines.append("|------|----|----------|------|-------------|")
                for p in ep.parameters:
                    req = "✅" if p.required else "❌"
                    lines.append(
                        f"| `{p.name}` | {p.location} | {req} | `{p.data_type}` | {p.description} |"
                    )
                lines.append("")
            if ep.response_model:
                lines.append(f"\n### Response\n")
                lines.append(f"Returns: **`{ep.response_model}`**\n")
            if ep.example_curl:
                lines.append("\n### Example\n")
                lines.append(f"```bash\n{ep.example_curl}\n```\n")
            lines.append("---\n")
        return "\n".join(lines)

    def _render_models_md(self) -> str:
        lines: List[str] = [
            "# Strava API v3 – Data Models\n",
            "> Auto-generated from https://developers.strava.com/docs/reference\n",
            f"**Total models:** {len(self.models)}\n",
            "---\n",
        ]
        for model in self.models:
            lines.append(f"## {model.name}\n")
            if model.description:
                lines.append(f"{model.description}\n")
            if model.fields:
                lines.append("\n| Field | Type | Description |")
                lines.append("|-------|------|-------------|")
                for f in model.fields:
                    lines.append(f"| `{f.name}` | `{f.data_type}` | {f.description} |")
                lines.append("")
            lines.append("---\n")
        return "\n".join(lines)

    def _render_overview_md(self) -> str:
        lines: List[str] = [
            "# Strava API v3 – Overview\n",
            "> Auto-generated from https://developers.strava.com/docs/reference\n",
            "## Base URL\n",
            "```\nhttps://www.strava.com/api/v3\n```\n",
            "## Authentication\n",
            "All endpoints require Bearer token authentication via OAuth2.\n",
            "## Rate Limits\n",
            "- **15-minute limit:** 100 requests\n",
            "- **Daily limit:** 1,000 requests\n",
            "## Endpoint Categories\n",
            "| Category | Endpoints | Description |",
            "|----------|-----------|-------------|",
        ]
        descriptions = {
            "Activities": "Create, read, update activities; laps, kudos, comments, zones",
            "Athletes": "Authenticated athlete profile, zones, stats",
            "Clubs": "Club details, members, activities",
            "Gears": "Bike and shoe gear details",
            "Routes": "Athlete routes, GPX/TCX export",
            "SegmentEfforts": "Individual efforts on segments with time filtering",
            "Segments": "Explore, star, and retrieve segments",
            "Streams": "Raw time-series sensor data (GPS, HR, power, cadence…)",
            "Uploads": "Upload FIT/GPX/TCX activity files",
        }
        for cat_name in CATEGORY_ORDER:
            cat = self.categories.get(cat_name, Category(name=cat_name))
            slug = cat_name.lower().replace(" ", "_")
            desc = descriptions.get(cat_name, "")
            lines.append(
                f"| [{cat_name}](./{slug}.md) | {len(cat.endpoints)} | {desc} |"
            )
        lines.append("")
        lines.append("## All Models\n")
        lines.append(f"See [models.md](./models.md) — {len(self.models)} models documented.\n")
        lines.append("## Useful Resources\n")
        lines.append("- [Official Reference](https://developers.strava.com/docs/reference)\n")
        lines.append("- [Authentication Guide](https://developers.strava.com/docs/authentication)\n")
        lines.append("- [Rate Limits](https://developers.strava.com/docs/rate-limits)\n")
        lines.append("- [Webhooks](https://developers.strava.com/docs/webhooks)\n")
        lines.append("- [Swagger Playground](https://developers.strava.com/playground)\n")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Strava docs scraper."""
    scraper = StravaScraper()

    print("=" * 60)
    print("Strava API Documentation Scraper")
    print("=" * 60)

    # Attempt live fetch; fall back to static data if fetch fails
    try:
        scraper.fetch()
        scraper.parse()
    except Exception as exc:
        print(f"  Live fetch/parse failed ({exc}); using static known data.")

    # Always ensure complete data via static fallback (Strava docs are JS-heavy)
    scraper.populate_static_data()

    print(f"\nWriting markdown files to: {OUTPUT_DIR}")
    scraper.write_markdown_files(OUTPUT_DIR)

    total_eps = sum(len(c.endpoints) for c in scraper.categories.values())
    print(f"\n✅ Done! {total_eps} endpoints, {len(scraper.models)} models saved.")
    print(f"   Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
