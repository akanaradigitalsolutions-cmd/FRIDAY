"""Obsidian vault skill — the assistant's home base.

An Obsidian vault is just a folder of Markdown files, so we read and write it
directly. That means a scheduled briefing can update the vault even when
Obsidian isn't open, and there's no plugin to install. Obsidian picks up the
file changes the moment you open or focus it.

Every path is resolved *inside* the configured vault; path traversal outside
it (e.g. "../secrets") is refused, so the assistant can only ever touch the
vault.
"""

from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime
from pathlib import Path

from obsidian_copilot.core import config


class VaultPathError(ValueError):
    pass


def _vault() -> Path:
    return config.settings.vault


def _resolve(rel_path: str) -> Path:
    """Resolve a vault-relative path, refusing anything that escapes the vault.
    Adds a .md extension if none is given (Obsidian notes are Markdown)."""
    if not rel_path or not rel_path.strip():
        raise VaultPathError("A note path is required.")
    cleaned = rel_path.strip().lstrip("/")
    candidate = (_vault() / cleaned)
    if candidate.suffix == "":
        candidate = candidate.with_suffix(".md")
    resolved = candidate.resolve()
    vault_root = _vault().resolve()
    if resolved != vault_root and vault_root not in resolved.parents:
        raise VaultPathError(
            f"Refusing to access '{rel_path}': it is outside the Obsidian vault."
        )
    return resolved


def _daily_note_path(day: str | None) -> Path:
    """Path to a daily note. `day` is an ISO date (YYYY-MM-DD); defaults to
    today. Daily notes live under the configured daily-notes subfolder."""
    if day:
        try:
            parsed = date_cls.fromisoformat(day)
        except ValueError as exc:
            raise VaultPathError(f"Invalid date '{day}', expected YYYY-MM-DD.") from exc
    else:
        parsed = datetime.now().date()
    daily_dir = config.settings.daily_notes_dir
    rel = f"{daily_dir}/{parsed.isoformat()}" if daily_dir else parsed.isoformat()
    return _resolve(rel)


# --------------------------------------------------------------------------- #
# Skill functions (registered with the MCP registry at import time)
# --------------------------------------------------------------------------- #
from obsidian_copilot.skills.base import skill  # noqa: E402


@skill(
    name="list_notes",
    description=(
        "List Markdown notes in the Obsidian vault, optionally within a subfolder. "
        "Returns vault-relative paths. Use this to see what notes exist before reading."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "subfolder": {
                "type": "string",
                "description": "Optional vault-relative subfolder to list (e.g. 'Projects'). Omit for the whole vault.",
            },
            "limit": {"type": "integer", "description": "Max notes to return (default 100)."},
        },
    },
)
def list_notes(subfolder: str = "", limit: int = 100) -> dict:
    base = _resolve(subfolder) if subfolder else _vault().resolve()
    if base.is_file():
        base = base.parent
    if not base.exists():
        return {"notes": [], "count": 0}
    vault_root = _vault().resolve()
    notes = []
    for path in sorted(base.rglob("*.md")):
        notes.append(str(path.relative_to(vault_root)))
        if len(notes) >= limit:
            break
    return {"notes": notes, "count": len(notes)}


@skill(
    name="read_note",
    description="Read the full Markdown content of a note in the Obsidian vault.",
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Vault-relative path to the note, e.g. 'Projects/Website.md' (the .md is optional).",
            }
        },
        "required": ["path"],
    },
)
def read_note(path: str) -> dict:
    target = _resolve(path)
    if not target.exists():
        return {"error": f"Note not found: {path}"}
    return {
        "path": str(target.relative_to(_vault().resolve())),
        "content": target.read_text(encoding="utf-8"),
    }


@skill(
    name="write_note",
    description=(
        "Create or overwrite a note in the Obsidian vault with the given Markdown "
        "content. Parent folders are created automatically. Use append_to_note to add "
        "to an existing note without replacing it."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Vault-relative note path, e.g. 'Reports/2026-07 Summary.md'."},
            "content": {"type": "string", "description": "Full Markdown content to write."},
            "overwrite": {
                "type": "boolean",
                "description": "If false (default) and the note already exists, refuse rather than overwrite.",
            },
        },
        "required": ["path", "content"],
    },
)
def write_note(path: str, content: str, overwrite: bool = False) -> dict:
    target = _resolve(path)
    if target.exists() and not overwrite:
        return {
            "error": f"Note already exists: {path}. Pass overwrite=true to replace it, "
            "or use append_to_note to add to it."
        }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target.relative_to(_vault().resolve())), "written": True}


@skill(
    name="append_to_note",
    description=(
        "Append Markdown to the end of a note in the Obsidian vault, creating the note "
        "if it doesn't exist. Ideal for logging or adding a section without disturbing "
        "existing content."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Vault-relative note path."},
            "content": {"type": "string", "description": "Markdown to append."},
        },
        "required": ["path", "content"],
    },
)
def append_to_note(path: str, content: str) -> dict:
    target = _resolve(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    separator = "" if (not existing or existing.endswith("\n")) else "\n"
    target.write_text(existing + separator + content + "\n", encoding="utf-8")
    return {"path": str(target.relative_to(_vault().resolve())), "appended": True}


@skill(
    name="get_daily_note",
    description=(
        "Read today's (or a given date's) Obsidian daily note. Returns empty content "
        "if it doesn't exist yet. Use this to see what's already planned for the day."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "date": {"type": "string", "description": "ISO date YYYY-MM-DD. Omit for today."}
        },
    },
)
def get_daily_note(date: str = "") -> dict:
    target = _daily_note_path(date or None)
    exists = target.exists()
    return {
        "path": str(target.relative_to(_vault().resolve())),
        "exists": exists,
        "content": target.read_text(encoding="utf-8") if exists else "",
    }


@skill(
    name="update_daily_note",
    description=(
        "Write or append to today's (or a given date's) Obsidian daily note — the "
        "landing spot for the morning briefing, agenda, and tasks. Appends by default "
        "so existing content is preserved."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Markdown to add to the daily note."},
            "date": {"type": "string", "description": "ISO date YYYY-MM-DD. Omit for today."},
            "mode": {
                "type": "string",
                "enum": ["append", "overwrite"],
                "description": "append (default) adds to the note; overwrite replaces it.",
            },
        },
        "required": ["content"],
    },
)
def update_daily_note(content: str, date: str = "", mode: str = "append") -> dict:
    target = _daily_note_path(date or None)
    target.parent.mkdir(parents=True, exist_ok=True)
    if mode == "overwrite" or not target.exists():
        target.write_text(content + "\n", encoding="utf-8")
    else:
        existing = target.read_text(encoding="utf-8")
        separator = "" if (not existing or existing.endswith("\n")) else "\n"
        target.write_text(existing + separator + content + "\n", encoding="utf-8")
    return {"path": str(target.relative_to(_vault().resolve())), "mode": mode}


@skill(
    name="add_task",
    description=(
        "Add a task (an Obsidian checkbox, '- [ ] ...') to the daily note or a specified "
        "note. Use for capturing to-dos so they show up in Obsidian's task views."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "The task text."},
            "path": {
                "type": "string",
                "description": "Optional vault-relative note to add the task to. Defaults to today's daily note.",
            },
        },
        "required": ["task"],
    },
)
def add_task(task: str, path: str = "") -> dict:
    line = f"- [ ] {task.strip()}"
    if path:
        return {**append_to_note(path, line), "task": task}
    result = update_daily_note(line, mode="append")
    return {**result, "task": task}


@skill(
    name="search_notes",
    description=(
        "Full-text search the Obsidian vault for a query string. Returns matching notes "
        "with the lines that matched, so the assistant can find relevant context."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to search for (case-insensitive)."},
            "limit": {"type": "integer", "description": "Max matching notes to return (default 20)."},
        },
        "required": ["query"],
    },
)
def search_notes(query: str, limit: int = 20) -> dict:
    needle = query.strip().lower()
    if not needle:
        return {"error": "A non-empty query is required."}
    vault_root = _vault().resolve()
    matches = []
    for path in sorted(vault_root.rglob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hit_lines = [ln.strip() for ln in text.splitlines() if needle in ln.lower()]
        if hit_lines:
            matches.append(
                {"path": str(path.relative_to(vault_root)), "matches": hit_lines[:5]}
            )
        if len(matches) >= limit:
            break
    return {"query": query, "results": matches, "count": len(matches)}
