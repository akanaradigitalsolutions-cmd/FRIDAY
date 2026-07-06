"""Report skill: save a compiled report as a Markdown note in the vault's
Reports folder, timestamped and easy to find in Obsidian.

The assistant does the actual synthesis (pulling from calendar, email, and
notes); this skill just standardizes where reports land and how they're
titled, so they accumulate in one place.
"""

from __future__ import annotations

from datetime import datetime

from friday.skills.base import skill
from friday.skills.obsidian import write_note

_REPORTS_DIR = "Reports"


def _slugify(title: str) -> str:
    keep = [c if c.isalnum() or c in " -_" else " " for c in title]
    return " ".join("".join(keep).split())[:80] or "Report"


@skill(
    name="save_report",
    description=(
        "Save a finished report as a Markdown note in the vault's Reports folder. "
        "Provide the title and the full Markdown body; the note is filed as "
        "'Reports/YYYY-MM-DD <title>.md'. Returns the note path to share with the user."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Report title, e.g. 'Weekly Ops Summary'."},
            "body": {"type": "string", "description": "Full report content in Markdown."},
            "date": {
                "type": "string",
                "description": "ISO date prefix YYYY-MM-DD. Omit for today.",
            },
        },
        "required": ["title", "body"],
    },
)
def save_report(title: str, body: str, date: str = "") -> dict:
    stamp = date.strip() or datetime.now().date().isoformat()
    filename = f"{_REPORTS_DIR}/{stamp} {_slugify(title)}.md"
    header = f"# {title}\n\n*Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
    result = write_note(filename, header + body, overwrite=True)
    return {**result, "title": title}
