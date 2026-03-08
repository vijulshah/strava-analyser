"""Base async Strava API HTTP client with Bearer auth injection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx

from strava_mcp.client.auth import token_manager

T = TypeVar("T")

_BASE_URL = "https://www.strava.com/api/v3"
_DEFAULT_TIMEOUT = 30.0


class StravaClient:
    """Async HTTP client for the Strava API v3.

    Automatically injects the Bearer access token on every request
    and raises on non-2xx responses.

    Usage::

        async with StravaClient() as client:
            data = await client.get("/athlete")
    """

    def __init__(self) -> None:
        self._http: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "StravaClient":
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=_DEFAULT_TIMEOUT,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._http:
            await self._http.aclose()

    def _auth_headers(self) -> Dict[str, str]:
        """Build Authorization header with current access token.

        Returns:
            Dict with Authorization Bearer header.
        """
        token = token_manager.get_access_token()
        return {"Authorization": f"Bearer {token}"}

    async def _get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Send an authenticated GET request.

        Args:
            path: API path (relative to base URL).
            params: Optional query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: On non-2xx response.
        """
        assert self._http is not None, "Use as async context manager"
        # Strip None values from params
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        response = await self._http.get(
            path, params=clean_params, headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()

    async def _post(self, path: str, data: Dict[str, Any]) -> Any:
        """Send an authenticated POST request.

        Args:
            path: API path.
            data: JSON body.

        Returns:
            Parsed JSON response.
        """
        assert self._http is not None
        response = await self._http.post(
            path, json=data, headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()

    async def _put(self, path: str, data: Dict[str, Any]) -> Any:
        """Send an authenticated PUT request.

        Args:
            path: API path.
            data: JSON body.

        Returns:
            Parsed JSON response.
        """
        assert self._http is not None
        response = await self._http.put(
            path, json=data, headers=self._auth_headers()
        )
        response.raise_for_status()
        return response.json()

    # -----------------------------------------------------------------------
    # Athletes
    # -----------------------------------------------------------------------

    async def get_athlete(self) -> Dict[str, Any]:
        """GET /athlete – authenticated athlete profile."""
        return await self._get("/athlete")

    async def get_athlete_zones(self) -> Dict[str, Any]:
        """GET /athlete/zones – HR and power training zones."""
        return await self._get("/athlete/zones")

    async def get_athlete_stats(self, athlete_id: int) -> Dict[str, Any]:
        """GET /athletes/{id}/stats – activity stats.

        Args:
            athlete_id: Athlete's Strava ID.
        """
        return await self._get(f"/athletes/{athlete_id}/stats")

    # -----------------------------------------------------------------------
    # Activities
    # -----------------------------------------------------------------------

    async def list_activities(
        self,
        before: Optional[int] = None,
        after: Optional[int] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """GET /athlete/activities – list authenticated athlete's activities.

        Args:
            before: Epoch timestamp — return activities before this time.
            after: Epoch timestamp — return activities after this time.
            page: Page number (default 1).
            per_page: Items per page (default 30, max 200).

        Returns:
            List of SummaryActivity dicts.
        """
        return await self._get(
            "/athlete/activities",
            params={"before": before, "after": after, "page": page, "per_page": per_page},
        )

    async def get_activity(
        self, activity_id: int, include_all_efforts: bool = True
    ) -> Dict[str, Any]:
        """GET /activities/{id} – detailed activity.

        Args:
            activity_id: Activity identifier.
            include_all_efforts: Include all segment efforts.
        """
        return await self._get(
            f"/activities/{activity_id}",
            params={"include_all_efforts": include_all_efforts},
        )

    async def get_activity_laps(self, activity_id: int) -> List[Dict[str, Any]]:
        """GET /activities/{id}/laps."""
        return await self._get(f"/activities/{activity_id}/laps")

    async def get_activity_comments(
        self, activity_id: int, page_size: int = 30, after_cursor: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """GET /activities/{id}/comments."""
        return await self._get(
            f"/activities/{activity_id}/comments",
            params={"page_size": page_size, "after_cursor": after_cursor},
        )

    async def get_activity_kudoers(
        self, activity_id: int, page: int = 1, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """GET /activities/{id}/kudos."""
        return await self._get(
            f"/activities/{activity_id}/kudos",
            params={"page": page, "per_page": per_page},
        )

    async def get_activity_zones(self, activity_id: int) -> List[Dict[str, Any]]:
        """GET /activities/{id}/zones – HR and power zones."""
        return await self._get(f"/activities/{activity_id}/zones")

    async def get_activity_streams(
        self,
        activity_id: int,
        keys: List[str],
    ) -> Dict[str, Any]:
        """GET /activities/{id}/streams.

        Args:
            activity_id: Activity identifier.
            keys: List of stream types (e.g. ['time', 'heartrate', 'watts']).
        """
        return await self._get(
            f"/activities/{activity_id}/streams",
            params={"keys": ",".join(keys), "key_by_type": "true"},
        )

    # -----------------------------------------------------------------------
    # Segments
    # -----------------------------------------------------------------------

    async def get_segment(self, segment_id: int) -> Dict[str, Any]:
        """GET /segments/{id}."""
        return await self._get(f"/segments/{segment_id}")

    async def get_starred_segments(
        self, page: int = 1, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """GET /segments/starred."""
        return await self._get(
            "/segments/starred", params={"page": page, "per_page": per_page}
        )

    async def explore_segments(
        self,
        bounds: str,
        activity_type: Optional[str] = None,
        min_cat: Optional[int] = None,
        max_cat: Optional[int] = None,
    ) -> Dict[str, Any]:
        """GET /segments/explore.

        Args:
            bounds: 'SW_lat,SW_lng,NE_lat,NE_lng' bounding box.
            activity_type: 'running' or 'riding'.
            min_cat: Minimum climb category (0-5).
            max_cat: Maximum climb category (0-5).
        """
        return await self._get(
            "/segments/explore",
            params={
                "bounds": bounds,
                "activity_type": activity_type,
                "min_cat": min_cat,
                "max_cat": max_cat,
            },
        )

    async def get_segment_efforts(
        self,
        segment_id: int,
        start_date_local: Optional[str] = None,
        end_date_local: Optional[str] = None,
        per_page: int = 30,
    ) -> List[Dict[str, Any]]:
        """GET /segment_efforts – efforts on a segment.

        Args:
            segment_id: Segment identifier.
            start_date_local: ISO 8601 start date filter.
            end_date_local: ISO 8601 end date filter.
            per_page: Items per page.
        """
        return await self._get(
            "/segment_efforts",
            params={
                "segment_id": segment_id,
                "start_date_local": start_date_local,
                "end_date_local": end_date_local,
                "per_page": per_page,
            },
        )

    async def get_segment_effort(self, effort_id: int) -> Dict[str, Any]:
        """GET /segment_efforts/{id}."""
        return await self._get(f"/segment_efforts/{effort_id}")

    async def get_segment_streams(
        self, segment_id: int, keys: List[str]
    ) -> Dict[str, Any]:
        """GET /segments/{id}/streams."""
        return await self._get(
            f"/segments/{segment_id}/streams",
            params={"keys": ",".join(keys), "key_by_type": "true"},
        )

    # -----------------------------------------------------------------------
    # Clubs
    # -----------------------------------------------------------------------

    async def get_athlete_clubs(
        self, page: int = 1, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """GET /athlete/clubs."""
        return await self._get(
            "/athlete/clubs", params={"page": page, "per_page": per_page}
        )

    async def get_club(self, club_id: int) -> Dict[str, Any]:
        """GET /clubs/{id}."""
        return await self._get(f"/clubs/{club_id}")

    async def get_club_activities(
        self, club_id: int, page: int = 1, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """GET /clubs/{id}/activities."""
        return await self._get(
            f"/clubs/{club_id}/activities",
            params={"page": page, "per_page": per_page},
        )

    async def get_club_members(
        self, club_id: int, page: int = 1, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """GET /clubs/{id}/members."""
        return await self._get(
            f"/clubs/{club_id}/members",
            params={"page": page, "per_page": per_page},
        )

    # -----------------------------------------------------------------------
    # Routes
    # -----------------------------------------------------------------------

    async def list_routes(
        self, athlete_id: int, page: int = 1, per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """GET /athletes/{id}/routes."""
        return await self._get(
            f"/athletes/{athlete_id}/routes",
            params={"page": page, "per_page": per_page},
        )

    async def get_route(self, route_id: int) -> Dict[str, Any]:
        """GET /routes/{id}."""
        return await self._get(f"/routes/{route_id}")

    async def get_route_streams(self, route_id: int) -> Dict[str, Any]:
        """GET /routes/{id}/streams."""
        return await self._get(f"/routes/{route_id}/streams")

    # -----------------------------------------------------------------------
    # Gear
    # -----------------------------------------------------------------------

    async def get_gear(self, gear_id: str) -> Dict[str, Any]:
        """GET /gear/{id}."""
        return await self._get(f"/gear/{gear_id}")
