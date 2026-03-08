"""Interactive helper to obtain a Strava OAuth2 refresh token.

Usage::

    python scripts/get_refresh_token.py

The script will:
1. Read STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET from .env (or environment).
2. Print the authorisation URL.
3. Wait for you to paste the ``code`` query parameter from the redirect.
4. Exchange the code for tokens and write them to .env.

Required Strava app scopes:  activity:read_all,read_all
"""

from __future__ import annotations

import asyncio
import os
import urllib.parse
from pathlib import Path

import httpx
from dotenv import load_dotenv, set_key

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
REDIRECT_URI = "http://localhost"  # no local server needed – copy from browser bar


def _load_credentials() -> tuple[str, str]:
    load_dotenv(ENV_PATH)
    client_id = os.getenv("STRAVA_CLIENT_ID", "").strip()
    client_secret = os.getenv("STRAVA_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "❌  STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set in .env first."
        )
    return client_id, client_secret


async def _exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    async with httpx.AsyncClient() as http:
        response = await http.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        return response.json()


async def main() -> None:
    client_id, client_secret = _load_credentials()

    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "force",
        "scope": "activity:read_all,read_all",
    }
    url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    print("\n═══════════════════════════════════════════════════════════")
    print("  Strava OAuth2 – Refresh Token Helper")
    print("═══════════════════════════════════════════════════════════")
    print("\n1. Open this URL in your browser:\n")
    print(f"   {url}\n")
    print("2. Authorise the app and you'll be redirected to:")
    print(f"   {REDIRECT_URI}/?state=&code=<CODE>&scope=...\n")
    print("3. Copy the value of the 'code' parameter from the URL.")
    print("═══════════════════════════════════════════════════════════\n")

    code = input("Paste the 'code' value here: ").strip()
    if not code:
        raise SystemExit("❌  No code entered. Aborting.")

    print("\n⏳  Exchanging code for tokens …")
    data = await _exchange_code(client_id, client_secret, code)

    access_token: str = data.get("access_token", "")
    refresh_token: str = data.get("refresh_token", "")
    expires_at: int = data.get("expires_at", 0)
    athlete = data.get("athlete", {})
    athlete_name = (
        f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
    )

    if not refresh_token:
        raise SystemExit(f"❌  Token exchange failed: {data}")

    # Write to .env
    if not ENV_PATH.exists():
        ENV_PATH.write_text("")

    set_key(str(ENV_PATH), "STRAVA_CLIENT_ID", client_id)
    set_key(str(ENV_PATH), "STRAVA_CLIENT_SECRET", client_secret)
    set_key(str(ENV_PATH), "STRAVA_REFRESH_TOKEN", refresh_token)
    set_key(str(ENV_PATH), "STRAVA_ACCESS_TOKEN", access_token)
    set_key(str(ENV_PATH), "STRAVA_TOKEN_EXPIRY", str(expires_at))

    print("\n✅  Success!")
    if athlete_name:
        print(f"   Authenticated as: {athlete_name}")
    print(f"   Refresh token written to: {ENV_PATH}")
    print("\nYou can now run the MCP server:\n")
    print("   python -m strava_mcp.mcp_server.server\n")


if __name__ == "__main__":
    asyncio.run(main())
