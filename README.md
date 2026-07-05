# Obsidian Copilot

An AI assistant that runs your **daily operations** and files everything into
your **Obsidian** vault — powered by **Claude**.

It does the five things you asked for:

| Daily task | What it does |
|---|---|
| 📊 **Reports** | Compiles daily/weekly summaries from your calendar, email, and notes, saved as Markdown notes in your vault |
| 📅 **Manage schedule** | Reads your Google Calendar; creates, moves, and cancels events |
| 📧 **Emails + urgent notices** | Reads your Gmail inbox and flags what's urgent or needs a reply today |
| 🎥 **Meeting arrangement** | Sets up a **Google Meet** or **Zoom** meeting and puts it on your calendar with the join link |
| 🧠 **Obsidian hub** | Reads/writes your vault; every result lands as a note, so your "second brain" stays the single source of truth |

The flagship feature is the **morning briefing**: one command (schedulable via
cron) reads today's calendar + unread email, flags the urgent items, and writes
a clean **Daily Note** into your Obsidian vault — so you open Obsidian and your
day is already laid out.

## How it works (30-second version)

Claude is the brain. Each capability above is a **skill** — a small Python
function exposed to Claude as a tool over MCP. You talk to it in plain English;
Claude decides which tools to call (read the calendar, fetch email, write the
note) and does the multi-step work in one shot. Your Obsidian vault is just a
folder of Markdown files, so the assistant reads and writes it directly — no
plugin, and it works even when Obsidian is closed.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Quick start

### 1. Install Claude Code and log in
The assistant uses the `claude` CLI as its brain, on your **Claude Pro/Max
subscription** — no separate API key/billing.
```bash
npm install -g @anthropic-ai/claude-code
claude login
```

### 2. Install Obsidian Copilot
```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -e ".[google]"          # include Google APIs (Gmail/Calendar/Meet)
```

### 3. Configure
```bash
cp .env.example .env
```
Set at least `OBSIDIAN_VAULT` (path to your vault) and `OC_TIMEZONE`. Fill in
Google/Zoom credentials when you're ready for those (see `.env.example` for the
step-by-step).

### 4. Authorize Google (one time)
```bash
obsidian-copilot auth-google        # opens a browser for consent, caches a token
```

### 5. Run
```bash
obsidian-copilot                    # interactive chat
obsidian-copilot brief              # run the morning briefing once
```

Try:
- "Give me my morning briefing"
- "What's on my calendar today, and any urgent emails?"
- "Set up a 30-minute Google Meet with alex@example.com tomorrow at 3pm"
- "Book a Zoom call titled 'Q3 Planning' Friday 10am for 45 minutes"
- "Summarize this week and save it as a report"

### Schedule the morning briefing
Add a cron entry (macOS/Linux) to run it automatically on weekday mornings:
```cron
0 7 * * 1-5  /full/path/to/.venv/bin/obsidian-copilot brief
```
Because the vault is written directly, the note appears whether or not Obsidian
is open — it shows up the moment you open the app.

## What works without credentials

The **Obsidian vault skills** (read/write notes, daily notes, tasks, search)
work immediately — no Google or Zoom setup needed. Gmail, Calendar, Meet, and
Zoom light up once you add their credentials; until then the assistant tells you
exactly what to set up instead of failing.

## Development
```bash
pip install -e ".[dev]"
pytest
```

## Security notes
- No Anthropic API key is used or stored — auth is handled by `claude login`.
- The vault skill can only read/write **inside your configured vault**; path
  traversal outside it is refused.
- Google/Zoom secrets live only in `.env` and cached token files, all
  gitignored. Gmail scope is `modify` (read + mark read/label) — it cannot
  permanently delete mail.
