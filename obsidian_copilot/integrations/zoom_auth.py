"""Zoom Server-to-Server OAuth client (standard library only — no extra deps).

Setup (one time):
  1. At https://marketplace.zoom.us create a "Server-to-Server OAuth" app.
  2. Give it the scope: meeting:write:admin (or meeting:write for your own user).
  3. Copy the Account ID, Client ID, and Client Secret into your .env as
     ZOOM_ACCOUNT_ID / ZOOM_CLIENT_ID / ZOOM_CLIENT_SECRET.

Tokens are short-lived; we fetch a fresh one per call (cheap) so there's no
token cache to manage.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

from obsidian_copilot.core.config import settings

_TOKEN_URL = "https://zoom.us/oauth/token"
_API_BASE = "https://api.zoom.us/v2"


class ZoomAuthError(RuntimeError):
    pass


def is_configured() -> bool:
    return bool(settings.zoom_account_id and settings.zoom_client_id and settings.zoom_client_secret)


def _access_token() -> str:
    if not is_configured():
        raise ZoomAuthError(
            "Zoom isn't configured. Set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, and "
            "ZOOM_CLIENT_SECRET (from a Server-to-Server OAuth app) in your .env."
        )
    params = urllib.parse.urlencode(
        {"grant_type": "account_credentials", "account_id": settings.zoom_account_id}
    )
    basic = base64.b64encode(
        f"{settings.zoom_client_id}:{settings.zoom_client_secret}".encode()
    ).decode()
    req = urllib.request.Request(
        f"{_TOKEN_URL}?{params}",
        method="POST",
        headers={"Authorization": f"Basic {basic}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise ZoomAuthError(f"Zoom token request failed ({exc.code}): {exc.read().decode()}") from exc
    except urllib.error.URLError as exc:
        raise ZoomAuthError(f"Zoom token request failed: {exc}") from exc
    token = data.get("access_token")
    if not token:
        raise ZoomAuthError(f"Zoom did not return an access token: {data}")
    return token


def create_meeting(topic: str, start_time: str, duration_minutes: int, timezone: str) -> dict:
    """Create a scheduled Zoom meeting for the authenticated account's user.
    Returns the raw Zoom API response (includes join_url and start_url)."""
    token = _access_token()
    body = json.dumps(
        {
            "topic": topic,
            "type": 2,  # scheduled meeting
            "start_time": start_time,
            "duration": duration_minutes,
            "timezone": timezone,
            "settings": {"join_before_host": True, "waiting_room": False},
        }
    ).encode()
    req = urllib.request.Request(
        f"{_API_BASE}/users/me/meetings",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise ZoomAuthError(f"Zoom meeting creation failed ({exc.code}): {exc.read().decode()}") from exc
    except urllib.error.URLError as exc:
        raise ZoomAuthError(f"Zoom meeting creation failed: {exc}") from exc
