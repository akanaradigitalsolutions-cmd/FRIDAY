# Obsidian Copilot — Architecture & Roadmap

An AI assistant for daily operations — email triage, schedule management,
meeting arrangement, reporting — with your Obsidian vault as the hub and Claude
as the brain.

## Design decisions (locked in)

| Decision | Choice | Why |
|---|---|---|
| Brain | The `claude` CLI (Claude Code) in headless mode, authed via `claude login` | Uses your Claude Pro/Max subscription instead of metered API billing; Claude Code runs its own tool-use loop so we don't build one |
| Extensibility | "Skills" — Python functions exposed to Claude as MCP tools | Every capability (email, calendar, meetings, reports, vault) is a self-contained skill; `mcp_server.py` serves them all as one MCP server |
| Obsidian access | **Direct vault folder** (read/write Markdown files) | Works when Obsidian is closed (needed for the scheduled briefing), no plugin dependency, offline-safe. The Local REST API plugin only works while Obsidian is running |
| Email + Calendar | Google (Gmail + Calendar APIs), one OAuth client | You're on Google Workspace; Meet links come free from the Calendar API |
| Meetings | Google Meet (via Calendar) **and** Zoom (Server-to-Server OAuth) | Meet needs no extra API; Zoom is a direct REST call, mirrored onto Calendar |
| Urgency detection | Done by Claude reading the mail, not keyword rules | The model judges importance far better than a hardcoded list |

## Brain: Claude Code CLI, not the API

We don't call the Anthropic Messages API directly. `core/llm.py` shells out to
`claude -p` in headless mode. When you've run `claude login` against a Pro/Max
subscription (and `ANTHROPIC_API_KEY` is unset), usage draws on the
subscription. Claude Code runs its own agentic tool-use loop, so a single call
can read the calendar, fetch email, and write the Daily Note in one shot.

Every call (see `ClaudeCLIClient.build_args`):
- `--mcp-config` / `--strict-mcp-config` — points Claude Code at
  `obsidian_copilot/mcp_server.py` as the only MCP server.
- `--allowedTools mcp__copilot__<skill>,…` — whitelists just our skills.
- `--disallowedTools Bash,Read,Write,…` — denies Claude Code's built-in tools
  by name, so it can only touch the machine through our skills.
- `--permission-mode dontAsk` — headless, no human to click "allow".
- `--system-prompt` — the Obsidian Copilot persona (see `orchestrator.py`).
- `--resume <session_id>` — Claude Code's own session store holds context
  between turns; the id is persisted by `SessionMemory`.

## High-level architecture

```
   Triggers                    Core Orchestrator              Skills (MCP tools)
 ─────────────      ┌────────────────────────────┐          ┌─────────────────────┐
 chat (CLI)  ─────▶ │                            │─`claude`▶│ obsidian  (vault R/W)│
 brief (cron) ────▶ │  build prompt → claude -p  │  spawns  │ gmail     (triage)   │
                    │  parse JSON reply          │◀────────▶│ gcalendar (schedule) │
                    │  (SessionMemory: id+log)   │  over MCP│ meetings  (meet/zoom)│
                    └────────────────────────────┘  (stdio) │ reports   (save .md) │
                                   │                         └─────────────────────┘
                                   ▼
                     Writes notes into your Obsidian
                     vault (Daily Note, Reports, tasks)
```

Every frontend (interactive chat, the `brief` job) just feeds text into the same
`Orchestrator`. The orchestrator and skills don't care where the text came from.

## Repo layout

```
obsidian_copilot/
  core/
    config.py         # env vars, vault path, credential paths, timezone
    llm.py             # ClaudeCLIClient: shells out to `claude -p` headlessly
    memory.py          # session id + transcript bookkeeping (JSON on disk)
    orchestrator.py    # system prompt + handle_message()
  skills/
    base.py            # @skill decorator + registry
    obsidian.py         # read/write notes, daily note, tasks, search (no creds needed)
    gmail.py            # list/read/mark-read inbox mail
    gcalendar.py        # list/create/update/cancel calendar events
    meetings.py         # create_meeting → Google Meet or Zoom + calendar event
    reports.py          # save_report → Markdown note in Reports/
  integrations/
    google_auth.py      # shared Google OAuth (Gmail + Calendar) + `auth-google`
    zoom_auth.py        # Zoom Server-to-Server OAuth (stdlib only)
  mcp_server.py         # MCP stdio server exposing the skill registry
  briefing.py           # the morning-briefing routine (obsidian-copilot brief)
  cli.py                # interactive terminal chat
  main.py               # entry point: chat / brief / auth-google
```

## The morning briefing

`briefing.py` sends one fixed instruction to the orchestrator: gather today's
calendar + unread email, judge urgency, and write a structured Daily Note
(Summary / Agenda / Needs Attention / Other Unread / Tasks). It's a normal
Claude turn, so the model chooses the tools and order. Schedule it with cron and
your day is drafted before you sit down.

## Roadmap (phased)

- **Phase 1 — Core + vault + Google + Zoom (this repo).** Skill engine, Obsidian
  vault skills (working with no credentials), Gmail/Calendar/Meet, Zoom,
  reports, and the morning briefing. Vault skills are unit-tested.
- **Phase 2 — Reply drafting & send.** Draft replies to urgent email for
  approval, then send (Gmail `send` scope).
- **Phase 3 — Weekly review & richer reports.** Weekly rollups, optional PDF
  export (reportlab), meeting-notes templates auto-created per event.
- **Phase 4 — Proactive nudges.** Watch for high-priority mail / imminent
  meetings and surface a notification, not just a note.
- **Phase 5 — More sources.** Slack, Notion, task managers (Todoist/Things) as
  additional skills, all still landing in the vault.
- **Phase 6 — Packaging.** A menu-bar/tray app and one-command scheduled setup.

## Security notes

- No Anthropic API key stored — auth via `claude login` only.
- Every `claude -p` call denies built-in Bash/Read/Write and whitelists only our
  skills, so Claude can't touch the machine outside them.
- The vault skill resolves every path inside the configured vault and refuses
  traversal outside it.
- Google/Zoom secrets and cached tokens are gitignored. Gmail uses the `modify`
  scope (read + label/mark-read), not delete.
