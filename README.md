# VPP Daily Editor Activity Report

Python script that posts a daily Google Chat summary of what each video post-production editor did yesterday, built from ClickUp task status changes.

## Architecture

Single scheduled run per weekday.

```
Scheduled trigger (weekdays, e.g. 13:00 local)
        │
        ▼
  daily_report.py
        │
        ├─► ClickUp API   (list tasks in the configured folder)
        │
        ▼
  report_builder.build_report(events, date_label)
        │
        ▼
  Google Chat incoming webhook  (POST JSON)
```

### Ongoing vs transition statuses

Every status in the mapping is tagged one of two ways:

- **Ongoing** (`editing`, `editing corrections`, `in progress`) — the editor is actively working. A task in this status appears in the report **every day** it remains there, regardless of when `date_updated` was last touched.
- **Transition** (`sent to client`, `uploaded`, `picked up`, etc.) — a one-time hand-off event. Included only when `date_updated` falls inside the workday window.

This split exists because ClickUp's `time_in_status` endpoint returns `"No data for TIS"` on this workspace's plan, so the exact moment a status changed isn't available. `date_updated` is the best proxy we have.

## Files

- [config.py](config.py) — loads team/folder IDs, editor name map, list→section map from env; hardcodes status→action phrase map
- [clickup_client.py](clickup_client.py) — minimal ClickUp v2 wrapper (search tasks in folder) with pagination
- [report_builder.py](report_builder.py) — pure logic: resolve raw task to a display `TaskEvent`, render final message
- [daily_report.py](daily_report.py) — orchestrator + Google Chat POST + CLI (`--date`, `--dry-run`)
- [test_report_builder.py](test_report_builder.py) + [conftest.py](conftest.py) — pytest tests for formatting rules
- [.env.example](.env.example) — required env vars
- [.gitignore](.gitignore) — excludes `.env` and caches

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

pip install requests python-dotenv pytest tzdata

cp .env.example .env
# edit .env with your values (see .env.example for every required var)
```

## Usage

```bash
# report for yesterday's workday (08:00 local → 08:00 local), post to Google Chat
python daily_report.py

# specific day, dry-run (prints the message, does not post)
python daily_report.py --date 2026-04-15 --dry-run

# specific day, actually post (useful for backfills)
python daily_report.py --date 2026-04-15

# tests
python -m pytest test_report_builder.py -v
```

## Status → action mapping (defaults)

| ClickUp status | Action phrase | Type |
|---|---|---|
| `EDIT QUE` | `picked up` | transition |
| `EDITING` | `continuing work on` | **ongoing** |
| `INTERNAL REVIEW` | `sent for internal review` | transition |
| `SENT TO CLIENT` | `sent to client` | transition |
| `EDITING CORRECTIONS` | `making corrections for` | **ongoing** |
| `REVIEW CORRECTIONS` | `reviewing corrections for` | transition |
| `CORRECTIONS SENT TO CLIENT` | `sent corrections to client` | transition |
| `UPLOADED ON YOUTUBE` | `uploaded` | transition |
| `In Progress` | `working on` | **ongoing** |
| `On Review` | `sent for review` | transition |
| `Complete` | `completed` | transition |
| `WAITING CORRECTIONS`, `REVIEW EXPIRED`, `FINAL DRAFT APPROVED`, `FINISHED`, `To Do` | — | *skipped* |

Edit these in `STATUS_ACTIONS`, `SKIP_STATUSES`, and `ONGOING_STATUSES` inside [config.py](config.py).

## Expected output

```
📹 VPP Daily Report — Wed, Apr 15–16

— Couples —
Dima — continuing work on Matt & Teresa · sent to client Diana & Bo
Yulia — making corrections for Brand X
```

Rules enforced by `build_report`:
- Every editor appears in every visible section; `-` when no activity for that pair.
- Sections without any activity are hidden.
- Same-action tasks collapse.
- Different actions concatenate with ` · `.
- Day with no activity across all sections posts `No activity.`

## Date label & workday window

The window runs from `target_day 08:00` to `target_day+1 08:00` in the configured timezone. Late-night work (e.g. 02:00 AM next morning) is counted toward `target_day`. Header shows a two-day range, e.g. `Wed, Apr 15–16`.

## Known limitations

- **Attribution by first assignee.** ClickUp's API on this plan doesn't expose "who changed the status", only the assignee. `resolve_event` takes `assignees[0]`.
- **Multi-page handling.** The client paginates transparently. No hard cap.
- **DST.** When the local timezone switches between summer and winter, a cron-based scheduler defined in UTC may drift by an hour for a few days. Prefer a scheduler that understands IANA timezones.
