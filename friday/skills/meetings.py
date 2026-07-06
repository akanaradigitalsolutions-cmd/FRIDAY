"""Meeting arrangement skill: schedule a meeting with a video link and put it
on the calendar.

Two providers:
  - "meet"  → a Google Meet link, created automatically by the Calendar API
              when the event is inserted (free, no separate API). The event
              lands on your Google Calendar.
  - "zoom"  → a Zoom meeting via Zoom's Server-to-Server OAuth API; we then
              also create a matching Google Calendar event carrying the Zoom
              join link, so it shows up on your schedule either way.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from friday.core.config import settings
from friday.integrations.google_auth import GoogleAuthError, calendar_service
from friday.integrations import zoom_auth
from friday.skills.base import skill


def _default_end(start: str, duration_minutes: int) -> str:
    return (datetime.fromisoformat(start) + timedelta(minutes=duration_minutes)).isoformat()


def _create_meet(title, start, end, description, attendees, calendar_id):
    service = calendar_service()
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start, "timeZone": settings.timezone},
        "end": {"dateTime": end, "timeZone": settings.timezone},
        "conferenceData": {
            "createRequest": {
                "requestId": uuid.uuid4().hex,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    ev = (
        service.events()
        .insert(calendarId=calendar_id, body=body, conferenceDataVersion=1, sendUpdates="all")
        .execute()
    )
    return {
        "provider": "meet",
        "title": title,
        "start": start,
        "end": end,
        "join_url": ev.get("hangoutLink", ""),
        "event_id": ev.get("id"),
        "calendar_link": ev.get("htmlLink"),
        "attendees": attendees or [],
    }


def _create_zoom(title, start, end, description, duration_minutes, attendees, calendar_id):
    zoom = zoom_auth.create_meeting(
        topic=title,
        start_time=start,
        duration_minutes=duration_minutes,
        timezone=settings.timezone,
    )
    join_url = zoom.get("join_url", "")
    # Mirror it onto Google Calendar so it appears on the schedule too.
    calendar_link = ""
    event_id = ""
    try:
        service = calendar_service()
        body = {
            "summary": title,
            "description": (description + "\n\n" if description else "") + f"Zoom: {join_url}",
            "start": {"dateTime": start, "timeZone": settings.timezone},
            "end": {"dateTime": end, "timeZone": settings.timezone},
        }
        if attendees:
            body["attendees"] = [{"email": e} for e in attendees]
        ev = service.events().insert(calendarId=calendar_id, body=body, sendUpdates="all").execute()
        calendar_link = ev.get("htmlLink", "")
        event_id = ev.get("id", "")
    except GoogleAuthError:
        # Zoom meeting still created; calendar mirroring is best-effort.
        pass
    return {
        "provider": "zoom",
        "title": title,
        "start": start,
        "end": end,
        "join_url": join_url,
        "zoom_meeting_id": zoom.get("id"),
        "event_id": event_id,
        "calendar_link": calendar_link,
        "attendees": attendees or [],
    }


@skill(
    name="create_meeting",
    description=(
        "Schedule a meeting with a video link and add it to Google Calendar. provider "
        "'meet' creates a free Google Meet link; provider 'zoom' creates a Zoom meeting. "
        "Returns the join URL. Times are ISO 8601 in the configured timezone."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Meeting title/topic."},
            "start": {"type": "string", "description": "ISO start datetime, e.g. 2026-07-06T15:00:00."},
            "provider": {
                "type": "string",
                "enum": ["meet", "zoom"],
                "description": "Video provider: 'meet' (Google Meet, default) or 'zoom'.",
            },
            "duration_minutes": {"type": "integer", "description": "Length in minutes (default 30)."},
            "end": {"type": "string", "description": "ISO end datetime (overrides duration_minutes if given)."},
            "description": {"type": "string", "description": "Optional agenda/notes."},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Attendee email addresses to invite.",
            },
            "calendar_id": {"type": "string", "description": "Calendar id (default 'primary')."},
        },
        "required": ["title", "start"],
    },
)
def create_meeting(
    title: str,
    start: str,
    provider: str = "meet",
    duration_minutes: int = 30,
    end: str = "",
    description: str = "",
    attendees: list[str] | None = None,
    calendar_id: str = "primary",
) -> dict:
    try:
        resolved_end = end or _default_end(start, duration_minutes)
    except ValueError:
        return {"error": f"Invalid start datetime '{start}'. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS)."}

    try:
        if provider == "zoom":
            return _create_zoom(
                title, start, resolved_end, description, duration_minutes, attendees, calendar_id
            )
        if provider == "meet":
            return _create_meet(title, start, resolved_end, description, attendees, calendar_id)
        return {"error": f"Unknown provider '{provider}'. Use 'meet' or 'zoom'."}
    except zoom_auth.ZoomAuthError as exc:
        return {"error": str(exc)}
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't create the meeting: {exc}"}
