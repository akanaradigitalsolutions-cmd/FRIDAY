"""Terminal chat client. Always works, no extra setup beyond the `claude` CLI.

    friday            # start an interactive chat
    friday brief      # run the morning briefing once and exit
"""

from __future__ import annotations

from friday.core.config import settings
from friday.core.memory import SessionMemory
from friday.core.orchestrator import Orchestrator

_BANNER = f"""FRIDAY — your daily-ops assistant.
Vault: {settings.vault}
Type your request, or 'exit' to quit. Try:
  - "Give me my morning briefing"
  - "What's on my calendar today?"
  - "Any urgent emails I should reply to?"
  - "Set up a 30-min Google Meet with alex@example.com tomorrow at 3pm"
"""


def run_chat() -> None:
    print(_BANNER)
    memory = SessionMemory.latest()
    orch = Orchestrator(memory=memory)
    while True:
        try:
            user = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user:
            continue
        if user.lower() in {"exit", "quit", ":q"}:
            break
        try:
            reply = orch.handle_message(user)
        except Exception as exc:  # noqa: BLE001 - keep the REPL alive on errors
            print(f"friday › (error) {exc}\n")
            continue
        print(f"friday › {reply}\n")


def main() -> None:
    run_chat()


if __name__ == "__main__":
    main()
