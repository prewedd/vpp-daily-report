"""Pure logic: take filtered task events, build the formatted report text."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from config import EDITORS, LISTS, SECTION_ORDER, STATUS_ACTIONS


@dataclass(frozen=True)
class TaskEvent:
    """One editor-visible status change for one task, resolved to display names."""

    section: str  # "Couples" | "Reels" | "Other"
    editor: str  # "Dima" | "Yulia"
    action: str  # e.g. "continuing work on"
    task_name: str


def resolve_event(
    task: dict, status_name: str, action_override: str | None = None
) -> TaskEvent | None:
    """Map a raw ClickUp task + current status to a display-ready TaskEvent.

    Returns None if the task's list, assignee, or status is outside our mapping
    (i.e. this event should not appear in the report).

    action_override forces the action phrase regardless of status — used when a
    task is included because the editor logged time on it (proven work) but the
    status has since moved to something whose mapped phrase would misrepresent
    what they actually did that day.
    """
    list_name = (task.get("list") or {}).get("name", "")
    section = LISTS.get(list_name)
    if section is None:
        return None

    assignees = task.get("assignees") or []
    if not assignees:
        return None
    editor = EDITORS.get(assignees[0].get("username", ""))
    if editor is None:
        return None

    action = action_override or STATUS_ACTIONS.get(status_name.lower())
    if action is None:
        return None

    return TaskEvent(
        section=section,
        editor=editor,
        action=action,
        task_name=task.get("name", "").strip(),
    )


def build_report(events: list[TaskEvent], date_label: str) -> str:
    """Render the final Google Chat message.

    Every editor appears in every section; '-' when that editor had no activity
    in that section. Within a section/editor, tasks sharing an action collapse:

        "made revisions for Matt & Teresa | Jess & Grayson"

    Different actions for the same editor concatenate with ' | ':

        "internal review for Carsyn & Tom | uploaded Diana & Bo"
    """
    # (section, editor, action) -> [task_name, ...]
    buckets: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    # preserve first-seen action order per (section, editor)
    action_order: dict[tuple[str, str], list[str]] = defaultdict(list)
    for ev in events:
        key = (ev.section, ev.editor, ev.action)
        buckets[key].append(ev.task_name)
        order_key = (ev.section, ev.editor)
        if ev.action not in action_order[order_key]:
            action_order[order_key].append(ev.action)

    editors_in_order = list(EDITORS.values())

    # Hide sections where no editor had any activity.
    active_sections = [
        s for s in SECTION_ORDER
        if any(action_order.get((s, ed)) for ed in editors_in_order)
    ]

    lines: list[str] = [f"📹 VPP Daily Report — {date_label}", ""]
    if not active_sections:
        lines.append("No activity.")
        return "\n".join(lines)

    for section in active_sections:
        lines.append(f"— {section} —")
        for editor in editors_in_order:
            actions = action_order.get((section, editor), [])
            if not actions:
                lines.append(f"{editor} — -")
                continue
            phrases = [
                f"{action} {' | '.join(buckets[(section, editor, action)])}"
                for action in actions
            ]
            lines.append(f"{editor} — {' | '.join(phrases)}")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)
