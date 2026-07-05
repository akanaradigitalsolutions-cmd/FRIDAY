"""Central configuration: env vars, the Obsidian vault path, credential
paths, and model selection. Loaded once at import time.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _resolve_vault() -> Path:
    """The Obsidian vault is just a folder of Markdown files. We read/write
    it directly (no plugin needed), so a scheduled briefing can update it
    even when Obsidian isn't running. Defaults to ~/ObsidianVault."""
    raw = os.getenv("OBSIDIAN_VAULT", "").strip()
    path = Path(raw).expanduser() if raw else Path.home() / "ObsidianVault"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _resolve_home() -> Path:
    path = Path.home() / ".obsidian-copilot"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass(frozen=True)
class Settings:
    # Brain
    claude_bin: str
    model: str
    # Storage
    vault: Path
    home: Path
    daily_notes_dir: str
    # Locale
    timezone: str
    # Google (Gmail + Calendar + Meet)
    google_credentials_file: str
    google_token_file: str
    # Zoom (Server-to-Server OAuth)
    zoom_account_id: str
    zoom_client_id: str
    zoom_client_secret: str

    @property
    def daily_notes_path(self) -> Path:
        path = self.vault / self.daily_notes_dir if self.daily_notes_dir else self.vault
        path.mkdir(parents=True, exist_ok=True)
        return path


def load_settings() -> Settings:
    home = _resolve_home()
    return Settings(
        claude_bin=os.getenv("OC_CLAUDE_BIN", "claude"),
        model=os.getenv("OC_MODEL", "claude-sonnet-5"),
        vault=_resolve_vault(),
        home=home,
        daily_notes_dir=os.getenv("OBSIDIAN_DAILY_NOTES_DIR", "Daily").strip(),
        timezone=os.getenv("OC_TIMEZONE", "UTC").strip() or "UTC",
        google_credentials_file=os.getenv(
            "GOOGLE_CREDENTIALS_FILE", str(home / "google_credentials.json")
        ).strip(),
        google_token_file=os.getenv(
            "GOOGLE_TOKEN_FILE", str(home / "google_token.json")
        ).strip(),
        zoom_account_id=os.getenv("ZOOM_ACCOUNT_ID", "").strip(),
        zoom_client_id=os.getenv("ZOOM_CLIENT_ID", "").strip(),
        zoom_client_secret=os.getenv("ZOOM_CLIENT_SECRET", "").strip(),
    )


settings = load_settings()
