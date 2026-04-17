"""Main orchestrator for the VPP daily editor activity report.

Usage:
    python daily_report.py                 # report for yesterday, send
    python daily_report.py --date 2026-04-15  # specific day
    python daily_report.py --dry-run       # build but don't post
"""

from __future__ import annotations

import argparse
import os
import sys

# Force UTF-8 on stdout/stderr so emoji (📹) print on Windows cp1252 consoles.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from clickup_client import ClickUpClient
from config import FOLDER_ID, SKIP_STATUSES, TEAM_ID, TIMEZONE, WORKDAY_START_HOUR
from report_builder import build_report, resolve_event


def workday_window_ms(target_day: date, tz_name: str, start_hour: int) -> tuple[int, int]:
    """Return (start_ms, end_ms) UTC unix-ms for the workday starting on target_day.

    Window is [target_day @ start_hour, target_day+1 @ start_hour) in the given tz.
    Late-night work (e.g. 02:00 AM next morning) is counted toward target_day.
    """
    tz = ZoneInfo(tz_name)
    start_local = datetime.combine(target_day, time(hour=start_hour), tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    start_ms = int(start_local.astimezone(timezone.utc).timestamp() * 1000)
    end_ms = int(end_local.astimezone(timezone.utc).timestamp() * 1000)
    return start_ms, end_ms


def collect_events(client: ClickUpClient, target_day: date) -> list:
    """Return TaskEvents for the given local day.

    We rely on `date_updated` as the activity signal. ClickUp's
    /task/{id}/time_in_status endpoint returns "No data for TIS" on this
    workspace's plan, so we can't verify that the status itself changed
    yesterday (vs. some other edit like a comment). Accepted trade-off:
    occasional false positives when a task is edited without status change.
    The workspace's date_status_updated timestamp doesn't exist in the API.
    """
    start_ms, end_ms = workday_window_ms(target_day, TIMEZONE, WORKDAY_START_HOUR)
    tasks = client.search_tasks_in_folder(TEAM_ID, FOLDER_ID, start_ms, end_ms)

    events = []
    for task in tasks:
        status_name = ((task.get("status") or {}).get("status") or "").lower()
        if status_name in SKIP_STATUSES or not status_name:
            continue
        event = resolve_event(task, status_name)
        if event is not None:
            events.append(event)
    return events


def post_to_google_chat(webhook_url: str, text: str) -> None:
    resp = requests.post(
        webhook_url,
        json={"text": text},
        headers={"Content-Type": "application/json; charset=UTF-8"},
        timeout=30,
    )
    resp.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target day in YYYY-MM-DD (local Kyiv). Default: yesterday.")
    parser.add_argument("--dry-run", action="store_true", help="Build the report but don't post it.")
    args = parser.parse_args()

    load_dotenv()
    clickup_token = os.environ.get("CLICKUP_API_TOKEN")
    webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL")
    if not clickup_token:
        print("Missing CLICKUP_API_TOKEN in environment.", file=sys.stderr)
        return 1
    if not webhook_url and not args.dry_run:
        print("Missing GOOGLE_CHAT_WEBHOOK_URL in environment.", file=sys.stderr)
        return 1

    if args.date:
        target = date.fromisoformat(args.date)
    else:
        now_kyiv = datetime.now(ZoneInfo(TIMEZONE)).date()
        target = now_kyiv - timedelta(days=1)

    client = ClickUpClient(clickup_token)
    events = collect_events(client, target)

    date_label = target.strftime("%a, %b ") + str(target.day)
    message = build_report(events, date_label)

    print(message)
    if args.dry_run:
        print("\n[dry-run] not posting", file=sys.stderr)
        return 0

    post_to_google_chat(webhook_url, message)
    print("\n[posted to Google Chat]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
