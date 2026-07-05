"""Tests for the Obsidian vault skill — the part that works with no external
credentials, so it's fully exercisable in CI.
"""

from __future__ import annotations

from datetime import datetime

import pytest


def test_write_and_read_note(temp_vault):
    vault, obsidian = temp_vault
    res = obsidian.write_note("Projects/Site.md", "# Site\nhello")
    assert res["written"] is True
    assert (vault / "Projects" / "Site.md").read_text() == "# Site\nhello"

    read = obsidian.read_note("Projects/Site")  # .md optional
    assert read["content"] == "# Site\nhello"
    assert read["path"] == "Projects/Site.md"


def test_write_note_no_overwrite_by_default(temp_vault):
    _, obsidian = temp_vault
    obsidian.write_note("a.md", "first")
    res = obsidian.write_note("a.md", "second")
    assert "error" in res
    res2 = obsidian.write_note("a.md", "second", overwrite=True)
    assert res2["written"] is True
    assert obsidian.read_note("a.md")["content"] == "second"


def test_append_creates_and_appends(temp_vault):
    vault, obsidian = temp_vault
    obsidian.append_to_note("log.md", "line1")
    obsidian.append_to_note("log.md", "line2")
    assert (vault / "log.md").read_text() == "line1\nline2\n"


def test_path_traversal_is_refused(temp_vault):
    _, obsidian = temp_vault
    with pytest.raises(obsidian.VaultPathError):
        obsidian._resolve("../escape.md")
    # A skill that gets a traversal path raises VaultPathError; the MCP server
    # catches it and returns the message to Claude rather than crashing.
    with pytest.raises(obsidian.VaultPathError):
        obsidian.read_note("../../etc/passwd")


def test_daily_note_roundtrip(temp_vault):
    vault, obsidian = temp_vault
    today = datetime.now().date().isoformat()

    empty = obsidian.get_daily_note()
    assert empty["exists"] is False
    assert empty["path"] == f"Daily/{today}.md"

    obsidian.update_daily_note("## Morning Briefing\nAll good.")
    got = obsidian.get_daily_note()
    assert got["exists"] is True
    assert "Morning Briefing" in got["content"]

    obsidian.update_daily_note("## Agenda\n- 9am standup")
    assert "Agenda" in obsidian.get_daily_note()["content"]
    assert "Morning Briefing" in obsidian.get_daily_note()["content"]  # append preserved


def test_add_task_writes_checkbox(temp_vault):
    _, obsidian = temp_vault
    obsidian.add_task("Reply to Alex")
    content = obsidian.get_daily_note()["content"]
    assert "- [ ] Reply to Alex" in content


def test_search_notes(temp_vault):
    _, obsidian = temp_vault
    obsidian.write_note("n1.md", "the quick brown fox")
    obsidian.write_note("n2.md", "nothing here")
    res = obsidian.search_notes("brown")
    assert res["count"] == 1
    assert res["results"][0]["path"] == "n1.md"
    assert "the quick brown fox" in res["results"][0]["matches"][0]


def test_list_notes(temp_vault):
    _, obsidian = temp_vault
    obsidian.write_note("a.md", "x")
    obsidian.write_note("sub/b.md", "y")
    listing = obsidian.list_notes()
    assert "a.md" in listing["notes"]
    assert "sub/b.md" in listing["notes"]
