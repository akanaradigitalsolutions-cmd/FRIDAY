"""Google OAuth helper shared by the Gmail, Calendar, and Meet skills.

One OAuth client covers all three Google APIs. The first time you run the
`authorize` flow it opens a browser, you consent, and a refresh token is
saved to GOOGLE_TOKEN_FILE — after that everything is non-interactive
(important for the scheduled morning briefing).

Setup (one time):
  1. In Google Cloud Console, create a project and enable the Gmail API and
     the Google Calendar API.
  2. Create an OAuth client ID of type "Desktop app" and download the JSON.
  3. Save it as the path in GOOGLE_CREDENTIALS_FILE (default
     ~/.friday/google_credentials.json).
  4. Run:  python -m friday.integrations.google_auth
     to complete consent and cache the token.

The google-api-python-client / google-auth libraries are an optional extra
(`pip install -e ".[google]"`), so this module imports them lazily and
returns a clear message if they're missing.
"""

from __future__ import annotations

import os
from pathlib import Path

from friday.core.config import settings

# Read/modify mail, and full calendar access (needed to create events with
# Meet links). Gmail "modify" lets us mark things read / add labels later;
# it does not allow permanent deletion.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]


class GoogleAuthError(RuntimeError):
    pass


def _require_libs():
    try:
        from google.auth.transport.requests import Request  # noqa: F401
        from google.oauth2.credentials import Credentials  # noqa: F401
        from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: F401
        from googleapiclient.discovery import build  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise GoogleAuthError(
            "Google API libraries aren't installed. Run: pip install -e \".[google]\""
        ) from exc


def get_credentials(interactive: bool = False):
    """Return valid Google OAuth credentials, refreshing or (if interactive)
    running the consent flow as needed."""
    _require_libs()
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_path = Path(settings.google_token_file)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
        return creds

    if not interactive:
        raise GoogleAuthError(
            "Google isn't authorized yet. Run: "
            "python -m friday.integrations.google_auth"
        )

    cred_path = Path(settings.google_credentials_file)
    if not cred_path.exists():
        raise GoogleAuthError(
            f"Missing OAuth client file at {cred_path}. Download a Desktop-app OAuth "
            "client ID from Google Cloud Console and save it there (see this module's "
            "docstring for the full setup)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(cred_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


def gmail_service():
    # get_credentials() validates that the libraries are installed and that a
    # token exists, raising GoogleAuthError otherwise — do it before importing
    # build so a missing dependency surfaces as a clean, catchable error.
    creds = get_credentials()
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def calendar_service():
    creds = get_credentials()
    from googleapiclient.discovery import build

    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def is_configured() -> bool:
    """True if a cached token exists (so non-interactive calls can work)."""
    return Path(settings.google_token_file).exists()


def main() -> None:
    """Run the interactive consent flow to cache a token."""
    try:
        get_credentials(interactive=True)
    except GoogleAuthError as exc:
        print(f"Authorization failed: {exc}")
        raise SystemExit(1)
    print(f"Google authorized. Token cached at {settings.google_token_file}")


if __name__ == "__main__":
    main()
