"""Configuration for VPP daily report.

Business-specific values (team/folder IDs, editor names, list names) are
loaded from environment variables so they stay out of source control. See
.env.example for the expected shape.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


TEAM_ID = _required("CLICKUP_TEAM_ID")
FOLDER_ID = _required("CLICKUP_FOLDER_ID")
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Kyiv")
WORKDAY_START_HOUR = int(os.environ.get("WORKDAY_START_HOUR", "8"))

# EDITORS_JSON: {"<ClickUp username>": "<display name>"}
EDITORS: dict[str, str] = json.loads(_required("EDITORS_JSON"))
# LISTS_JSON: {"<ClickUp list name>": "<section label>"}
LISTS: dict[str, str] = json.loads(_required("LISTS_JSON"))
# Section display order, deduped while preserving first-seen order.
SECTION_ORDER: list[str] = list(dict.fromkeys(LISTS.values()))

STATUS_ACTIONS = {
    "edit que": "picked up",
    "editing": "continuing work on",
    "internal review": "sent for internal review",
    "sent to client": "sent to client",
    "editing corrections": "making corrections for",
    "review corrections": "reviewing corrections for",
    "corrections sent to client": "sent corrections to client",
    "uploaded on youtube": "uploaded",
    "in progress": "working on",
    "on review": "sent for review",
    "complete": "completed",
}

SKIP_STATUSES = {
    "waiting corrections",
    "review expired",
    "final draft approved",
    "finished",
    "to do",
}

# Ongoing work: task appears in the report every day while in this status, even
# if nothing changed today. Everything else in STATUS_ACTIONS is a transition
# event — shown only on the day date_updated falls in the window.
ONGOING_STATUSES = {
    "editing",
    "editing corrections",
    "in progress",
}

# Sections (display labels from LISTS) whose tasks are attributed by the task's
# due_date in ClickUp instead of by status-change activity. The task lands in
# the report for whichever day its due_date matches in the local timezone.
# Tasks in these sections without a due_date are skipped.
DUE_DATE_SECTIONS = {"Reels", "Venues"}

# Sections where a task in an ongoing status is shown ONLY if the assigned
# editor logged time on the task during the report window. Without time
# tracking proof, an "editing" task could sit there for weeks and look like
# someone is actively working on it daily — this filter cuts that noise.
# Transition events in these sections still show regardless of time tracking
# (the status change itself is the proof of work).
TIME_TRACKED_ONGOING_SECTIONS = {"Couples"}
