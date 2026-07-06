"""Importing this package registers every skill with the shared registry.

Each submodule calls @skill(...) at import time, so importing them here is
what populates the registry the MCP server and the CLI client read from.
"""

from friday.skills import (  # noqa: F401
    gcalendar,
    gmail,
    meetings,
    obsidian,
    reports,
)
