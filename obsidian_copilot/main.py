"""Entry point for the `obsidian-copilot` command.

Subcommands:
    obsidian-copilot                 interactive chat (default)
    obsidian-copilot brief           run the morning briefing once
    obsidian-copilot auth-google     run the Google OAuth consent flow
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="obsidian-copilot", description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="chat",
        choices=["chat", "brief", "auth-google"],
        help="What to run (default: chat).",
    )
    args = parser.parse_args()

    if args.command == "brief":
        from obsidian_copilot.briefing import main as brief_main

        brief_main()
    elif args.command == "auth-google":
        from obsidian_copilot.integrations.google_auth import main as auth_main

        auth_main()
    else:
        from obsidian_copilot.cli import main as chat_main

        chat_main()


if __name__ == "__main__":
    main()
