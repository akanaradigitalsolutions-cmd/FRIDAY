"""Tests for the skill registry and the graceful-degradation behavior of the
Google/Zoom skills when credentials aren't configured.
"""

from __future__ import annotations


def test_all_skills_registered():
    import friday.skills  # noqa: F401 - triggers registration
    from friday.skills import base

    names = {s.name for s in base.all_skills()}
    expected = {
        # obsidian
        "list_notes", "read_note", "write_note", "append_to_note",
        "get_daily_note", "update_daily_note", "add_task", "search_notes",
        # gmail
        "list_emails", "read_email", "mark_email_read",
        # calendar
        "list_events", "create_event", "update_event", "cancel_event",
        # meetings + reports
        "create_meeting", "save_report",
    }
    assert expected <= names


def test_skill_schemas_are_valid_json_schema():
    from friday.skills import base

    for s in base.all_skills():
        assert s.input_schema.get("type") == "object"
        assert "properties" in s.input_schema
        assert isinstance(s.description, str) and s.description


def test_gmail_without_credentials_returns_error(temp_vault):
    # temp_vault points config at a temp dir whose google token file doesn't
    # exist, so Gmail auth can't succeed and the skill must degrade gracefully.
    from friday.skills import gmail

    res = gmail.list_emails()
    assert "error" in res


def test_meeting_zoom_without_config_returns_error():
    from friday.skills import meetings

    res = meetings.create_meeting(
        title="Sync", start="2026-07-06T15:00:00", provider="zoom"
    )
    assert "error" in res


def test_meeting_bad_datetime_returns_error():
    from friday.skills import meetings

    res = meetings.create_meeting(title="Sync", start="not-a-date", provider="meet")
    assert "error" in res
