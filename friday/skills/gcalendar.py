"""Google Calendar skill: read the schedule and create / move / cancel events.

Requires Google authorization (see integrations/google_auth.py). Meeting
creation with Google Meet links lives in skills/meetings.py, which builds on
the same calendar service.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from friday.core.config import settings
from friday.integrations.google_auth import GoogleAuthError, calendar_service
from friday.skills.base import skill


def _event_summary(ev: dict) -> dict:
    start = ev.get("start", {})
    end = ev.get("end", {})
    return {
        "id": ev.get("id"),
        "title": ev.get("summary", "(no title)"),
        "start": start.get("dateTime") or start.get("date"),
        "end": end.get("dateTime") or end.get("date"),
        "location": ev.get("location", ""),
        "meet_link": ev.get("hangoutLink", ""),
        "attendees": [a.get("email") for a in ev.get("attendees", []) if a.get("email")],
        "status": ev.get("status"),
    }


@skill(
    name="list_events",
    description=(
        "List Google Calendar events in a time window (default: today). Use this for the "
        "agenda in a daily briefing or to check availability before scheduling."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "start": {
                "type": "string",
                "description": "ISO start datetime (e.g. 2026-07-05T00:00:00). Omit for the start of today.",
            },
            "end": {
                "type": "string",
                "description": "ISO end datetime. Omit for end of today (or +N days if 'days' is given).",
            },
            "days": {
                "type": "integer",
                "description": "Convenience: events for the next N days starting now (ignored if start/end given).",
            },
            "calendar_id": {"type": "string", "description": "Calendar id (default 'primary')."},
        },
    },
)
def list_events(start: str = "", end: str = "", days: int = 0, calendar_id: str = "primary") -> dict:
    try:
        service = calendar_service()
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    try:
        now = datetime.now(timezone.utc)
        if start:
            time_min = start
        else:
            time_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if end:
            time_max = end
        elif days:
            time_max = (now + timedelta(days=days)).isoformat()
        else:
            time_max = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

        result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = [_event_summary(ev) for ev in result.get("items", [])]
        return {"count": len(events), "events": events, "time_min": time_min, "time_max": time_max}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Calendar request failed: {exc}"}


@skill(
    name="create_event",
    description=(
        "Create a Google Calendar event (without a video link — use create_meeting for "
        "one with Google Meet or Zoom). Times are ISO 8601; if no timezone offset is "
        "given, the configured FRIDAY_TIMEZONE is assumed."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title."},
            "start": {"type": "string", "description": "ISO start datetime, e.g. 2026-07-06T14:00:00."},
            "end": {"type": "string", "description": "ISO end datetime. Omit to default to 1 hour after start."},
            "description": {"type": "string", "description": "Optional event description/notes."},
            "location": {"type": "string", "description": "Optional location."},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional attendee email addresses.",
            },
            "calendar_id": {"type": "string", "description": "Calendar id (default 'primary')."},
        },
        "required": ["title", "start"],
    },
)
def create_event(
    title: str,
    start: str,
    end: str = "",
    description: str = "",
    location: str = "",
    attendees: list[str] | None = None,
    calendar_id: str = "primary",
) -> dict:
    try:
        service = calendar_service()
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    if not end:
        try:
            end = (datetime.fromisoformat(start) + timedelta(hours=1)).isoformat()
        except ValueError:
            return {"error": f"Invalid start datetime '{start}'. Use ISO 8601."}
    body = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {"dateTime": start, "timeZone": settings.timezone},
        "end": {"dateTime": end, "timeZone": settings.timezone},
    }
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]
    try:
        ev = service.events().insert(calendarId=calendar_id, body=body, sendUpdates="all").execute()
        return {"created": True, "event": _event_summary(ev), "html_link": ev.get("htmlLink")}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't create event: {exc}"}


@skill(
    name="update_event",
    description="Move or edit an existing Google Calendar event (new time, title, etc.).",
    input_schema={
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The event id (from list_events)."},
            "start": {"type": "string", "description": "New ISO start datetime (optional)."},
            "end": {"type": "string", "description": "New ISO end datetime (optional)."},
            "title": {"type": "string", "description": "New title (optional)."},
            "calendar_id": {"type": "string", "description": "Calendar id (default 'primary')."},
        },
        "required": ["event_id"],
    },
)
def update_event(
    event_id: str, start: str = "", end: str = "", title: str = "", calendar_id: str = "primary"
) -> dict:
    try:
        service = calendar_service()
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    try:
        ev = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        if title:
            ev["summary"] = title
        if start:
            ev["start"] = {"dateTime": start, "timeZone": settings.timezone}
        if end:
            ev["end"] = {"dateTime": end, "timeZone": settings.timezone}
        updated = (
            service.events()
            .update(calendarId=calendar_id, eventId=event_id, body=ev, sendUpdates="all")
            .execute()
        )
        return {"updated": True, "event": _event_summary(updated)}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't update event {event_id}: {exc}"}


@skill(
    name="cancel_event",
    description="Cancel/delete a Google Calendar event by id (notifies attendees).",
    input_schema={
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The event id (from list_events)."},
            "calendar_id": {"type": "string", "description": "Calendar id (default 'primary')."},
        },
        "required": ["event_id"],
    },
)
def cancel_event(event_id: str, calendar_id: str = "primary") -> dict:
    try:
        service = calendar_service()
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    try:
        service.events().delete(
            calendarId=calendar_id, eventId=event_id, sendUpdates="all"
        ).execute()
        return {"cancelled": True, "event_id": event_id}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't cancel event {event_id}: {exc}"}
