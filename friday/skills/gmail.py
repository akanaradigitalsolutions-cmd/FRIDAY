"""Gmail skill: read the inbox, surface unread mail, and mark messages read.

Urgency classification is intentionally *not* hardcoded here — the assistant
(Claude) reads the returned messages and decides what's urgent, which is far
better than a keyword rule. This skill's job is just to fetch clean, readable
message summaries.

Requires Google authorization (see integrations/google_auth.py). Without it,
every call returns a clear, actionable error instead of crashing.
"""

from __future__ import annotations

import base64
from typing import Any

from friday.integrations.google_auth import GoogleAuthError, gmail_service
from friday.skills.base import skill


def _header(payload: dict, name: str) -> str:
    for h in payload.get("headers", []):
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _extract_text(payload: dict) -> str:
    """Best-effort plain-text body extraction from a Gmail message payload."""
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")
    if mime == "text/plain" and data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        text = _extract_text(part)
        if text:
            return text
    # Fall back to any body data if no text/plain part was found.
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def _summarize_message(service, msg_id: str, snippet_only: bool) -> dict[str, Any]:
    fmt = "metadata" if snippet_only else "full"
    msg = service.users().messages().get(userId="me", id=msg_id, format=fmt).execute()
    payload = msg.get("payload", {})
    summary = {
        "id": msg_id,
        "thread_id": msg.get("threadId"),
        "from": _header(payload, "From"),
        "subject": _header(payload, "Subject"),
        "date": _header(payload, "Date"),
        "snippet": msg.get("snippet", ""),
        "unread": "UNREAD" in msg.get("labelIds", []),
    }
    if not snippet_only:
        body = _extract_text(payload)
        summary["body"] = body[:4000]
    return summary


@skill(
    name="list_emails",
    description=(
        "List recent Gmail messages (default: unread in the inbox) so the assistant can "
        "triage them and decide what's urgent or needs a reply. Returns sender, subject, "
        "date, and a snippet for each. Use full=true to include message bodies."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gmail search query. Default 'is:unread in:inbox'. "
                "Examples: 'from:boss@x.com', 'newer_than:1d', 'is:important'.",
            },
            "max_results": {"type": "integer", "description": "Max messages (default 15)."},
            "full": {
                "type": "boolean",
                "description": "If true, include full message bodies (slower). Default false (snippets only).",
            },
        },
    },
)
def list_emails(query: str = "is:unread in:inbox", max_results: int = 15, full: bool = False) -> dict:
    try:
        service = gmail_service()
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    try:
        listing = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        ids = [m["id"] for m in listing.get("messages", [])]
        messages = [_summarize_message(service, mid, snippet_only=not full) for mid in ids]
        return {"query": query, "count": len(messages), "emails": messages}
    except Exception as exc:  # noqa: BLE001 - surface API errors to the model
        return {"error": f"Gmail request failed: {exc}"}


@skill(
    name="read_email",
    description="Read the full body of a specific Gmail message by its id (from list_emails).",
    input_schema={
        "type": "object",
        "properties": {"id": {"type": "string", "description": "The Gmail message id."}},
        "required": ["id"],
    },
)
def read_email(id: str) -> dict:  # noqa: A002 - matches the tool's argument name
    try:
        service = gmail_service()
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    try:
        return _summarize_message(service, id, snippet_only=False)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't read message {id}: {exc}"}


@skill(
    name="mark_email_read",
    description="Mark a Gmail message as read (removes the UNREAD label). Does not delete anything.",
    input_schema={
        "type": "object",
        "properties": {"id": {"type": "string", "description": "The Gmail message id."}},
        "required": ["id"],
    },
)
def mark_email_read(id: str) -> dict:  # noqa: A002
    try:
        service = gmail_service()
    except GoogleAuthError as exc:
        return {"error": str(exc)}
    try:
        service.users().messages().modify(
            userId="me", id=id, body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return {"id": id, "marked_read": True}
    except Exception as exc:  # noqa: BLE001
        return {"error": f"Couldn't mark message {id} read: {exc}"}
