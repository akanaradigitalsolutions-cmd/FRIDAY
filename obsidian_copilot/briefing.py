"""The morning briefing — the flagship routine.

Runs one Claude turn with a fixed instruction that tells the assistant to
gather today's calendar and unread/urgent email, then write a structured
Daily Note into the Obsidian vault. Because it's a normal orchestrator call,
Claude decides which tools to use and in what order.

Run it on demand:
    obsidian-copilot brief
Or on a schedule (cron / launchd / Task Scheduler), e.g. every weekday 7am:
    0 7 * * 1-5  /path/to/venv/bin/obsidian-copilot brief
"""

from __future__ import annotations

from datetime import datetime

from obsidian_copilot.core.orchestrator import Orchestrator

BRIEFING_INSTRUCTION = """Produce my morning briefing for {today} and write it into today's \
Obsidian daily note. Steps:

1. List today's calendar events (use list_events).
2. List my unread inbox email (use list_emails) and judge which ones are urgent or need a reply \
today — don't invent anything, only use what you actually retrieve.
3. Read today's existing daily note (get_daily_note) so you don't duplicate what's already there.
4. Using update_daily_note, write a clean Markdown briefing with these sections:
   - '## Morning Briefing' with a one or two sentence summary of the day.
   - '## Agenda' — today's meetings as a time-ordered list (include Meet/Zoom links if present).
   - '## Needs Attention' — the urgent emails, each as '- [ ] Reply to <sender>: <subject>' with a \
one-line why-it-matters.
   - '## Other Unread' — a short bulleted digest of the remaining unread email.
   - '## Tasks' — carry over any open tasks you see, plus anything the email/calendar implies.

Keep it tight and skimmable. When done, tell me the daily note path and give me a 3-line spoken-\
style summary of the most important things.
""".format(today=datetime.now().strftime("%A, %d %B %Y"))


def run_briefing(orchestrator: Orchestrator | None = None) -> str:
    orch = orchestrator or Orchestrator()
    return orch.handle_message(BRIEFING_INSTRUCTION)


def main() -> None:
    print(run_briefing())


if __name__ == "__main__":
    main()
