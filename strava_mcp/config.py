"""Application configuration using pydantic-settings.

Reads all settings from environment variables / .env file.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Root of the project (two levels up from this file)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
ENV_FILE: Path = PROJECT_ROOT / ".env"


class StravaSettings(BaseSettings):
    """Strava OAuth2 + app configuration.

    All values are read from the .env file or environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Strava OAuth ---
    # Only client_id and client_secret are required at startup.
    # refresh_token / access_token can be obtained later via the /auth/* endpoints.
    strava_client_id: str = Field(..., description="Strava app client ID")
    strava_client_secret: str = Field(..., description="Strava app client secret")
    strava_refresh_token: str = Field(
        default="", description="Strava OAuth refresh token (set via /auth/callback)"
    )

    # Managed automatically by TokenManager — do not set manually
    strava_access_token: str = Field(default="", description="Current access token")
    strava_token_expiry: float = Field(
        default=0.0, description="Access token expiry epoch"
    )

    # --- FastAPI ---
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    api_debug: bool = Field(default=True)

    @field_validator("strava_client_id", "strava_client_secret", mode="before")
    @classmethod
    def must_not_be_placeholder(cls, v: str, info: object) -> str:
        """Ensure credentials are not still set to placeholder values."""
        placeholders = {"your_client_id_here", "your_client_secret_here"}
        if v in placeholders:
            raise ValueError(
                "Please configure a real value in your .env file. "
                "See .env.example for instructions."
            )
        return v

    def is_authenticated(self) -> bool:
        """Return True if a refresh token has been configured."""
        return bool(self.strava_refresh_token)


def get_settings() -> StravaSettings:
    """Return a cached StravaSettings instance.

    Returns:
        StravaSettings: Application settings loaded from .env.

    Raises:
        ValidationError: If required env vars are missing or invalid.
    """
    return StravaSettings()  # type: ignore[call-arg]


# Single shared instance – import this where needed
settings: StravaSettings = StravaSettings()  # type: ignore[call-arg]
