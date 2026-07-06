"""Entry point for the `friday` command.

Subcommands:
    friday                 interactive chat (default)
    friday brief           run the morning briefing once
    friday auth-google     run the Google OAuth consent flow
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="friday", description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        default="chat",
        choices=["chat", "brief", "auth-google"],
        help="What to run (default: chat).",
    )
    args = parser.parse_args()

    if args.command == "brief":
        from friday.briefing import main as brief_main

        brief_main()
    elif args.command == "auth-google":
        from friday.integrations.google_auth import main as auth_main

        auth_main()
    else:
        from friday.cli import main as chat_main

        chat_main()


if __name__ == "__main__":
    main()
