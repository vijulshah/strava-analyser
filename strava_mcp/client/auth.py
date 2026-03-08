"""Strava OAuth2 token manager.

Handles access token caching, expiry detection, and refresh via the
Strava token endpoint. Persists updated tokens back to the .env file.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import httpx

from strava_mcp.config import settings, PROJECT_ROOT

_STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
_STRAVA_DEAUTH_URL = "https://www.strava.com/oauth/deauthorize"
_ENV_FILE = PROJECT_ROOT / ".env"


class TokenManager:
    """Manages Strava access token lifecycle.

    Automatically refreshes the access token when it expires and
    persists the new token + expiry back to the .env file.

    The manager initialises from whatever is currently stored in settings,
    but tokens can also be injected at runtime via ``set_tokens()`` after
    the user completes the OAuth flow through the ``/auth/callback`` route.
    """

    def __init__(self) -> None:
        # Initialise from whatever is already stored (may be empty strings)
        self._access_token: str = settings.strava_access_token
        self._refresh_token: str = settings.strava_refresh_token
        self._token_expiry: float = settings.strava_token_expiry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_authenticated(self) -> bool:
        """Return True if a refresh token is available."""
        return bool(self._refresh_token)

    def is_expired(self) -> bool:
        """Check whether the current access token is expired (or missing).

        Returns:
            True if token needs refresh, False if still valid.
        """
        return not self._access_token or time.time() >= (self._token_expiry - 60)

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary.

        Returns:
            str: A valid Bearer access token.

        Raises:
            httpx.HTTPStatusError: If the refresh request fails.
            RuntimeError: If no refresh token is configured yet.
        """
        if not self.is_authenticated():
            raise RuntimeError(
                "Not authenticated. Visit /auth/login to authorise with Strava first."
            )
        if self.is_expired():
            self._refresh()
        return self._access_token

    def set_tokens(
        self,
        access_token: str,
        refresh_token: str,
        token_expiry: float,
    ) -> None:
        """Inject tokens obtained from the OAuth callback.

        This is called by the ``/auth/callback`` route after a successful
        code exchange. Tokens are stored in memory and persisted to .env.

        Args:
            access_token: New short-lived access token.
            refresh_token: Long-lived refresh token (may rotate each call).
            token_expiry: Unix epoch when the access token expires.
        """
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expiry = token_expiry
        # Also update the live settings object so other code sees the change
        settings.strava_access_token = access_token
        settings.strava_refresh_token = refresh_token
        settings.strava_token_expiry = token_expiry
        self._save_to_env(
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
        )

    def deauthorize(self) -> None:
        """Clear all stored tokens (local only; also call Strava's deauth endpoint)."""
        self._access_token = ""
        self._refresh_token = ""
        self._token_expiry = 0.0
        settings.strava_access_token = ""
        settings.strava_refresh_token = ""
        settings.strava_token_expiry = 0.0
        self._save_to_env(access_token="", refresh_token="", token_expiry=0.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Perform the OAuth2 refresh token flow.

        Raises:
            RuntimeError: If the refresh token is missing.
            httpx.HTTPStatusError: If the Strava API returns an error.
        """
        payload = {
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }

        with httpx.Client(timeout=15) as client:
            response = client.post(_STRAVA_TOKEN_URL, data=payload)
            response.raise_for_status()

        data = response.json()
        self.set_tokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", self._refresh_token),
            token_expiry=float(data["expires_at"]),
        )

    def _save_to_env(
        self,
        access_token: str,
        refresh_token: str,
        token_expiry: float,
    ) -> None:
        """Write updated token fields back to the .env file.

        Args:
            access_token: New access token.
            token_expiry: New expiry epoch timestamp.
            refresh_token: Potentially rotated refresh token.
        """
        if not _ENV_FILE.exists():
            return

        lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
        updates = {
            "STRAVA_ACCESS_TOKEN": access_token,
            "STRAVA_TOKEN_EXPIRY": str(token_expiry),
            "STRAVA_REFRESH_TOKEN": refresh_token,
        }

        new_lines: list[str] = []
        written: set[str] = set()
        for line in lines:
            key = line.split("=", 1)[0].strip().upper()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                written.add(key)
            else:
                new_lines.append(line)

        # Add any keys not yet present in the file
        for key, val in updates.items():
            if key not in written:
                new_lines.append(f"{key}={val}")

        _ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


# Module-level singleton — created lazily so startup never fails due to
# missing tokens; tokens are injected later via set_tokens().
token_manager = TokenManager()
