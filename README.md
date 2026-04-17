# VPP Daily Editor Activity Report

Python script that posts a daily Google Chat summary of what each VPP editor did **yesterday**, built from ClickUp task status changes.

Same pattern as `lead_ingestion`: local Python for dev/testing, Anthropic Cloud scheduled agent for production.

## Architecture

```
Claude scheduled agent (weekdays 08:00 Kyiv)
        │
        ▼
  daily_report.py
        │
        ├─► ClickUp API  (search tasks updated yesterday in folder 901513870625)
        │   ClickUp API  (time_in_status per task — verify status changed yesterday)
        │
        ▼
  report_builder.build_report(events, date_label)
        │
        ▼
  Google Chat incoming webhook  (POST JSON)
```

**Why two ClickUp calls per task?** `date_updated` bumps on any edit (comment, priority…), so it alone causes false positives — a stale `SENT TO CLIENT` task with a comment from yesterday would be reported as "sent to client today". `GET /task/{id}/time_in_status` returns `current_status.total_time.since` — the exact timestamp when the task entered its current status. We keep only tasks whose `since` falls inside the yesterday-Kyiv window.

## Files

- [config.py](config.py) — team/folder IDs, editor name map, list→section map, status→action map
- [clickup_client.py](clickup_client.py) — minimal ClickUp v2 wrapper (search in folder, time_in_status) with pagination
- [report_builder.py](report_builder.py) — pure logic: resolve raw task to a display `TaskEvent`, render final message
- [daily_report.py](daily_report.py) — orchestrator + Google Chat POST + CLI (`--date`, `--dry-run`)
- [test_report_builder.py](test_report_builder.py) — pytest tests for formatting rules
- [.env.example](.env.example) — required env vars
- [.gitignore](.gitignore) — excludes `.env` and caches

## Local setup

```bash
cd C:\Users\kolis\Projects\TLIC\vpp_daily_report

python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

pip install requests python-dotenv pytest

cp .env.example .env
# edit .env: fill CLICKUP_API_TOKEN (pk_... from ClickUp Settings → Apps)
# GOOGLE_CHAT_WEBHOOK_URL is already known — paste it in
```

## Usage

```bash
# report for yesterday (Kyiv), post to Google Chat
python daily_report.py

# specific day, dry-run (prints the message, does not post)
python daily_report.py --date 2026-04-15 --dry-run

# specific day, actually post (useful for backfills)
python daily_report.py --date 2026-04-15

# tests
python -m pytest test_report_builder.py -v
```

## Status → action mapping

### Couples Projects
| ClickUp status | Action phrase | Included? |
|---|---|---|
| `EDIT QUE` | `picked up` | ✓ |
| `EDITING` | `continuing work on` | ✓ |
| `INTERNAL REVIEW` | `sent for internal review` | ✓ |
| `SENT TO CLIENT` | `sent to client` | ✓ |
| `EDITING CORRECTIONS` | `making corrections for` | ✓ |
| `REVIEW CORRECTIONS` | `reviewing corrections for` | ✓ |
| `CORRECTIONS SENT TO CLIENT` | `sent corrections to client` | ✓ |
| `UPLOADED ON YOUTUBE` | `uploaded` | ✓ |
| `WAITING CORRECTIONS`, `REVIEW EXPIRED`, `FINAL DRAFT APPROVED`, `FINISHED` | — | skipped |

### Reels / Other projects
| ClickUp status | Action phrase | Included? |
|---|---|---|
| `In Progress` | `working on` | ✓ |
| `On Review` | `sent for review` | ✓ |
| `Complete` | `completed` | ✓ |
| `To Do` | — | skipped |

All three mappings live in one dict: `STATUS_ACTIONS` in [config.py](config.py). Add/change statuses there.

## Expected output

```
📹 VPP Daily Report — Wed, Apr 15

— Couples —
Dima — continuing work on Matt & Teresa
Yulia — sent to client Diana & Bo

— Reels —
Dima — -
Yulia — working on Brand X

— Other —
Dima — -
Yulia — sent for review Project Z
```

Rules enforced by `build_report`:
- Every editor appears in every section; `-` when no activity for that pair.
- Same-action tasks collapse: `made revisions for Matt & Teresa · Jess & Grayson`.
- Different actions concatenate with ` · `: `internal review for Carsyn & Tom · uploaded Diana & Bo`.
- Actions appear in the order they first occurred for that editor (stable).

## Cloud scheduling — Anthropic Cloud Claude agent

Same approach as `lead_ingestion` (`trig_01YDeqpk229K1rMPeh9DbwtX`).

Since there's no ClickUp MCP, the scheduled trigger uses Bash to run the script inline. The trigger prompt embeds the logic and credentials (or fetches them from a secret store):

**Trigger setup steps:**
1. Go to https://claude.ai/code/scheduled → **+ New scheduled task**
2. Schedule: `0 10 * * 1-5` UTC (summer) or `0 11 * * 1-5` UTC (winter) — 13:00 Kyiv
3. Paste the prompt template below. Replace `__CLICKUP_TOKEN__` and `__GCHAT_WEBHOOK__` with real values (they become part of the trigger configuration — treat the trigger as a secret).
4. After creating, save the Trigger ID back into this README (next to `lead_ingestion` trigger ID) so we can manage it.

**Trigger prompt template:**

```
You are running the VPP daily report. Execute these commands exactly as written:

bash: |
  mkdir -p /tmp/vpp && cd /tmp/vpp

  # Clone the project (requires the repo to be pushed to GitHub — see README "Publishing" section)
  curl -sL https://raw.githubusercontent.com/<OWNER>/<REPO>/main/vpp_daily_report/config.py -o config.py
  curl -sL https://raw.githubusercontent.com/<OWNER>/<REPO>/main/vpp_daily_report/clickup_client.py -o clickup_client.py
  curl -sL https://raw.githubusercontent.com/<OWNER>/<REPO>/main/vpp_daily_report/report_builder.py -o report_builder.py
  curl -sL https://raw.githubusercontent.com/<OWNER>/<REPO>/main/vpp_daily_report/daily_report.py -o daily_report.py

  pip install -q requests python-dotenv

  export CLICKUP_API_TOKEN="__CLICKUP_TOKEN__"
  export GOOGLE_CHAT_WEBHOOK_URL="__GCHAT_WEBHOOK__"

  python daily_report.py

Report back the stdout of that python run.
```

**Alternative (no GitHub): inline Python in the prompt.** Paste all four `.py` files contents inline via heredocs, then run. More self-contained but the prompt becomes large and edits are awkward.

**Alternative (no Claude scheduled agent): GitHub Actions.** Push this folder to a repo, add `.github/workflows/daily.yml` with a cron trigger and secrets for the two env vars. Zero dependency on Anthropic Cloud, free under free tier, and logs live with the code. Happy to scaffold this workflow — just say the word.

## DST note

Europe/Kyiv is **EEST (UTC+3)** late March → late October and **EET (UTC+2)** the rest of the year. The cron must be adjusted twice a year when DST flips, or use a scheduler that understands IANA timezones. For the Claude scheduled agent, just edit the cron on the DST transition day.

## Extending

- **Add editor (e.g. Ilya):** append `"<ClickUp username>": "Ilya"` to `EDITORS` in [config.py](config.py:7). No other changes — `build_report` iterates over `EDITORS.values()`.
- **Add list:** append to `LISTS` and `SECTION_ORDER` in [config.py](config.py).
- **Add status:** add to `STATUS_ACTIONS` (or `SKIP_STATUSES` to exclude). Matching is lowercased.
- **Multiple assignees per task:** `resolve_event` in [report_builder.py](report_builder.py) currently takes `assignees[0]`. To credit all known editors on a task, change it to return a list of events.

## Known limitations

- **Status-based only.** Editors who worked on a task all day without changing its status are invisible. Capturing that would require time-tracking or task-update webhooks — out of scope here.
- **First assignee only.** See "Extending" for how to change.
- **API cost.** 1 search call + 1 `time_in_status` call per task updated yesterday. For small teams (<50 tasks/day) well within ClickUp's rate limits.
