"""Thin ClickUp API client for the VPP daily report."""

from __future__ import annotations

import requests

BASE_URL = "https://api.clickup.com/api/v2"


class ClickUpClient:
    def __init__(self, api_token: str):
        self.session = requests.Session()
        self.session.headers.update({"Authorization": api_token})

    def search_tasks_in_folder(
        self,
        team_id: str,
        folder_id: str,
        date_updated_gt_ms: int | None = None,
        date_updated_lt_ms: int | None = None,
    ) -> list[dict]:
        """Return tasks in a folder, optionally filtered by a date_updated window.

        Paginates until an empty page comes back.
        """
        tasks: list[dict] = []
        page = 0
        while True:
            params: dict[str, object] = {
                "page": page,
                "project_ids[]": folder_id,
                "include_closed": "true",
                "subtasks": "false",
            }
            if date_updated_gt_ms is not None:
                params["date_updated_gt"] = date_updated_gt_ms
            if date_updated_lt_ms is not None:
                params["date_updated_lt"] = date_updated_lt_ms
            resp = self.session.get(
                f"{BASE_URL}/team/{team_id}/task",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json().get("tasks", [])
            if not batch:
                break
            tasks.extend(batch)
            page += 1
        return tasks

    def get_task_comments(self, task_id: str) -> list[dict]:
        """Return a task's comments (most recent first).

        One page (~25 newest) is enough for a one-day report window — status
        transitions we care about are always recent relative to the run.
        """
        resp = self.session.get(
            f"{BASE_URL}/task/{task_id}/comment",
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("comments", [])

    def get_task_time_entries(self, task_id: str) -> list[dict]:
        """Return time-tracking intervals on a task, grouped by user.

        Each item in the list looks like {"user": {...}, "intervals": [...]}
        where each interval has "start" and "end" as unix-ms strings.
        Empty list if no time has been tracked.
        """
        resp = self.session.get(
            f"{BASE_URL}/task/{task_id}/time",
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def get_time_in_status(self, task_id: str) -> dict | None:
        """Return time_in_status payload, or None if ClickUp has no TIS data.

        The endpoint returns HTTP 401 with body {"err":"No data for TIS"} for
        tasks whose status history hasn't been recorded — we treat this as "no
        data, skip this task" rather than an auth failure.
        """
        resp = self.session.get(
            f"{BASE_URL}/task/{task_id}/time_in_status",
            timeout=30,
        )
        if resp.status_code in (401, 404):
            try:
                body = resp.json()
            except ValueError:
                body = {}
            if "No data for TIS" in body.get("err", ""):
                return None
        resp.raise_for_status()
        return resp.json()
