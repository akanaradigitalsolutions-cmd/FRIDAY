"""Test fixtures: point the vault at a temp dir so tests never touch a real
Obsidian vault. We swap `config.settings` in place (no module reload), which
the obsidian skill reads at call time — so skills aren't re-registered.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def temp_vault(tmp_path, monkeypatch):
    from friday.core import config

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Daily").mkdir()

    test_settings = config.Settings(
        claude_bin="claude",
        model="claude-sonnet-5",
        vault=vault,
        home=tmp_path / "home",
        daily_notes_dir="Daily",
        timezone="UTC",
        google_credentials_file=str(tmp_path / "gc.json"),
        google_token_file=str(tmp_path / "gt.json"),
        zoom_account_id="",
        zoom_client_id="",
        zoom_client_secret="",
    )
    monkeypatch.setattr(config, "settings", test_settings)

    import friday.skills.obsidian as obsidian

    return vault, obsidian
